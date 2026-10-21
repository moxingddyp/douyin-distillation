import importlib.util
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pipeline', ROOT / 'scripts/pipeline.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name) / 'work'
        p.make_demo(self.work)

    def mutate(self, file, callback):
        value = p.read(self.work / file)
        callback(value)
        p.save(self.work / file, value)

    def test_real_wav_decode(self):
        result = p.media_info(self.work / 'source.wav')
        self.assertEqual(result['duration_s'], 2)
        self.assertEqual(result['audio_decoded_samples'], 32000)

    def test_fixture_rejected_by_default(self):
        with self.assertRaisesRegex(ValueError, 'Fixture'):
            p.validate_review(self.work)

    def test_fixture_explicit_only(self):
        report = p.validate_review(self.work, True)
        self.assertTrue(report['fixture'])
        self.assertFalse(report['semantic_truth_verified_by_program'])

    def test_no_overwrite(self):
        with self.assertRaises(ValueError):
            p.make_demo(self.work)

    def test_source_change_rejected(self):
        with (self.work / 'source.wav').open('ab') as stream:
            stream.write(b'changed')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            p.validate_review(self.work, True)

    def test_transcript_source_rejected(self):
        self.mutate('transcript.json', lambda d: d.update(source_sha256='other'))
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            p.read_packet(self.work, 'transcript')

    def test_transcript_boundary(self):
        self.mutate('transcript.json', lambda d: d['segments'][0].update(end=10))
        with self.assertRaisesRegex(ValueError, 'boundary'):
            p.read_packet(self.work, 'transcript')

    def test_transcript_nonnumeric(self):
        self.mutate('transcript.json', lambda d: d['segments'][0].update(start='bad'))
        with self.assertRaises(ValueError):
            p.read_packet(self.work, 'transcript')

    def test_time_filter(self):
        self.assertEqual(len(p.read_packet(self.work, 'transcript', 1.2, 1.8)['segments']), 0)

    def test_frame_tamper(self):
        (self.work / 'frame.ppm').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'frame missing/changed'):
            p.validate_review(self.work, True)

    def test_path_escape(self):
        with self.assertRaisesRegex(ValueError, 'escapes'):
            p.within(self.work, '../outside')

    def test_symlink_escape(self):
        external = Path(self.temp.name) / 'outside'
        external.write_text('external')
        (self.work / 'link').symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'escapes'):
            p.within(self.work, 'link')

    def test_missing_gate(self):
        self.mutate('review.json', lambda d: d.update(conclusions_traceable=False))
        with self.assertRaisesRegex(ValueError, 'gate missing'):
            p.validate_review(self.work, True)

    def test_audio_no_inherited_authorization(self):
        self.mutate('review.json', lambda d: d.update(independent_audio_reviewed=False))
        with self.assertRaisesRegex(ValueError, 'explicit scoped'):
            p.validate_review(self.work, True)

    def test_audio_exclusions_required(self):
        self.mutate('review.json', lambda d: d.update(independent_audio_reviewed=False,
            audio_acceptance={'mode': 'crosschecked_sources_with_audio_exclusions',
                              'authorization_reference': 'this-task-only',
                              'audio_only_items_excluded': True, 'exclusions_file': 'missing.md'}))
        with self.assertRaisesRegex(ValueError, 'exclusions'):
            p.validate_review(self.work, True)

    def test_audio_scoped_acceptance(self):
        (self.work / 'exclusions.md').write_text('声音专属未核信息不进入结论。', encoding='utf-8')
        self.mutate('review.json', lambda d: d.update(independent_audio_reviewed=False,
            audio_acceptance={'mode': 'crosschecked_sources_with_audio_exclusions',
                              'authorization_reference': 'synthetic-task',
                              'audio_only_items_excluded': True, 'exclusions_file': 'exclusions.md'}))
        self.assertTrue(p.validate_review(self.work, True)['fixture'])

    def test_comment_count(self):
        self.mutate('review.json', lambda d: d.update(captured_comment_count=0))
        with self.assertRaisesRegex(ValueError, 'count mismatch'):
            p.validate_review(self.work, True)

    def test_comment_other_work(self):
        self.mutate('comments.json', lambda d: d.update(work_id='another-work'))
        with self.assertRaisesRegex(ValueError, 'different work'):
            p.validate_review(self.work, True)
        with self.assertRaisesRegex(ValueError, 'different work'):
            p.read_packet(self.work, 'comments')

    def test_comment_other_source_same_count(self):
        self.mutate('comments.json', lambda d: d.update(source_sha256='different'))
        with self.assertRaisesRegex(ValueError, 'different work'):
            p.validate_review(self.work, True)

    def test_comment_fixture_only(self):
        for file in ['manifest.json', 'transcript.json', 'ocr.json', 'review.json']:
            self.mutate(file, lambda d: d.update(fixture=False))
        with self.assertRaisesRegex(ValueError, 'Fixture'):
            p.validate_review(self.work)

    def test_no_account_identifiers_exported(self):
        self.mutate('comments.json', lambda d: d['comments'][0].update(user_id='private', nickname='private'))
        out = p.read_packet(self.work, 'comments')
        self.assertNotIn('user_id', out['comments'][0])
        self.assertNotIn('nickname', out['comments'][0])

    def test_source_reference_missing(self):
        self.mutate('review.json', lambda d: d.update(sources=[]))
        with self.assertRaisesRegex(ValueError, 'primary sources'):
            p.validate_review(self.work, True)

    def test_pending_review(self):
        self.mutate('review.json', lambda d: d.update(remaining_gates=['listen']))
        with self.assertRaisesRegex(ValueError, 'completed gates'):
            p.validate_review(self.work, True)

    def test_missing_local_model_blocks_before_import(self):
        with patch.dict('sys.modules', {'faster_whisper': None}):
            with self.assertRaisesRegex(ValueError, 'local CTranslate2'):
                p.transcribe(self.work, Path(self.temp.name) / 'missing', 'cpu', 'int8', 'zh')

    def test_missing_ocr_assets_blocks_before_import(self):
        with patch.dict('sys.modules', {'rapidocr': None, 'av': None}):
            with self.assertRaisesRegex(ValueError, 'All local OCR'):
                p.ocr(self.work, 15, '/missing/det', '/missing/cls', '/missing/rec', '/missing/keys')

    def test_ocr_partial_frames_not_overwritten(self):
        # Remove only synthetic temp test output, not release/user data.
        (self.work / 'ocr.json').unlink()
        (self.work / 'frames').mkdir()
        marker = self.work / 'frames' / 'keep'
        marker.write_text('retained')
        assets = []
        for name in ['det', 'cls', 'rec', 'keys']:
            file = Path(self.temp.name) / name
            file.write_bytes(b'local-test-asset')
            assets.append(file)
        with self.assertRaisesRegex(ValueError, 'Uncommitted'):
            p.ocr(self.work, 15, *assets)
        self.assertEqual(marker.read_text(), 'retained')


if __name__ == '__main__':
    unittest.main()
