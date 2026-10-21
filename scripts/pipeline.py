#!/usr/bin/env python3
"""Local, explicit-stage evidence pipeline. No network or model download."""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import struct
import tempfile
import wave
from contextlib import ExitStack
from unittest.mock import patch
from pathlib import Path

VERSION = "0.1.0-preparation"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def within(root, relative):
    root = Path(root).resolve()
    candidate = (root / relative).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError('Path escapes work directory')
    return candidate


def media_info(path):
    """WAV via stdlib; videos/audio via optional PyAV, full decode."""
    path = Path(path)
    if path.suffix.lower() == '.wav':
        with wave.open(str(path)) as stream:
            samples = stream.getnframes()
            frames = 0
            while True:
                block = stream.readframes(8192)
                if not block:
                    break
                frames += len(block) // (stream.getnchannels() * stream.getsampwidth())
            if frames != samples or frames == 0:
                raise ValueError('Empty or truncated WAV')
            return {'duration_s': samples / stream.getframerate(), 'audio_decoded_samples': frames,
                    'video_decoded_frames': 0, 'audio_tracks': 1, 'decoder': 'stdlib-wave'}
    import av
    with av.open(str(path)) as container:
        audio = len(container.streams.audio)
        duration = container.duration / 1000000 if container.duration else None
        counts = {'audio': 0, 'video': 0}
        for frame in container.decode():
            kind = 'audio' if isinstance(frame, av.AudioFrame) else 'video'
            counts[kind] += 1
    if not duration or not math.isfinite(duration) or not any(counts.values()):
        raise ValueError('Media cannot be completely decoded')
    return {'duration_s': duration, 'audio_tracks': audio,
            'audio_decoded_frames': counts['audio'], 'video_decoded_frames': counts['video'], 'decoder': 'pyav'}


def checked_work(root):
    manifest = read(root / 'manifest.json')
    media = within(root, manifest['media'])
    if sha(media) != manifest['source_sha256']:
        raise ValueError('Source changed; create a new work/version, do not reuse checkpoints')
    return manifest, media


def ingest(media, output, ident, source_url, fixture=False):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', ident):
        raise ValueError('Invalid stable work ID')
    media = Path(media).resolve()
    output = Path(output)
    if output.exists():
        raise ValueError('Refusing overwrite; use a new work directory')
    info = media_info(media)
    output.mkdir(parents=True)
    target = output / ('source' + media.suffix.lower())
    shutil.copyfile(media, target)
    manifest = {'schema': 1, 'tool_version': VERSION, 'work_id': ident,
                'source_url': source_url, 'media': target.name, 'source_sha256': sha(target),
                'media_info': info, 'fixture': fixture, 'status': 'media_verified'}
    save(output / 'manifest.json', manifest)
    return manifest


def validate_segments(data, manifest):
    if data.get('source_sha256') != manifest['source_sha256']:
        raise ValueError('Transcript source hash mismatch')
    rows = data.get('segments')
    if not isinstance(rows, list):
        raise ValueError('Segments must be a list')
    duration = manifest['media_info']['duration_s']
    for row in rows:
        start, end = row['start'], row['end']
        if not all(isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v) for v in (start, end)):
            raise ValueError('Non-finite timestamp')
        if start < 0 or end <= start or end > duration + .5 or not isinstance(row['text'], str):
            raise ValueError('Invalid transcript boundary/text; quarantine instead of adoption')
    return rows


def transcribe(root, model, device, compute, language):
    manifest, media = checked_work(root)
    if not manifest['media_info']['audio_tracks']:
        raise ValueError('No audio track')
    profile = {'engine': 'faster-whisper', 'model_tree_sha256': model_digest(model),
               'device': device, 'compute_type': compute, 'language': language}
    output = root / 'transcript.json'
    if output.exists():
        previous = read(output)
        validate_segments(previous, manifest)
        if previous.get('profile') != profile or previous.get('fixture'):
            raise ValueError('Different profile/fixture checkpoint: use a new work directory')
        return {'reused': True, 'segments': len(previous['segments'])}
    from faster_whisper import WhisperModel
    engine = WhisperModel(str(model), device=device, compute_type=compute, local_files_only=True, cpu_threads=1)
    rows, info = engine.transcribe(str(media), language=language, beam_size=5,
                                  vad_filter=True, condition_on_previous_text=False)
    data = {'source_sha256': manifest['source_sha256'], 'fixture': False, 'profile': profile,
            'status': 'machine_unreviewed', 'language': info.language,
            'segments': [{'start': s.start, 'end': s.end, 'text': s.text.strip()} for s in rows]}
    validate_segments(data, manifest)
    save(output, data)
    return {'reused': False, 'segments': len(data['segments'])}


def model_digest(path):
    path = Path(path).resolve()
    if not path.is_dir() or not (path / 'model.bin').is_file():
        raise ValueError('Provide an existing local CTranslate2 model directory with model.bin')
    digest = hashlib.sha256()
    for entry in sorted(p for p in path.rglob('*') if p.is_file()):
        digest.update(entry.relative_to(path).as_posix().encode())
        digest.update(sha(entry).encode())
    return digest.hexdigest()


def ocr_profile(det, cls, rec, keys):
    files = {'det': Path(det), 'cls': Path(cls), 'rec': Path(rec), 'keys': Path(keys)}
    if any(not p.is_file() or p.stat().st_size == 0 for p in files.values()):
        raise ValueError('All local OCR det/cls/rec models and character dictionary must exist')
    return files, {name: sha(path) for name, path in files.items()}


def ocr(root, interval, det, cls, rec, keys):
    manifest, media = checked_work(root)
    if interval <= 0 or not math.isfinite(interval):
        raise ValueError('Interval must be finite and positive')
    files, hashes = ocr_profile(det, cls, rec, keys)
    output = root / 'ocr.json'
    if output.exists():
        data = read(output)
        validate_ocr(data, manifest, root)
        if data.get('sample_interval_s') != interval or data.get('model_hashes') != hashes or data.get('fixture'):
            raise ValueError('OCR profile changed; use new work directory')
        return {'reused': True, 'frames': len(data['frames'])}
    if (root / 'frames').exists():
        raise ValueError('Uncommitted frame directory exists; preserve it and use a new work directory')
    # All asset checks precede imports/initialization. Refuse any hidden download.
    import av
    from rapidocr import RapidOCR
    params = {f'{part}.model_path': str(files[name].resolve())
              for part, name in [('Det', 'det'), ('Cls', 'cls'), ('Rec', 'rec')]}
    params.update({'Rec.rec_keys_path': str(files['keys'].resolve()),
                   'EngineConfig.onnxruntime.intra_op_num_threads': 1,
                   'EngineConfig.onnxruntime.inter_op_num_threads': 1,
                   'EngineConfig.onnxruntime.use_cuda': False})
    def deny_network(*args, **kwargs):
        raise RuntimeError('OCR is offline-only; prepare missing assets explicitly')
    offline = ExitStack()
    offline.enter_context(patch('socket.socket.connect', deny_network))
    offline.enter_context(patch('socket.create_connection', deny_network))
    try:
        engine = RapidOCR(params=params)
    except BaseException:
        offline.close()
        raise
    frames = []
    next_second = 0.0
    try:
      with av.open(str(media)) as container:
        for frame in container.decode(video=0):
            second = float(frame.time or 0)
            if second < next_second:
                continue
            image = frame.to_image()
            name = f'frames/frame-{len(frames):05d}.png'
            within(root, name).parent.mkdir(exist_ok=True)
            image.save(root / name)
            result = engine(frame.to_ndarray(format='bgr24'))
            frames.append({'second': second, 'file': name, 'sha256': sha(root / name),
                           'texts': [{'text': t, 'score': float(s)} for t, s in zip(result.txts or [], result.scores or [])]})
            next_second = second + interval
    finally:
        offline.close()
    data = {'source_sha256': manifest['source_sha256'], 'fixture': False,
            'status': 'machine_unreviewed', 'sample_interval_s': interval,
            'engine': 'rapidocr', 'model_hashes': hashes, 'frames': frames}
    validate_ocr(data, manifest, root)
    save(output, data)
    return {'reused': False, 'frames': len(frames)}


def validate_ocr(data, manifest, root):
    if data.get('source_sha256') != manifest['source_sha256'] or not isinstance(data.get('frames'), list):
        raise ValueError('OCR manifest mismatch')
    for frame in data['frames']:
        if not 0 <= frame['second'] <= manifest['media_info']['duration_s'] + .5:
            raise ValueError('OCR timestamp outside source')
        if sha(within(root, frame['file'])) != frame['sha256']:
            raise ValueError('OCR frame missing/changed')


def read_packet(root, section, start=0, end=float('inf')):
    manifest, _ = checked_work(root)
    if section == 'transcript':
        data = read(root / 'transcript.json')
        rows = validate_segments(data, manifest)
        return {'work_id': manifest['work_id'], 'fixture': data.get('fixture', False),
                'segments': [r for r in rows if r['end'] > start and r['start'] < end]}
    if section == 'ocr':
        data = read(root / 'ocr.json')
        validate_ocr(data, manifest, root)
        return {'work_id': manifest['work_id'], 'fixture': data.get('fixture', False),
                'frames': [r for r in data['frames'] if start <= r['second'] <= end]}
    data = checked_comments(root, manifest)
    # Selected scoped comments: account IDs/nicknames are deliberately not exported.
    return {'captured_count': len(data['comments']), 'platform_total_verified': False,
            'comments': [{'text': r['text'], 'is_reply': bool(r.get('is_reply'))} for r in data['comments']]}


def checked_comments(root, manifest):
    data = read(root / 'comments.json')
    if data.get('work_id') != manifest['work_id'] or data.get('source_sha256') != manifest['source_sha256']:
        raise ValueError('Comments belong to a different work/source')
    if not isinstance(data.get('comments'), list) or any(not isinstance(r.get('text'), str) for r in data['comments']):
        raise ValueError('Invalid comments')
    return data


def validate_review(root, allow_fixture=False):
    manifest, _ = checked_work(root)
    transcript = read(root / 'transcript.json')
    validate_segments(transcript, manifest)
    ocr_data = read(root / 'ocr.json')
    validate_ocr(ocr_data, manifest, root)
    review = read(root / 'review.json')
    comments = checked_comments(root, manifest)
    fixture = any(x.get('fixture', False) for x in (manifest, transcript, ocr_data, review, comments))
    if fixture and not allow_fixture:
        raise ValueError('Fixture never counts as real content validation')
    if review.get('source_sha256') != manifest['source_sha256']:
        raise ValueError('Review source mismatch')
    for key in ('key_frames_reviewed', 'conclusions_traceable', 'captured_comments_reviewed'):
        if review.get(key) is not True:
            raise ValueError('Review gate missing: ' + key)
    if review.get('captured_comment_count') != len(comments['comments']):
        raise ValueError('Captured comment count mismatch')
    audio = review.get('independent_audio_reviewed') is True
    if not audio:
        accepted = review.get('audio_acceptance', {})
        if not (accepted.get('mode') == 'crosschecked_sources_with_audio_exclusions'
                and accepted.get('authorization_reference') and accepted.get('audio_only_items_excluded') is True):
            raise ValueError('Audio review or explicit scoped acceptance required')
        exclusions = within(root, accepted['exclusions_file'])
        if not exclusions.is_file() or not exclusions.read_text(encoding='utf-8').strip():
            raise ValueError('Missing audio exclusions')
    if not review.get('reviewer') or review.get('remaining_gates') != []:
        raise ValueError('Reviewer and completed gates required')
    frames = review.get('reviewed_frames', [])
    if not frames:
        raise ValueError('No visually reviewed frame evidence')
    for frame in frames:
        if sha(within(root, frame['file'])) != frame['sha256']:
            raise ValueError('Reviewed frame changed')
    sources = review.get('sources', [])
    if not sources or any(not r.get('url', '').startswith('https://') or not r.get('checked_claim') for r in sources):
        raise ValueError('Missing actually consulted primary sources/claim mapping')
    for name in ('note.md', 'methods.md'):
        if not (root / name).is_file() or not (root / name).read_text(encoding='utf-8').strip():
            raise ValueError('Missing note/method integration')
    return {'record_checks_passed': True, 'fixture': fixture,
            'semantic_truth_verified_by_program': False, 'work_id': manifest['work_id'],
            'source_sha256': manifest['source_sha256']}


def make_demo(output):
    output = Path(output)
    if output.exists():
        raise ValueError('Refusing overwrite')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        media = Path(temporary) / 'synthetic-tone.wav'
        with wave.open(str(media), 'wb') as wav:
            wav.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
            wav.writeframes(b''.join(struct.pack('<h', int(4000 * math.sin(2 * math.pi * 440 * i / 16000))) for i in range(32000)))
        manifest = ingest(media, output, 'demo-local', 'https://example.org/self-made-demo', fixture=True)
    # Explicit synthetic records exercise gates; this tone has no speech.
    save(output / 'transcript.json', {'fixture': True, 'source_sha256': manifest['source_sha256'],
         'status': 'fixture-not-model-output', 'segments': [{'start': 0, 'end': 1, 'text': '合成示例，不是音频转写。'}]})
    frame = output / 'frame.ppm'
    frame.write_bytes(b'P6\n2 2\n255\n' + bytes([60, 180, 220]) * 4)
    evidence = {'second': 0, 'file': 'frame.ppm', 'sha256': sha(frame)}
    save(output / 'ocr.json', {'fixture': True, 'source_sha256': manifest['source_sha256'],
         'frames': [{**evidence, 'texts': [{'text': '合成OCR占位', 'score': 1.0}]}]})
    save(output / 'comments.json', {'fixture': True, 'work_id': manifest['work_id'],
         'source_sha256': manifest['source_sha256'], 'comments': [{'text': '虚构问题：输入是什么？', 'is_reply': False}]})
    save(output / 'review.json', {'fixture': True, 'source_sha256': manifest['source_sha256'],
         'reviewer': 'synthetic-fixture', 'key_frames_reviewed': True, 'conclusions_traceable': True,
         'captured_comments_reviewed': True, 'captured_comment_count': 1, 'independent_audio_reviewed': True,
         'remaining_gates': [], 'reviewed_frames': [evidence],
         'sources': [{'url': 'https://example.org/synthetic-source', 'checked_claim': '合成校验字段，不代表实际访问'}]})
    (output / 'note.md').write_text('# 合成单条笔记\n仅演示原话、帧证据、来源和推断分开记录；不存在真实作者。\n', encoding='utf-8')
    (output / 'methods.md').write_text('# 合成方法整合\n输入：自制正弦波；步骤：完整解码、哈希、结构测试；输出：校验报告。\n不包含真实ASR/OCR推断。\n', encoding='utf-8')
    save(output / 'validation.json', validate_review(output, allow_fixture=True))
    return {'demo': 'synthetic-only', 'duration_s': 2, 'actual_model_inference': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    demo = commands.add_parser('demo'); demo.add_argument('--output', type=Path, required=True)
    imp = commands.add_parser('ingest')
    imp.add_argument('--media', type=Path, required=True); imp.add_argument('--output', type=Path, required=True)
    imp.add_argument('--id', required=True); imp.add_argument('--source-url', required=True)
    for name in ('verify-media', 'asr', 'ocr', 'read', 'validate'):
        sub = commands.add_parser(name); sub.add_argument('--work', type=Path, required=True)
        if name == 'asr':
            sub.add_argument('--model-dir', type=Path, required=True)
            sub.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
            sub.add_argument('--compute-type', default='int8'); sub.add_argument('--language', default='zh')
        if name == 'ocr':
            sub.add_argument('--interval', type=float, default=15)
            for part in ('det', 'cls', 'rec', 'keys'):
                sub.add_argument('--' + part, type=Path, required=True)
        if name == 'read':
            sub.add_argument('--section', choices=['transcript', 'ocr', 'comments'], required=True)
            sub.add_argument('--start', type=float, default=0); sub.add_argument('--end', type=float, default=float('inf'))
        if name == 'validate': sub.add_argument('--allow-fixture', action='store_true')
    args = parser.parse_args()
    if args.command == 'demo': result = make_demo(args.output)
    elif args.command == 'ingest': result = ingest(args.media, args.output, args.id, args.source_url)
    elif args.command == 'verify-media':
        manifest, media = checked_work(args.work); result = media_info(media)
    elif args.command == 'asr': result = transcribe(args.work, args.model_dir, args.device, args.compute_type, args.language)
    elif args.command == 'ocr': result = ocr(args.work, args.interval, args.det, args.cls, args.rec, args.keys)
    elif args.command == 'read': result = read_packet(args.work, args.section, args.start, args.end)
    else: result = validate_review(args.work, args.allow_fixture)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
