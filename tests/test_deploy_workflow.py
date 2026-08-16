import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-backend.yml"


class DeployWorkflowTest(unittest.TestCase):
    def test_backend_workflow_has_safe_live_deployment_contract(self):
        self.assertTrue(WORKFLOW.exists(), "backend deployment workflow is missing")

        result = subprocess.run(
            ["ruby", "-e", "require 'yaml'; YAML.load_file(ARGV[0])", str(WORKFLOW)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

        source = WORKFLOW.read_text(encoding="utf-8")
        required_fragments = (
            "workflow_dispatch:",
            "backend/**",
            "TENCENT_HOST",
            "TENCENT_USER",
            "TENCENT_SSH_PRIVATE_KEY",
            "deploy/Caddyfile",
            "docker compose up -d --build",
            "/api/version",
            "EXPECTED_COMMIT",
        )
        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

    def test_dockerfile_uses_tencent_mirrors_for_server_builds(self):
        dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("mirrors.tencentyun.com/debian", dockerfile)
        self.assertIn("mirrors.cloud.tencent.com/pypi/simple", dockerfile)


if __name__ == "__main__":
    unittest.main()
