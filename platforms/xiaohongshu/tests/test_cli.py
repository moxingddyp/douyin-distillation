import asyncio
import copy
from email.message import Message
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.request import Request

SPEC = importlib.util.spec_from_file_location('xhs_cli', Path(__file__).resolve().parents[1] / 'cli.py')
cli = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cli)


def packet():
    return {'note': {'noteId': 'synthetic-note', 'title': 'Synthetic example', 'desc': 'Local test', 'user': {'nickname': 'Example'}, 'imageList': []},
            'comments': {'list': [{'id': 'c1', 'content': 'Example comment', 'likeCount': '2'}], 'hasMore': True}}


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
    def tearDown(self):
        self.temp.cleanup()
    def test_export_allowlist_and_redaction(self):
        data = packet()
        data['cookie'] = 'SHOULD_NOT_EXPORT'
        data['note']['desc'] = 'https://example.com/read?xsec_token=SECRET https://a.xhscdn.com/file?signature=SECRET cookie=SECRET'
        result = cli.export(data, self.root)
        serialized = json.dumps(result)
        self.assertNotIn('SECRET', serialized)
        self.assertNotIn('SHOULD_NOT_EXPORT', serialized)
        self.assertEqual(result['interaction_snapshot'], {})
        self.assertIn('not obtained', (self.root / 'synthetic-note/content.md').read_text())
        self.assertFalse(result['coverage']['all_comments_verified'])
    def test_share_count_alias_preserves_observed_key_and_raw_value(self):
        for key in ('shareCount', 'sharedCount'):
            with self.subTest(key=key):
                data = packet()
                data['note']['interactInfo'] = {key: '1.2万'}
                result = cli.export(data, self.root)
                self.assertEqual(result['interaction_snapshot'], {key: '1.2万'})
                rendered = (self.root / 'synthetic-note/content.md').read_text()
                self.assertIn('- sharedCount: 1.2万', rendered)
    def test_missing_share_count_remains_unknown(self):
        result = cli.export(packet(), self.root)
        self.assertEqual(result['interaction_snapshot'], {})
        self.assertIn('- sharedCount: not obtained', (self.root / 'synthetic-note/content.md').read_text())
    def test_empty_refresh_preserves_comments_and_snapshot(self):
        first = cli.export(packet(), self.root)
        data = packet(); data['comments']['list'] = []
        second = cli.export(data, self.root)
        self.assertEqual(second['comments'], first['comments'])
        self.assertEqual(second['coverage']['current_top_level'], 0)
        self.assertEqual(second['coverage']['retained_from_previous'], 1)
        self.assertEqual(len(list((self.root / 'synthetic-note/snapshots').glob('*.json'))), 1)
    def test_conflicting_comment_parent(self):
        with self.assertRaises(ValueError):
            cli.comments([{'id': 'a', 'subComments': [{'id': 'b'}]}, {'id': 'b'}])
    def test_note_traversal_and_symlink_escape(self):
        data = packet(); data['note']['noteId'] = '../escape'
        with self.assertRaises(ValueError): cli.export(data, self.root)
        other = self.root / 'other'; other.mkdir()
        out = self.root / 'out'; out.mkdir()
        (out / 'synthetic-note').symlink_to(other, target_is_directory=True)
        with self.assertRaises(ValueError): cli.export(packet(), out)
        with self.assertRaises(ValueError): cli.inside(self.root, '../elsewhere')
    def test_manifest_identity_and_media_hash(self):
        folder = self.root / 'synthetic-note'; folder.mkdir()
        cli.save(folder / 'media-manifest.json', {'note_id': 'another-note', 'files': []})
        with self.assertRaises(ValueError): cli.export(packet(), self.root)
        media = folder / 'sample.png'; media.write_bytes(b'synthetic')
        cli.save(folder / 'media-manifest.json', {'note_id': 'synthetic-note', 'files': [{'kind': 'image', 'path': 'sample.png', 'sha256': 'wrong'}]})
        with self.assertRaises(ValueError): cli.export(packet(), self.root)
    def test_cdn_and_redirect_bounds(self):
        self.assertTrue(cli.allowed_media('https://example.xhscdn.com/image?sig=private'))
        for url in ['http://example.xhscdn.com/a', 'https://xhscdn.com.evil.test/a', 'https://user:password@a.xhscdn.com/a', 'https://a.xhscdn.com:444/a', 'file:///tmp/a']:
            self.assertFalse(cli.allowed_media(url))
        with self.assertRaises(ValueError): cli.CDNRedirect().redirect_request(Request('https://a.xhscdn.com/a'), None, 302, '', {}, 'https://example.com/a')
    def test_original_image_order_and_h264_preference(self):
        note = {'imageList': [{'urlDefault': 'first'}, {'urlDefault': 'second'}], 'video': {'media': {'stream': {'h265': [{'masterUrl': 'hevc', 'videoCodec': 'h265', 'width': 4096, 'height': 2160}], 'h264': [{'masterUrl': 'avc', 'videoCodec': 'h264', 'width': 1920, 'height': 1080}]}}}}
        self.assertEqual(cli.media_jobs(note), [('image', 1, 'first'), ('image', 2, 'second'), ('video', 1, 'avc')])
    def test_private_and_public_paths_separate(self):
        profile = self.root / 'profile'; profile.mkdir()
        with self.assertRaises(ValueError): cli.validate_capture_paths(profile, profile / 'raw', self.root / 'out')
        cli.validate_capture_paths(profile, self.root / 'private', self.root / 'output')
    def test_non_windows_capture_stops_before_browser(self):
        with patch.object(cli, 'windows_runtime', return_value=False):
            with self.assertRaises(RuntimeError): asyncio.run(cli.capture(SimpleNamespace()))
            with self.assertRaises(RuntimeError): cli.download(packet(), self.root)
    def test_download_reuse_bound_and_manifest_transaction(self):
        data = packet(); data['note']['imageList'] = [{'urlDefault': 'https://a.xhscdn.com/file?signature=one'}]
        class Response:
            def __init__(self):
                self.headers = Message(); self.headers['Content-Type'] = 'image/png'; self.headers['Content-Length'] = '4'; self.blocks = [b'data', b'']
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, n): return self.blocks.pop(0)
        opener = SimpleNamespace(open=lambda *args, **kwargs: Response())
        with patch.object(cli, 'windows_runtime', return_value=True), patch.object(cli, 'build_opener', return_value=opener):
            result = cli.download(data, self.root, 4)
            self.assertEqual(len(result), 1)
            self.assertNotIn('signature', json.dumps(result))
            data['note']['imageList'][0]['urlDefault'] = 'https://a.xhscdn.com/file?signature=two'
            with patch.object(opener, 'open', side_effect=AssertionError('must reuse bytes')):
                self.assertEqual(cli.download(data, self.root, 4), result)
            before = (self.root / 'synthetic-note/media-manifest.json').read_bytes()
            data['note']['imageList'].append({'urlDefault': 'https://a.xhscdn.com/another'})
            with self.assertRaises(ValueError): cli.download(data, self.root, 3)
            self.assertEqual((self.root / 'synthetic-note/media-manifest.json').read_bytes(), before)
    def test_normal_link_query_preserved(self):
        self.assertEqual(cli.clean_text('https://example.com/paper?doi=10.1234%2Fab&signature=private#section'), 'https://example.com/paper?doi=10.1234%2Fab#section')
    def test_same_note_changed_media_invalidates_processing(self):
        cli.export(packet(), self.root)
        folder = self.root / 'synthetic-note'
        old = cli.read(folder / 'data.json'); old['machine_processing'] = {'asr': {'path': 'derived/transcript.json'}}; cli.save(folder / 'data.json', old)
        image = folder / 'image.png'; image.write_bytes(b'synthetic')
        entry = {'kind': 'image', 'index': 1, 'path': 'image.png', 'sha256': cli.sha(image), 'bytes': 9}
        cli.save(folder / 'media-manifest.json', {'note_id': 'synthetic-note', 'files': [entry]})
        result = cli.export(packet(), self.root)
        self.assertEqual(result['machine_processing'], {})
        self.assertTrue(any(cli.read(p).get('machine_processing') for p in (folder / 'snapshots').glob('*.json')))
    def test_process_rejects_different_export_mapping(self):
        cli.export(packet(), self.root)
        folder = self.root / 'synthetic-note'
        cli.save(folder / 'media-manifest.json', {'note_id': 'synthetic-note', 'files': [{'kind': 'image', 'path': 'another.png', 'sha256': 'hash'}]})
        with patch.object(cli, 'shared_pipeline', return_value=SimpleNamespace()):
            with self.assertRaisesRegex(ValueError, 'mapping differs'): cli.process(SimpleNamespace(note_dir=folder))
    def test_missing_main_video_is_explicit_partial(self):
        data = packet(); data['note']['type'] = 'video'; data['note']['imageList'] = [{'urlDefault': 'https://a.xhscdn.com/cover'}]
        with patch.object(cli, 'windows_runtime', return_value=True):
            with self.assertRaises(cli.MediaIncomplete) as error: cli.download(data, self.root)
        self.assertEqual(error.exception.coverage['missing_sources']['video'], 1)
        self.assertEqual(error.exception.coverage['obtained']['video'], 0)
        self.assertFalse((self.root / 'synthetic-note/media-manifest.json').exists())
    def test_image_missing_url_is_not_silently_skipped(self):
        data = packet(); data['note']['imageList'] = [{'urlDefault': 'https://a.xhscdn.com/one'}, {}]
        with patch.object(cli, 'windows_runtime', return_value=True):
            with self.assertRaises(cli.MediaIncomplete) as error: cli.download(data, self.root)
        self.assertEqual(error.exception.coverage['expected']['image'], 2)
        self.assertEqual(error.exception.coverage['missing_sources']['image'], 1)
    def test_empty_media_refresh_keeps_prior_manifest(self):
        folder = self.root / 'synthetic-note'; folder.mkdir()
        cli.save(folder / 'media-manifest.json', {'note_id': 'synthetic-note', 'files': [{'path': 'kept.png'}]})
        before = (folder / 'media-manifest.json').read_bytes()
        with patch.object(cli, 'windows_runtime', return_value=True):
            with self.assertRaises(cli.MediaIncomplete): cli.download(packet(), self.root)
        self.assertEqual((folder / 'media-manifest.json').read_bytes(), before)
    def test_process_checks_changed_input_before_models(self):
        cli.export(packet(), self.root)
        folder = self.root / 'synthetic-note'
        (folder / 'image.png').write_bytes(b'changed')
        cli.save(folder / 'media-manifest.json', {'note_id': 'synthetic-note', 'files': [{'kind': 'image', 'path': 'image.png', 'sha256': 'wrong'}]})
        saved = cli.read(folder / 'data.json'); saved['media'] = cli.read(folder / 'media-manifest.json')['files']; cli.save(folder / 'data.json', saved)
        with patch.object(cli, 'shared_pipeline', return_value=SimpleNamespace()):
            with self.assertRaisesRegex(ValueError, 'input changed'): cli.process(SimpleNamespace(note_dir=folder))


if __name__ == '__main__': unittest.main()
