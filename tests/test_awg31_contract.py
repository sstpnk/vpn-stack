import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

AWG31_FIELDS = [
    "S3",
    "S4",
    "HeaderProtectionKey",
    "ContentPaddingAddition",
    "RekeyAfterTime",
    "RekeyTimeout",
    "RejectAfterTime",
    "KeepaliveTimeout",
    "MaxHandshakeAttempts",
    "RandomTrailers",
    "DisableCookies",
]


class AmneziaWG31ContractTest(unittest.TestCase):
    def test_wireguard_generator_emits_full_awg31_field_set_conditionally(self):
        wireguard = (ROOT / "awg-easy" / "src" / "lib" / "WireGuard.js").read_text(encoding="utf-8")

        self.assertIn("AWG_PROTOCOL_VERSION === '3.1'", wireguard)
        self.assertIn("crypto.randomBytes(32).toString('base64')", wireguard)

        for field in AWG31_FIELDS:
            self.assertRegex(
                wireguard,
                rf"{field}\s*=\s*\$\{{(?:config\.server|masking)\.{self._camel(field)}\}}",
            )

    def test_default_31_headers_use_header_protection_compatibility_values(self):
        config = (ROOT / "awg-easy" / "src" / "config.js").read_text(encoding="utf-8")

        self.assertIn("defaultForProtocol('695467002', '1')", config)
        self.assertIn("defaultForProtocol('405207407', '2')", config)
        self.assertIn("defaultForProtocol('141743987', '3')", config)
        self.assertIn("defaultForProtocol('206219833', '4')", config)
        self.assertIn("process.env.RANDOM_TRAILERS || defaultForProtocol('off', 'on')", config)

    def test_compose_passes_awg31_contract_environment(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        self.assertIn("AWG_PROTOCOL_VERSION=${AMNEZIA_PROTOCOL_VERSION:-legacy}", compose)
        self.assertIn("HEADER_PROTECTION_KEY=${AMNEZIA_HEADER_PROTECTION_KEY:-}", compose)
        for field in AWG31_FIELDS:
            env_key = re.sub(r"(?<!^)(?=[A-Z])", "_", field).upper()
            if field in {"S3", "S4"}:
                self.assertIn(f"{field}=${{AMNEZIA_{field}:-}}", compose)
            elif field != "HeaderProtectionKey":
                self.assertRegex(compose, rf"{env_key}=\$\{{AMNEZIA_{env_key}:-")

    def test_awg_runtime_image_is_pinned_to_31_line(self):
        dockerfile = (ROOT / "awg-easy" / "Dockerfile").read_text(encoding="utf-8")

        self.assertIn("FROM amneziavpn/amneziawg-go:3.1.20260828", dockerfile)
        self.assertIn("WG_QUICK_USERSPACE_IMPLEMENTATION=amneziawg-go", dockerfile)
        self.assertIn("iptables-legacy", dockerfile)
        self.assertNotIn("FROM amneziavpn/amnezia-wg:latest", dockerfile)

    def test_admin_create_client_form_exposes_awg31_client_masking(self):
        app = (ROOT / "awg-easy" / "src" / "www" / "js" / "app.js").read_text(encoding="utf-8")
        html = (ROOT / "awg-easy" / "src" / "www" / "index.html").read_text(encoding="utf-8")

        self.assertIn("maskingDefaults.awgProtocolVersion === '3.1'", html)
        self.assertNotIn("HeaderProtectionKey", html)

        for field in [
            "s3",
            "s4",
            "contentPaddingAddition",
            "rekeyAfterTime",
            "rekeyTimeout",
            "rejectAfterTime",
            "keepaliveTimeout",
            "maxHandshakeAttempts",
            "randomTrailers",
            "disableCookies",
        ]:
            self.assertIn(field, app)
            self.assertIn(field, html)

    def test_bot_nekobox_json_preserves_awg31_fields_and_ranges(self):
        bot = (ROOT / "bot" / "src" / "bot.py").read_text(encoding="utf-8")

        for field in AWG31_FIELDS:
            self.assertIn(f'"{field}"', bot)
        self.assertIn('peer["persistent_keepalive"] = v', bot)
        self.assertNotIn('peer["persistent_keepalive"] = int(v)', bot)

    @staticmethod
    def _camel(field):
        return field[0].lower() + field[1:]


if __name__ == "__main__":
    unittest.main()
