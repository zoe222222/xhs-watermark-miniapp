import importlib.util
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
MINIPROGRAM = ROOT / "miniprogram"


def load_server_module():
    sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location("backend_server", BACKEND / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_xhs_fetcher_module():
    sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location("xhs_fetcher", BACKEND / "xhs_fetcher.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BackendContractTest(unittest.TestCase):
    def test_backend_keeps_miniprogram_api_paths(self):
        source = (BACKEND / "server.py").read_text(encoding="utf-8")

        self.assertIn("/api/health", source)
        self.assertIn("/api/version", source)
        self.assertIn("/api/fetch-xhs", source)
        self.assertIn("/api/proxy-image", source)

    def test_backend_exposes_version_payload(self):
        server = load_server_module()

        payload = server.build_version_payload()

        self.assertIs(payload["ok"], True)
        self.assertEqual(payload["service"], "xhs-watermark-backend")
        self.assertIsInstance(payload["gitCommit"], str)
        self.assertTrue(payload["gitCommit"])

    def test_backend_uses_local_git_commit_when_env_is_absent(self):
        old_values = {
            name: os.environ.pop(name, None)
            for name in ("RAILWAY_GIT_COMMIT_SHA", "GIT_COMMIT_SHA", "COMMIT_SHA")
        }
        try:
            server = load_server_module()
            payload = server.build_version_payload()
        finally:
            for name, value in old_values.items():
                if value is not None:
                    os.environ[name] = value

        expected = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip()
        self.assertEqual(payload["gitCommit"], expected)

    def test_thumbnail_image_headers_are_inline(self):
        server = load_server_module()

        headers = server.build_image_headers("image/jpeg", inline=True)

        self.assertEqual(headers["Content-Type"], "image/jpeg")
        self.assertEqual(headers["Content-Disposition"], 'inline; filename="image.jpg"')

    def test_download_image_headers_remain_attachment(self):
        server = load_server_module()

        headers = server.build_image_headers("image/png", inline=False)

        self.assertEqual(headers["Content-Type"], "image/png")
        self.assertEqual(headers["Content-Disposition"], 'attachment; filename="image.png"')


class MiniProgramGalleryContractTest(unittest.TestCase):
    def test_gallery_downloads_jpeg_compatible_images(self):
        source = (MINIPROGRAM / "pages" / "gallery" / "gallery.js").read_text(encoding="utf-8")

        self.assertIn("proxyUrl:   base + '&fmt=jpeg'", source)
        self.assertNotIn("proxyUrl:   base + '&fmt=png'", source)


class XhsFetcherTest(unittest.TestCase):
    def test_extract_note_url_accepts_xhslink_cn_share_text(self):
        fetcher = load_xhs_fetcher_module()

        text = "壁纸合集 | 梦幻蓝 http://xhslink.cn/o/2szHj741DvS 先复制再进入【小红书】"

        self.assertEqual(
            fetcher.extract_note_url(text),
            "http://xhslink.cn/o/2szHj741DvS",
        )

    def test_fetch_images_rejects_xiaohongshu_404_pages(self):
        fetcher = load_xhs_fetcher_module()

        def fake_fetch_page(_url, timeout=20):
            return (
                "https://www.xiaohongshu.com/404?source=/explore/deadbeef",
                '<meta property="og:image" content="https://picasso-static.xiaohongshu.com/e-platform/404.png">',
            )

        original_fetch_page = fetcher.fetch_page
        fetcher.fetch_page = fake_fetch_page
        try:
            result = fetcher.fetch_images("https://www.xiaohongshu.com/explore/deadbeef")
        finally:
            fetcher.fetch_page = original_fetch_page

        self.assertFalse(result["ok"])
        self.assertIn("链接不可访问", result["error"])

    def test_proxy_image_detects_avif_content(self):
        fetcher = load_xhs_fetcher_module()

        class FakeResult:
            returncode = 0
            stdout = b"\x00\x00\x00\x18ftypavif\x00\x00\x00\x00"
            stderr = b""

        original_run = fetcher.subprocess.run
        fetcher.subprocess.run = lambda *args, **kwargs: FakeResult()
        try:
            _data, content_type = fetcher.proxy_image("https://ci.xiaohongshu.com/test")
        finally:
            fetcher.subprocess.run = original_run

        self.assertEqual(content_type, "image/avif")
