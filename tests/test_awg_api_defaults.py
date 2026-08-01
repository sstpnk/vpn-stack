import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AWGAPIDefaultsTest(unittest.TestCase):
    def test_bot_uses_https_for_self_signed_awg_api(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("WG_EASY_URL=${WG_EASY_URL:-https://wg-easy:51821}", compose)
        self.assertIn("WG_EASY_VERIFY_TLS=${WG_EASY_VERIFY_TLS:-false}", compose)


if __name__ == "__main__":
    unittest.main()
