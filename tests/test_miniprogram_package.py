import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MINIPROGRAM = ROOT / "miniprogram"
PROJECT_CONFIG = MINIPROGRAM / "project.config.json"
MAX_MAIN_PACKAGE_BYTES = 2 * 1024 * 1024


class MiniprogramPackageTest(unittest.TestCase):
    def test_main_package_stays_under_wechat_limit(self):
        config = json.loads(PROJECT_CONFIG.read_text(encoding="utf-8"))
        ignored_files = {
            item["value"]
            for item in config.get("packOptions", {}).get("ignore", [])
            if item.get("type") == "file"
        }

        packaged_files = [
            path
            for path in MINIPROGRAM.rglob("*")
            if path.is_file()
            and path.relative_to(MINIPROGRAM).as_posix() not in ignored_files
        ]
        package_size = sum(path.stat().st_size for path in packaged_files)

        self.assertLessEqual(
            package_size,
            MAX_MAIN_PACKAGE_BYTES,
            f"main package is {package_size} bytes, exceeding WeChat's 2 MB limit",
        )


if __name__ == "__main__":
    unittest.main()
