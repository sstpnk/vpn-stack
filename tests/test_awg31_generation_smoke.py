import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


NODE_SMOKE = r"""
const fs = require('node:fs');
const path = require('node:path');

console.log = () => {};
const WireGuard = require('./awg-easy/src/services/WireGuard');

(async () => {
  const client = await WireGuard.createClient({ name: 'smoke' });
  const clientConfig = await WireGuard.getClientConfiguration({ clientId: client.id });
  const serverConfig = fs.readFileSync(path.join(process.env.WG_PATH, 'wg0.conf'), 'utf8');
  const state = JSON.parse(fs.readFileSync(path.join(process.env.WG_PATH, 'wg0.json'), 'utf8'));
  await WireGuard.Shutdown();
  process.stdout.write(JSON.stringify({ clientConfig, serverConfig, state }));
})().catch((err) => {
  process.stderr.write(`${err.stack || err}\n`);
  process.exit(1);
});
"""


class AmneziaWG31GenerationSmokeTest(unittest.TestCase):
    def test_legacy_generation_omits_awg31_fields(self):
        result = self._generate("legacy")

        for config in [result["serverConfig"], result["clientConfig"]]:
            self.assertNotIn("HeaderProtectionKey", config)
            self.assertNotIn("RandomTrailers", config)
            self.assertNotIn("DisableCookies", config)
            self.assertNotIn("S3 =", config)
            self.assertNotIn("S4 =", config)

        self.assertNotIn("awgProtocolVersion", result["state"]["server"])

    def test_awg31_generation_emits_server_and_client_contract(self):
        result = self._generate("3.1")

        expected_pairs = {
            "S3": "43",
            "S4": "12",
            "H1": "1",
            "H2": "2",
            "H3": "3",
            "H4": "4",
            "ContentPaddingAddition": "0-0",
            "RekeyAfterTime": "0-0",
            "RekeyTimeout": "0-0",
            "RejectAfterTime": "0-0",
            "KeepaliveTimeout": "0-0",
            "MaxHandshakeAttempts": "0-0",
            "RandomTrailers": "on",
            "DisableCookies": "off",
        }

        for key, value in expected_pairs.items():
            expected = f"{key} = {value}"
            self.assertIn(expected, result["serverConfig"])
            self.assertIn(expected, result["clientConfig"])

        key_line = "HeaderProtectionKey = "
        self.assertIn(key_line, result["serverConfig"])
        self.assertIn(key_line, result["clientConfig"])

        header_key = result["state"]["server"]["headerProtectionKey"]
        self.assertRegex(header_key, r"^[A-Za-z0-9+/]{43}=$")
        self.assertIn(f"HeaderProtectionKey = {header_key}", result["serverConfig"])
        self.assertIn(f"HeaderProtectionKey = {header_key}", result["clientConfig"])
        self.assertEqual(result["state"]["server"]["awgProtocolVersion"], "3.1")

    def test_enabling_awg31_on_existing_legacy_state_migrates_header_values(self):
        result = self._generate(
            "3.1",
            {
                "server": {
                    "privateKey": "server-private",
                    "publicKey": "server-public",
                    "address": "10.8.0.1",
                    "jc": 3,
                    "jmin": 50,
                    "jmax": 1000,
                    "s1": 103,
                    "s2": 21,
                    "h1": "695467002",
                    "h2": "405207407",
                    "h3": "141743987",
                    "h4": "206219833",
                },
                "clients": {},
            },
        )

        self.assertIn("H1 = 1", result["serverConfig"])
        self.assertIn("H2 = 2", result["serverConfig"])
        self.assertIn("H3 = 3", result["serverConfig"])
        self.assertIn("H4 = 4", result["serverConfig"])
        self.assertEqual(result["state"]["server"]["h1"], "1")
        self.assertEqual(result["state"]["server"]["h2"], "2")
        self.assertEqual(result["state"]["server"]["h3"], "3")
        self.assertEqual(result["state"]["server"]["h4"], "4")

    def _generate(self, protocol_version, initial_state=None):
        with tempfile.TemporaryDirectory() as tmpdir:
            if initial_state:
                Path(tmpdir, "wg0.json").write_text(json.dumps(initial_state), encoding="utf-8")
            env = os.environ.copy()
            env.update(
                {
                    "AWG_PROTOCOL_VERSION": protocol_version,
                    "WG_HOST": "vpn.example.test",
                    "WG_PATH": tmpdir,
                    "WG_DEFAULT_ADDRESS": "10.8.0.x",
                }
            )
            completed = subprocess.run(
                ["node", "-e", NODE_SMOKE],
                cwd=ROOT,
                env=env,
                check=True,
                text=True,
                capture_output=True,
            )
            return json.loads(completed.stdout)


if __name__ == "__main__":
    unittest.main()
