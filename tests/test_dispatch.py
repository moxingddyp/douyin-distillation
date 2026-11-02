import importlib.util
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("dispatch",ROOT/"scripts/media.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class DispatchTests(unittest.TestCase):
    def test_platform_commands_are_separate(self):
        self.assertEqual(Path(m.command(["douyin","capture","--help"])[1]).name,"capture_one.py")
        self.assertEqual(Path(m.command(["xiaohongshu","--help"])[1]),ROOT/"platforms/xiaohongshu/cli.py")
        self.assertEqual(Path(m.command(["bilibili","capture","--help"])[1]).name,"bilibili_capture.py")
        self.assertEqual(Path(m.command(["local","demo","--output","new"])[1]).name,"pipeline.py")
    def test_reject_unscoped_or_unknown_platform(self):
        for args in (["douyin","all"],["other","capture"],["bilibili","all"]):
            with self.assertRaises(ValueError):m.command(args)
    def test_help_has_no_side_effects(self):
        self.assertIsNone(m.command(["--help"]))
if __name__=="__main__":unittest.main()
