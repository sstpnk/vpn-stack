import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

AWG_DEFAULTS = {
    "AMNEZIA_PROTOCOL_VERSION": "legacy",
    "AMNEZIA_JC": "3",
    "AMNEZIA_JMIN": "50",
    "AMNEZIA_JMAX": "1000",
    "AMNEZIA_S1": "103",
    "AMNEZIA_S2": "21",
    "AMNEZIA_S3": "43",
    "AMNEZIA_S4": "12",
    "AMNEZIA_H1": "695467002",
    "AMNEZIA_H2": "405207407",
    "AMNEZIA_H3": "141743987",
    "AMNEZIA_H4": "206219833",
    "AMNEZIA_CONTENT_PADDING_ADDITION": "0-0",
    "AMNEZIA_REKEY_AFTER_TIME": "0-0",
    "AMNEZIA_REKEY_TIMEOUT": "0-0",
    "AMNEZIA_REJECT_AFTER_TIME": "0-0",
    "AMNEZIA_KEEPALIVE_TIMEOUT": "0-0",
    "AMNEZIA_MAX_HANDSHAKE_ATTEMPTS": "0-0",
    "AMNEZIA_RANDOM_TRAILERS": "off",
    "AMNEZIA_DISABLE_COOKIES": "off",
}


class AmneziaDefaultsTest(unittest.TestCase):
    def test_compose_and_env_defaults_use_valid_server_values(self):
        env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        for key, value in AWG_DEFAULTS.items():
            self.assertIn(f"{key}={value}", env_example)
            compose_key = key.removeprefix("AMNEZIA_")
            if key in {
                "AMNEZIA_H1",
                "AMNEZIA_H2",
                "AMNEZIA_H3",
                "AMNEZIA_H4",
                "AMNEZIA_S3",
                "AMNEZIA_S4",
            }:
                self.assertIn(f"{compose_key}=${{{key}:-}}", compose)
            elif key == "AMNEZIA_PROTOCOL_VERSION":
                self.assertIn(f"AWG_PROTOCOL_VERSION=${{{key}:-{value}}}", compose)
            else:
                self.assertIn(f"{compose_key}=${{{key}:-{value}}}", compose)

    def test_awg_config_fallbacks_do_not_emit_header_ranges(self):
        config = (ROOT / "awg-easy" / "src" / "config.js").read_text(encoding="utf-8")

        for key, value in AWG_DEFAULTS.items():
            if key == "AMNEZIA_PROTOCOL_VERSION":
                self.assertIn("module.exports.AWG_PROTOCOL_VERSION = AWG_PROTOCOL_VERSION", config)
                continue
            if key.startswith("AMNEZIA_") and key not in {
                "AMNEZIA_JC",
                "AMNEZIA_JMIN",
                "AMNEZIA_JMAX",
                "AMNEZIA_S1",
                "AMNEZIA_S2",
                "AMNEZIA_S3",
                "AMNEZIA_S4",
                "AMNEZIA_H1",
                "AMNEZIA_H2",
                "AMNEZIA_H3",
                "AMNEZIA_H4",
            }:
                continue
            config_key = key.removeprefix("AMNEZIA_")
            if key in {"AMNEZIA_H1", "AMNEZIA_H2", "AMNEZIA_H3", "AMNEZIA_H4"}:
                self.assertIn(f"module.exports.{config_key} = process.env.{config_key} || defaultForProtocol(", config)
                self.assertIn(repr(value), config)
            else:
                self.assertRegex(
                    config,
                    rf"module\.exports\.{config_key}\s*=\s*process\.env\.{config_key}\s*\|\|\s*['\"]?{re.escape(value)}['\"]?",
                )

        self.assertNotIn("1000-12999", config)
        self.assertNotIn("13000-24999", config)
        self.assertNotIn("25000-36999", config)
        self.assertNotIn("37000-50000", config)

    def test_setup_writes_awg_defaults_to_generated_env(self):
        setup = (ROOT / "setup.sh").read_text(encoding="utf-8")

        for key, value in AWG_DEFAULTS.items():
            self.assertIn(f"{key}={value}", setup)


if __name__ == "__main__":
    unittest.main()
