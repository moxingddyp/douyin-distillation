"""Read one authorized Xiaohongshu note on Windows; export and process local media."""
import argparse
import asyncio
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from unittest.mock import patch
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

NOTE_ID = re.compile(r'^[A-Za-z0-9_-]+$')
PAGE_HOSTS = {'xiaohongshu.com', 'www.xiaohongshu.com', 'xhslink.com', 'www.xhslink.com', 'xhslink.cn', 'www.xhslink.cn'}


class WorkflowError(ValueError, RuntimeError):
    pass


class MediaIncomplete(WorkflowError):
    def __init__(self, coverage):
        self.coverage = coverage
        super().__init__('Media source incomplete; no new media manifest was written. Obtain a complete note response and retry; existing media is retained.')


def windows_runtime():
    return os.name == 'nt'


def note_folder(output_root, ident):
    root = Path(output_root).resolve()
    return inside(root, ident)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def inside(root, relative):
    root = Path(root).resolve()
    relative = Path(relative)
    result = (root / relative).resolve()
    if relative.is_absolute() or not result.is_relative_to(root) or result == root:
        raise WorkflowError('Media path is outside its note directory')
    return result


def clean_text(value):
    if not isinstance(value, str):
        return value
    def url(match):
        parsed = urlsplit(match.group(0))
        if (parsed.hostname or '').endswith('.xhscdn.com'):
            return '[temporary media URL omitted]'
        private_keys = {'xsec_token', 'xsec_source', 'signature', 'sig', 'authorization', 'cookie', 'access_token', 'session', 'sessionid', 'token', 'expires', 'policy', 'key-pair-id'}
        query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k.lower() not in private_keys and not k.lower().startswith(('x-amz-', 'x-goog-'))]
        netloc = parsed.netloc.rsplit('@', 1)[-1]
        return urlunsplit((parsed.scheme, netloc, parsed.path, urlencode(query), parsed.fragment))
    value = re.sub(r'https?://[^\s<>\]\)]+', url, value)
    return re.sub(r'(?i)\b(xsec_token|signature|authorization|cookie|access_token|session(?:id)?)\s*[=:]\s*[^\s;,]+', r'\1=[private]', value)


def scalar_map(value, keys):
    return {key: clean_text(value[key]) for key in keys if key in value and isinstance(value[key], (str, int, float, bool, type(None)))}


def packet_note(packet):
    for _ in range(6):
        if isinstance(packet, dict) and isinstance(packet.get('note'), dict):
            nid = packet['note'].get('noteId')
            if not isinstance(nid, str) or not NOTE_ID.fullmatch(nid):
                raise WorkflowError('Invalid note identity')
            return packet, packet['note']
        if not isinstance(packet, dict) or 'data' not in packet:
            break
        packet = packet['data']
    raise WorkflowError('No note object')


def comments(rows):
    found = {}
    def walk(items, parent=None):
        for item in items:
            ident = item.get('id')
            if not isinstance(ident, str) or not ident:
                raise WorkflowError('Comment requires a stable ID')
            if ident in found and found[ident]['parent_id'] != parent:
                raise WorkflowError('Comment has conflicting parents')
            if ident not in found:
                found[ident] = dict(scalar_map(item, ('id', 'content', 'likeCount', 'createTime')), parent_id=parent,
                                    author=scalar_map(item.get('userInfo') or {}, ('userId', 'nickname', 'nickName')))
            walk(item.get('subComments') or [], ident)
    walk(rows)
    return list(found.values())


def render(folder, record):
    lines = ['# ' + record['title'], '', record['source_url'], '', '## Content / 正文', '', record['body'], '',
             '## Interaction snapshot / 互动快照', '', 'Captured / 采集时间: ' + record['captured_at']]
    for key in ('likedCount', 'collectedCount', 'commentCount', 'sharedCount'):
        value = record['interaction_snapshot'].get(key)
        if key == 'sharedCount' and value is None:
            value = record['interaction_snapshot'].get('shareCount')
        lines.append(f'- {key}: {value if value not in (None, "") else "not obtained / 未取得"}')
    lines += ['', '## Local media / 本地媒体', '']
    for entry in record['media']:
        target = inside(folder, entry['path'])
        if not target.is_file() or sha(target) != entry['sha256']:
            raise WorkflowError('Media bytes do not match their manifest')
        lines.append(('!' if entry['kind'] == 'image' else '') + f'[{entry["path"]}]({entry["path"]})')
    lines += ['', '## Comments / 评论', '', f'Obtained / 已取得: {len(record["comments"])}; ' + record['coverage']['stop_reason'],
              'This is not a complete-comment claim. / 不声明评论全量。', '']
    for item in record['comments']:
        lines += ['### ' + item['id'], 'Parent / 父评论: ' + str(item['parent_id']), '', item.get('content', ''), '']
    lines += ['## Machine processing / 机器处理', '', 'Machine output is not independently reviewed. / 机器输出未独立听校。']
    for name, data in record.get('machine_processing', {}).items():
        if isinstance(data, dict) and data.get('path'):
            path = inside(folder, data['path'])
            if path.is_file():
                lines.append(f'- [{name}]({data["path"]})')
    (folder / 'content.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    save(folder / 'data.json', record)


def export(packet, output_root, stop_reason='visible_sample_only'):
    packet, note = packet_note(packet)
    folder = note_folder(output_root, note['noteId'])
    folder.mkdir(parents=True, exist_ok=True)
    manifest_file = folder / 'media-manifest.json'
    media = [scalar_map(v, ('kind', 'index', 'path', 'bytes', 'sha256', 'source_locator_sha256')) for v in read(manifest_file)['files']] if manifest_file.exists() else []
    if manifest_file.exists() and read(manifest_file).get('note_id') != note['noteId']:
        raise WorkflowError('Media belongs to another note')
    fresh = comments((packet.get('comments') or {}).get('list') or [])
    previous_file = folder / 'data.json'
    previous = read(previous_file) if previous_file.exists() else None
    if previous and previous.get('note_id') != note['noteId']:
        raise WorkflowError('Existing note identity differs')
    if previous:
        save(inside(folder, 'snapshots/' + sha(previous_file) + '.json'), previous)
    # Retained comments keep their original capture time; they are not fresh observations.
    captured = datetime.now(timezone.utc).isoformat()
    for item in fresh:
        item['observed_at'] = captured
    merged = {v['id']: v for v in (previous or {}).get('comments', [])}
    for item in fresh:
        merged[item['id']] = item
    record = {'schema_version': 1, 'note_id': note['noteId'], 'source_url': 'https://www.xiaohongshu.com/explore/' + note['noteId'],
              'captured_at': captured, 'title': clean_text(note.get('title', '')), 'body': clean_text(note.get('desc', '')),
              'author': scalar_map(note.get('user') or {}, ('userId', 'nickname', 'nickName')),
              'published_at_raw': scalar_map(note, ('time',)).get('time'), 'type': scalar_map(note, ('type',)).get('type'),
              'interaction_snapshot': scalar_map(note.get('interactInfo') or {}, ('likedCount', 'collectedCount', 'commentCount', 'sharedCount', 'shareCount')),
              'media': media, 'comments': list(merged.values()),
              'coverage': {'current_top_level': sum(c['parent_id'] is None for c in fresh), 'current_replies': sum(c['parent_id'] is not None for c in fresh),
                           'retained_from_previous': sum(k not in {v['id'] for v in fresh} for k in merged),
                           'upstream_has_more': (packet.get('comments') or {}).get('hasMore'), 'stop_reason': clean_text(stop_reason), 'all_comments_verified': False},
              'machine_processing': (previous or {}).get('machine_processing', {}) if (previous or {}).get('media', []) == media else {}}
    render(folder, record)
    return record


def allowed_media(url):
    p = urlsplit(url)
    return p.scheme == 'https' and bool(p.hostname) and p.hostname.endswith('.xhscdn.com') and not p.username and not p.password and p.port in (None, 443)


class CDNRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_media(newurl):
            raise WorkflowError('Media redirect left approved CDN')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def media_jobs(note):
    jobs = []
    for index, image in enumerate(note.get('imageList') or [], 1):
        url = image.get('urlDefault') or image.get('urlPre')
        if url:
            jobs.append(('image', index, url))
    streams = (((note.get('video') or {}).get('media') or {}).get('stream') or {})
    candidates = [v for rows in streams.values() for v in rows if v.get('masterUrl')]
    if candidates:
        chosen = max(candidates, key=lambda v: (v.get('videoCodec', '').lower() in ('h264', 'avc'), v.get('width', 0) * v.get('height', 0)))
        jobs.append(('video', 1, chosen['masterUrl']))
    return jobs


def media_coverage(note, jobs):
    images = len(note.get('imageList') or [])
    video = int(note.get('type') == 'video' or bool(note.get('video')))
    available = {'image': sum(kind == 'image' for kind, _, _ in jobs), 'video': sum(kind == 'video' for kind, _, _ in jobs)}
    expected = {'image': images, 'video': video}
    return {'expected': expected, 'available_urls': available, 'obtained': {'image': 0, 'video': 0},
            'missing_sources': {kind: max(expected[kind] - available[kind], 0) for kind in expected},
            'no_media_sources': not bool(jobs)}


def download(packet, output_root, max_bytes=1024 ** 3):
    if not windows_runtime():
        raise WorkflowError('Live download runs on Windows PC only')
    if max_bytes <= 0:
        raise WorkflowError('Positive byte bound required')
    _, note = packet_note(packet)
    folder = note_folder(output_root, note['noteId'])
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / 'media-manifest.json'
    old = read(manifest_path) if manifest_path.exists() else {'note_id': note['noteId'], 'files': []}
    if old['note_id'] != note['noteId']:
        raise WorkflowError('Existing media note identity differs')
    jobs = media_jobs(note)
    coverage = media_coverage(note, jobs)
    if coverage['no_media_sources'] or any(coverage['missing_sources'].values()):
        raise MediaIncomplete(coverage)
    result = []
    opener = build_opener(CDNRedirect())
    for kind, index, url in jobs:
        if not allowed_media(url):
            raise WorkflowError('Unexpected media host')
        p = urlsplit(url)
        locator = hashlib.sha256(urlunsplit((p.scheme, p.netloc, p.path, '', '')).encode()).hexdigest()
        previous = next((v for v in old['files'] if v['kind'] == kind and v['index'] == index and v.get('source_locator_sha256') == locator), None)
        if previous:
            target = inside(folder, previous['path'])
            if target.is_file() and sha(target) == previous['sha256']:
                result.append(previous)
                continue
        req = Request(url, headers={'Referer': 'https://www.xiaohongshu.com/', 'User-Agent': 'Mozilla/5.0'})
        with opener.open(req, timeout=90) as response:
            content_type = response.headers.get_content_type()
            extensions = {'image/jpeg': '.jpg', 'image/png': '.png', 'image/webp': '.webp', 'image/avif': '.avif'} if kind == 'image' else {'video/mp4': '.mp4', 'application/octet-stream': '.mp4'}
            ext = extensions.get(content_type)
            if not ext:
                raise WorkflowError('Unexpected media content type')
            directory = inside(folder, 'images' if kind == 'image' else 'video')
            directory.mkdir(exist_ok=True)
            fd, name = tempfile.mkstemp(prefix='.download-', suffix='.part', dir=directory)
            count = 0
            with os.fdopen(fd, 'wb') as target:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    count += len(block)
                    if count > max_bytes:
                        raise WorkflowError('Media exceeds explicit size bound')
                    target.write(block)
            length = response.headers.get('Content-Length')
            if count == 0 or (length and count != int(length)):
                raise WorkflowError('Empty or truncated media')
        temporary = Path(name)
        digest = sha(temporary)
        relative = f'{directory.name}/{index:03d}-{digest[:16]}{ext}'
        destination = inside(folder, relative)
        if destination.exists() and sha(destination) != digest:
            raise WorkflowError('Media destination collision')
        if destination.exists():
            temporary.unlink()
        else:
            temporary.replace(destination)
        result.append({'kind': kind, 'index': index, 'path': relative, 'bytes': count, 'sha256': digest, 'source_locator_sha256': locator})
    coverage['obtained'] = {kind: sum(v['kind'] == kind for v in result) for kind in ('image', 'video')}
    save(manifest_path, {'note_id': note['noteId'], 'files': result, 'media_coverage': coverage})
    return result


def validate_capture_paths(profile, private, output):
    profile, private, output = (Path(v).resolve() for v in (profile, private, output))
    if not profile.is_dir():
        raise WorkflowError('Use an existing manually authenticated Chrome profile')
    for a, b in ((profile, output), (private, output), (profile, private)):
        if a == b or a.is_relative_to(b) or b.is_relative_to(a):
            raise WorkflowError('Profile, private responses, and delivered output must be separate directories')
    return profile, private, output


async def capture(args):
    if not windows_runtime():
        raise WorkflowError('Live capture runs on Windows PC only')
    job = read(args.input)
    source_url = job.get('source_url', '')
    parsed = urlsplit(source_url)
    if parsed.scheme != 'https' or parsed.hostname not in PAGE_HOSTS or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise WorkflowError('Expected an HTTPS Xiaohongshu link')
    profile, private, output = validate_capture_paths(args.profile, args.private_dir, args.output_root)
    private.mkdir(parents=True, exist_ok=True)
    private.chmod(0o700)
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(str(profile), channel='chrome', headless=True, viewport={'width': 1280, 'height': 900}, timeout=25000)
        try:
            marker = private / ('session-imported-' + hashlib.sha256(str(profile).encode()).hexdigest()[:16] + '.json')
            if args.session_file and not marker.exists():
                session = read(args.session_file)
                rows = session.get('cookies', []) if isinstance(session, dict) else session
                keys = {'name', 'value', 'domain', 'path', 'expires', 'httpOnly', 'secure', 'sameSite'}
                normalized = []
                for row in rows:
                    c = {k: v for k, v in row.items() if k in keys}
                    domain = c.get('domain', '').lstrip('.')
                    if domain not in ('xiaohongshu.com', 'www.xiaohongshu.com'):
                        raise WorkflowError('Session contains an unrelated domain')
                    if c.get('sameSite') not in ('Strict', 'Lax', 'None'):
                        c.pop('sameSite', None)
                    c.setdefault('path', '/')
                    normalized.append(c)
                await context.add_cookies(normalized)
                save(marker, {'imported': True})
            page = await context.new_page()
            await page.goto(source_url, wait_until='domcontentloaded', timeout=45000)
            if urlsplit(page.url).hostname not in PAGE_HOSTS:
                raise WorkflowError('Unexpected page redirect')
            match = re.search(r'/([a-f0-9]{24})(?:[/?]|$)', page.url)
            if not match:
                raise WorkflowError('Link not resolved; user login or verification may be required')
            nid = match.group(1)
            requested = re.search(r'/([a-f0-9]{24})(?:[/?]|$)', parsed.path)
            if requested and requested.group(1) != nid:
                raise WorkflowError('Page note identity differs from requested note')
            for _ in range(15):
                if await page.locator('#captcha-verify-image, #captcha_container').count():
                    raise WorkflowError('User verification required')
                ready = await page.evaluate('id => Object.values(window.__INITIAL_STATE__?.note?.noteDetailMap || {}).some(v=>v?.note?.noteId===id)', nid)
                if ready:
                    break
                await page.wait_for_timeout(1000)
            else:
                raise WorkflowError('Note unavailable or user login required')
            for _ in range(args.comment_scrolls):
                box = page.locator('.comments-container').first
                if not await box.count():
                    break
                await box.hover(timeout=3000)
                await page.mouse.wheel(0, 650)
                await page.wait_for_timeout(1200)
            if await page.locator('#captcha-verify-image, #captcha_container').count():
                raise WorkflowError('User verification required')
            packet = await page.evaluate('''id => {
                const e=Object.values(window.__INITIAL_STATE__.note.noteDetailMap).find(v=>v?.note?.noteId===id);
                return JSON.parse(JSON.stringify({note:e.note,comments:e.comments||{list:[]}}));
            }''', nid)
            _, note = packet_note(packet)
            if note['noteId'] != nid:
                raise WorkflowError('Detail identity mismatch')
            raw = private / (nid + '-detail.json')
            save(raw, packet)
            raw.chmod(0o600)
            receipt = private / (nid + '-receipt.json')
            save(receipt, {'note_id': nid, 'authorization_reference': args.authorization_reference, 'captured_at': datetime.now(timezone.utc).isoformat()})
            receipt.chmod(0o600)
        finally:
            await context.close()
    download(packet, output, args.max_media_bytes)
    record = export(packet, output, 'visible_sample_only' if args.comment_scrolls else 'comments_not_requested')
    return {'state': 'complete', 'note_id': record['note_id'], 'media_files': len(record['media']), 'media_coverage': read(output / record['note_id'] / 'media-manifest.json')['media_coverage'], 'coverage': record['coverage'], 'browser_closed': True}


def shared_pipeline():
    file = Path(__file__).resolve().parents[2] / 'scripts/pipeline.py'
    if not file.is_file():
        raise WorkflowError('Keep this component inside the full media workflow repository')
    spec = importlib.util.spec_from_file_location('shared_media_pipeline', file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def process(args):
    pipeline = shared_pipeline()
    folder = args.note_dir.resolve()
    record = read(folder / 'data.json')
    manifest = read(folder / 'media-manifest.json')
    if manifest['note_id'] != record['note_id'] or folder.name != record['note_id']:
        raise WorkflowError('Processing note identity mismatch')
    if record.get('media') != manifest['files']:
        raise WorkflowError('Exported media mapping differs from manifest; export the current response before processing')
    for item in manifest['files']:
        media = inside(folder, item['path'])
        if not media.is_file() or sha(media) != item['sha256']:
            raise WorkflowError('Processing input changed')
    derived = inside(folder, 'derived')
    derived.mkdir(exist_ok=True)
    if args.asr and not args.model_dir:
        raise WorkflowError('--model-dir required for ASR')
    if args.ocr and not all((args.det, args.cls, args.rec, args.keys)):
        raise WorkflowError('Explicit local OCR model files and dictionary required')
    videos = [v for v in manifest['files'] if v['kind'] == 'video']
    if videos:
        video = videos[0]
        work = args.work_dir.resolve()
        if work == folder or folder.is_relative_to(work) or work.is_relative_to(folder):
            raise WorkflowError('Use a separate video-work directory')
        if work.exists():
            existing, _ = pipeline.checked_work(work)
            if existing['work_id'] != record['note_id'] or existing['source_sha256'] != video['sha256']:
                raise WorkflowError('Video work belongs to another source')
        else:
            pipeline.ingest(inside(folder, video['path']), work, record['note_id'], record['source_url'])
        if args.asr:
            pipeline.transcribe(work, args.model_dir, args.device, args.compute_type, args.language)
            target = derived / 'transcript.json'
            shutil.copy2(work / 'transcript.json', target)
            record['machine_processing']['asr'] = {'path': target.relative_to(folder).as_posix(), 'status': 'machine_unreviewed', 'source_sha256': video['sha256']}
        if args.ocr:
            pipeline.ocr(work, args.interval, args.det, args.cls, args.rec, args.keys)
            target = derived / 'video-ocr.json'
            data = read(work / 'ocr.json')
            for frame in data['frames']:
                source_frame = pipeline.within(work, frame['file'])
                destination = inside(folder, 'derived/' + frame['file'])
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_frame, destination)
                frame['file'] = destination.relative_to(folder).as_posix()
            save(target, data)
            record['machine_processing']['video_ocr'] = {'path': target.relative_to(folder).as_posix(), 'status': 'machine_unreviewed', 'source_sha256': video['sha256']}
    images = [v for v in manifest['files'] if v['kind'] == 'image']
    if args.ocr and images:
        files, hashes = pipeline.ocr_profile(args.det, args.cls, args.rec, args.keys)
        profile = {'models': hashes, 'sources': [v['sha256'] for v in images]}
        target = derived / 'image-ocr.json'
        if target.exists():
            result = read(target)
            if result.get('profile') != profile:
                raise WorkflowError('Image/model inputs changed; use a new result version')
        else:
            from rapidocr import RapidOCR
            params = {f'{part}.model_path': str(files[name].resolve()) for part, name in [('Det', 'det'), ('Cls', 'cls'), ('Rec', 'rec')]}
            params.update({'Rec.rec_keys_path': str(files['keys'].resolve()), 'EngineConfig.onnxruntime.intra_op_num_threads': 1, 'EngineConfig.onnxruntime.inter_op_num_threads': 1, 'EngineConfig.onnxruntime.use_cuda': False})
            def offline(*unused, **kwargs):
                raise WorkflowError('OCR is offline-only; prepare missing assets explicitly')
            with ExitStack() as stack:
                stack.enter_context(patch('socket.socket.connect', offline))
                stack.enter_context(patch('socket.create_connection', offline))
                engine = RapidOCR(params=params)
                rows = []
                for item in images:
                    output = engine(str(inside(folder, item['path'])))
                    rows.append({'path': item['path'], 'source_sha256': item['sha256'], 'texts': [{'text': clean_text(t), 'score': float(s)} for t, s in zip(output.txts or [], output.scores or [])]})
            result = {'status': 'machine_unreviewed', 'profile': profile, 'images': rows}
            save(target, result)
        record['machine_processing']['image_ocr'] = {'path': target.relative_to(folder).as_posix(), 'status': 'machine_unreviewed'}
    if args.asr and not videos:
        raise WorkflowError('No video/audio media to transcribe')
    render(folder, record)
    return {'note_id': record['note_id'], 'machine_processing': record['machine_processing']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    c = sub.add_parser('capture')
    c.add_argument('--input', type=Path, required=True, help='Private JSON with source_url; do not put signed links in shell history')
    c.add_argument('--profile', type=Path, required=True)
    c.add_argument('--private-dir', type=Path, required=True)
    c.add_argument('--output-root', type=Path, required=True)
    c.add_argument('--session-file', type=Path)
    c.add_argument('--authorization-reference', required=True)
    c.add_argument('--comment-scrolls', type=int, choices=range(4), default=0)
    c.add_argument('--max-media-bytes', type=int, default=1024 ** 3)
    e = sub.add_parser('export')
    e.add_argument('--input', type=Path, required=True)
    e.add_argument('--output-root', type=Path, required=True)
    e.add_argument('--stop-reason', default='imported_snapshot_only')
    p = sub.add_parser('process')
    p.add_argument('--note-dir', type=Path, required=True)
    p.add_argument('--work-dir', type=Path, required=True)
    p.add_argument('--asr', action='store_true')
    p.add_argument('--ocr', action='store_true')
    p.add_argument('--model-dir', type=Path)
    p.add_argument('--device', choices=['cpu', 'cuda'], default='cpu')
    p.add_argument('--compute-type', default='int8')
    p.add_argument('--language', default='zh')
    p.add_argument('--interval', type=float, default=15)
    for key in ('det', 'cls', 'rec', 'keys'):
        p.add_argument('--' + key, type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'capture':
            result = asyncio.run(asyncio.wait_for(capture(args), timeout=420))
        elif args.command == 'export':
            record = export(read(args.input), args.output_root, args.stop_reason)
            result = {'note_id': record['note_id'], 'coverage': record['coverage']}
        else:
            if not args.asr and not args.ocr:
                parser.error('Select --asr and/or --ocr')
            result = process(args)
        print(json.dumps(result, ensure_ascii=True))
    except Exception as exc:
        detail = str(exc) if isinstance(exc, WorkflowError) else ('Required local file is missing; check the selected input/profile/model paths' if isinstance(exc, FileNotFoundError) else 'Required Python dependency is missing; install the documented dependencies in this environment' if isinstance(exc, ImportError) else 'Operation timed out; close the dedicated Chrome window and manually check login/verification before retrying' if 'Timeout' in type(exc).__name__ else 'Input or dependency failed; check the response schema, local model files and browser state; raw browser errors are omitted to protect signed URLs')
        result = {'state': 'partial' if isinstance(exc, MediaIncomplete) else 'failed', 'error_type': type(exc).__name__, 'detail': detail}
        if isinstance(exc, MediaIncomplete):
            result['media_coverage'] = exc.coverage
        print(json.dumps(result))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
