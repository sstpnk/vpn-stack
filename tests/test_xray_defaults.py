import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class XrayDefaultsTest(unittest.TestCase):
    def test_xray_uses_standard_tls_port_by_default(self):
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
        template = json.loads(
            (ROOT / "xray-config" / "config.template.json").read_text(encoding="utf-8")
        )

        self.assertIn("XRAY_PORT=443", env_example)
        self.assertIn("${XRAY_PORT:-443}:443/tcp", compose)
        self.assertIn("XRAY_PORT=${XRAY_PORT:-443}", compose)
        self.assertEqual(template["inbounds"][0]["port"], 443)


if __name__ == "__main__":
    unittest.main()
