"""Capture one explicitly approved video through an external pinned collector.

No creator inventory, comments, stealth scripts, automatic login or CAPTCHA solver.
Original collector files and historical captures remain unchanged.
"""
import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

async def run(args):
    CRAWLER = args.crawler_dir.resolve()
    args.output = args.output.resolve()
    args.browser_profile = args.browser_profile.resolve()
    if not (CRAWLER / 'media_platform/douyin/core.py').is_file():
        raise ValueError('External collector missing; obtain under its own license')
    if not args.browser_profile.is_dir():
        raise ValueError('Use an existing manually authenticated browser profile')
    if args.output == CRAWLER or args.output.is_relative_to(CRAWLER):
        raise ValueError('Output must be outside external collector')
    args.output.mkdir(parents=True, exist_ok=False)
    os.chdir(CRAWLER)
    sys.path.insert(0, str(CRAWLER))
    import config
    config.PLATFORM = 'dy'
    config.CRAWLER_TYPE = 'detail'
    config.ENABLE_GET_COMMENTS = False
    config.ENABLE_GET_SUB_COMMENTS = False
    config.ENABLE_GET_MEDIA = True
    config.ENABLE_IP_PROXY = False
    config.SAVE_DATA_OPTION = 'jsonl'
    config.SAVE_DATA_PATH = str(args.output)
    config.MAX_CONCURRENCY_NUM = 1
    from media_platform.douyin.core import DouYinCrawler
    from store import douyin as store
    from var import crawler_type_var
    from playwright.async_api import async_playwright
    crawler = DouYinCrawler()
    report = {'at': datetime.now(timezone.utc).isoformat(), 'work_id': args.id,
              'authorization_reference': args.authorization_reference,
              'work_limit': 1, 'comments_requested': False,
              'stealth_or_captcha_automation': False}
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            str(args.browser_profile), channel='chrome', headless=True,
            viewport={'width': 1280, 'height': 900}, timeout=20000)
        try:
            crawler.browser_context = context
            crawler.context_page = await context.new_page()
            await crawler.context_page.goto('https://www.douyin.com/video/' + args.id,
                                            wait_until='domcontentloaded', timeout=45000)
            await crawler.context_page.wait_for_timeout(4000)
            report['login_confirmed'] = await crawler.context_page.evaluate("() => localStorage.getItem('HasUserLogin') === '1'")
            report['captcha_visible'] = await crawler.context_page.locator('#captcha-verify-image, #captcha_container').count() > 0
            if not report['login_confirmed'] or report['captcha_visible']:
                report['state'] = 'needs_user_login_or_verification'
            else:
                crawler.dy_client = await crawler.create_douyin_client(None)
                detail = await crawler.dy_client.get_video_by_id(args.id)
                if str(detail.get('aweme_id', '')) != args.id:
                    raise ValueError('Detail identity mismatch')
                report['detail_identity_verified'] = True
                report['video_element'] = {'duration': detail['video']['duration'] / 1000}
                crawler_type_var.set('detail')
                await store.update_douyin_aweme(aweme_item=detail)
                await crawler.download_media(aweme_item=detail)
                files = list((args.output / 'dy/media' / args.id).glob('video.*'))
                report.update(state='captured' if files else 'media_missing',
                              media_file_count=len(files),
                              media_bytes=sum(f.stat().st_size for f in files))
                if files:
                    report['media_file_relative'] = str(files[0].relative_to(args.output))
        except Exception as exc:
            report.update(state='failed', error_type=type(exc).__name__)
        finally:
            await context.close()
    (args.output / 'status.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if report.get('state') != 'captured':
        raise SystemExit(2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--crawler-dir', type=Path, required=True)
    parser.add_argument('--browser-profile', type=Path, required=True)
    parser.add_argument('--authorization-reference', required=True, help='Your scoped approval reference, not a credential')
    parser.add_argument('--accept-external-license', action='store_true')
    args = parser.parse_args()
    if not args.id.isdigit():
        parser.error('One reviewed numeric work ID is required')
    if not args.accept_external_license:
        parser.error('Read external collector license; explicit acceptance required')
    asyncio.run(asyncio.wait_for(run(args), timeout=120))
