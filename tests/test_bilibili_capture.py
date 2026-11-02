"""Offline API-fixture checks; never contacts Bilibili or opens Chrome."""
import contextlib
import io
import json
from pathlib import Path
import runpy
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'skill/distillation-workflow/scripts/bilibili_capture.py'
BV = 'BV1234567890'

class Response:
    status = 200
    headers = {}
    def __init__(self, data=None, body=b'media'):
        self.data, self.raw = data, body
    async def json(self): return {'code': 0, 'data': self.data}
    async def body(self): return self.raw
    async def dispose(self): pass

class CaptureTests(unittest.TestCase):
    def invoke(self, root, *, wrong_identity=False):
        class Request:
            async def get(self, url, **kwargs):
                if '/nav' in url: return Response({'isLogin': True})
                if '/view?' in url:
                    return Response({'bvid': 'BV0000000000' if wrong_identity else BV,
                                     'aid': 10, 'pages': [{'page': 1, 'cid': 11}],
                                     'owner': {'mid': 12, 'name': 'fixture author'}})
                if '/wbi/v2?' in url:
                    return Response({'subtitle': {'subtitles': [{'subtitle_url': 'https://fixture.test/subtitle?private=secret', 'lan': 'ai-zh'}]}})
                if '/playurl?' in url:
                    return Response({'dash': {'video': [{'height': 1080, 'width': 1920, 'codecs': 'avc', 'baseUrl': 'https://fixture.test/video?private=secret'}],
                                               'audio': [{'bandwidth': 100, 'baseUrl': 'https://fixture.test/audio?private=secret'}]}})
                if '/subtitle?' in url: return Response(body=b'{"body":[{"content":"fixture"}]}')
                return Response()
        class Context:
            request = Request()
            async def close(self): pass
        class Chromium:
            async def launch_persistent_context(self, profile, **kwargs): return Context()
        class Playwright:
            chromium = Chromium()
            async def __aenter__(self): return self
            async def __aexit__(self, *args): pass
        module = types.ModuleType('playwright.async_api')
        module.async_playwright = Playwright
        profile = root / 'profile'
        profile.mkdir(exist_ok=True)
        args = [str(SCRIPT), '--bvid', BV, '--browser-profile', str(profile), '--output', str(root / 'capture')]
        with patch.dict(sys.modules, {'playwright': types.ModuleType('playwright'), 'playwright.async_api': module}), patch.object(sys, 'argv', args):
            runpy.run_path(str(SCRIPT), run_name='__main__')

    def test_identity_and_signed_url_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.invoke(root)
            raw = (root / 'capture/capture-report.json').read_text()
            report = json.loads(raw)
            self.assertEqual(report['state'], 'downloaded_pending_decode')
            self.assertEqual((report['aid'], report['cid'], report['part']), (10, 11, 1))
            self.assertEqual(len(report['files']), 3)
            self.assertNotIn('private=secret', raw)
            self.assertNotIn('https://fixture.test', raw)

    def test_identity_mismatch_keeps_failure_and_no_media(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(RuntimeError): self.invoke(root, wrong_identity=True)
            report = json.loads((root / 'capture/capture-report.json').read_text())
            self.assertEqual(report['state'], 'failed')
            self.assertFalse((root / 'capture/video.m4s').exists())

    def test_existing_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'capture').mkdir()
            marker = root / 'capture/original.txt'
            marker.write_text('keep')
            with self.assertRaises(FileExistsError): self.invoke(root)
            self.assertEqual(marker.read_text(), 'keep')

if __name__ == '__main__': unittest.main()
