"""Unified entry point; captures run on the Windows execution machine."""
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
USAGE = """Media Collection and Distillation Workflow
Usage:
  python scripts/media.py douyin capture <capture options>
  python scripts/media.py xiaohongshu <capture|export|process> <options>
  python scripts/media.py bilibili capture <capture options>
  python scripts/media.py local <demo|ingest|asr|ocr|read|validate|verify-media> <options>
Use --help after a route for that tool's arguments. / 在路线后加--help查看参数。
"""
def command(argv):
    if not argv or argv[0] in ('-h','--help'):
        return None
    platform,*rest=argv
    if platform=='douyin':
        if not rest or rest[0]!='capture':
            raise ValueError('Use douyin capture --help; local processing uses the local route')
        return [sys.executable,str(ROOT/'scripts/capture_one.py'),*rest[1:]]
    if platform=='bilibili':
        if not rest or rest[0]!='capture':
            raise ValueError('Use bilibili capture --help')
        return [sys.executable,str(ROOT/'skill/distillation-workflow/scripts/bilibili_capture.py'),*rest[1:]]
    if platform=='xiaohongshu':
        return [sys.executable,str(ROOT/'platforms/xiaohongshu/cli.py'),*rest]
    if platform=='local':
        return [sys.executable,str(ROOT/'scripts/pipeline.py'),*rest]
    raise ValueError('Unknown route: choose douyin, bilibili, xiaohongshu or local')
def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    try:
        cmd=command(args)
    except ValueError as exc:
        print(str(exc),file=sys.stderr)
        return 2
    if cmd is None:
        print(USAGE)
        return 0
    return subprocess.run(cmd).returncode
if __name__=='__main__':
    raise SystemExit(main())
