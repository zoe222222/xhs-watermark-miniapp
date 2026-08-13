import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"


def load_server_module():
    sys.path.insert(0, str(BACKEND))
    spec = importlib.util.spec_from_file_location("backend_server", BACKEND / "server.py")
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
