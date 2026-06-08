import os
import requests


AMNEZIA_INTERFACE_DEFAULTS = (
    ("Jc", "AMNEZIA_JC", "9"),
    ("Jmin", "AMNEZIA_JMIN", "50"),
    ("Jmax", "AMNEZIA_JMAX", "1000"),
    ("S1", "AMNEZIA_S1", "33"),
    ("S2", "AMNEZIA_S2", "18"),
    ("H1", "AMNEZIA_H1", "1556852380"),
    ("H2", "AMNEZIA_H2", "854724827"),
    ("H3", "AMNEZIA_H3", "1373297535"),
    ("H4", "AMNEZIA_H4", "1443617385"),
    ("I1", "AMNEZIA_I1", "4"),
    ("I2", "AMNEZIA_I2", "4"),
    ("I3", "AMNEZIA_I3", "3"),
    ("I4", "AMNEZIA_I4", "0"),
    ("I5", "AMNEZIA_I5", "0"),
    ("MTU", "WG_MTU", "1280"),
)

SPLIT_TUNNEL_ALLOWED_IPS = (
    "0.0.0.0/5, 8.0.0.0/7, 11.0.0.0/8, 12.0.0.0/6, "
    "16.0.0.0/4, 32.0.0.0/3, 64.0.0.0/2, 128.0.0.0/3, "
    "160.0.0.0/5, 168.0.0.0/6, 172.0.0.0/12, 172.32.0.0/11, "
    "172.64.0.0/10, 172.128.0.0/9, 173.0.0.0/8, 174.0.0.0/7, "
    "176.0.0.0/4, 192.0.0.0/9, 192.128.0.0/11, 192.160.0.0/13, "
    "192.169.0.0/16, 192.170.0.0/15, 192.172.0.0/14, "
    "192.176.0.0/12, 192.192.0.0/10, 193.0.0.0/8, 194.0.0.0/7, "
    "196.0.0.0/6, 200.0.0.0/5, 208.0.0.0/4, 8.8.8.8/32, 1.1.1.1/32"
)


def _patch_client_config(config: str) -> str:
    newline = "\r\n" if "\r\n" in config else "\n"
    has_trailing_newline = config.endswith(("\r", "\n"))
    lines = config.splitlines()

    interface_values = {
        key.lower(): (key, os.getenv(env_name, default))
        for key, env_name, default in AMNEZIA_INTERFACE_DEFAULTS
    }
    section_values = {
        "interface": interface_values,
        "peer": {
            "allowedips": ("AllowedIPs", SPLIT_TUNNEL_ALLOWED_IPS),
        },
    }

    result = []
    current_section = None
    seen_keys = set()

    def add_missing_values():
        values = section_values.get(current_section)
        if not values:
            return

        trailing_blank_lines = []
        while result and not result[-1].strip():
            trailing_blank_lines.append(result.pop())

        for normalized_key, (key, value) in values.items():
            if normalized_key not in seen_keys:
                result.append(f"{key} = {value}")

        result.extend(reversed(trailing_blank_lines))

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            add_missing_values()
            current_section = stripped[1:-1].strip().lower()
            seen_keys = set()
            result.append(line)
            continue

        values = section_values.get(current_section)
        if values and "=" in line and not stripped.startswith(("#", ";")):
            key = line.split("=", 1)[0].strip().lower()
            replacement = values.get(key)
            if replacement:
                if key not in seen_keys:
                    canonical_key, value = replacement
                    result.append(f"{canonical_key} = {value}")
                    seen_keys.add(key)
                continue

        result.append(line)

    add_missing_values()
    patched = newline.join(result)
    if has_trailing_newline:
        patched += newline
    return patched


class WGEasyAPI:
    def __init__(self):
        self.base_url = os.environ["WG_EASY_URL"].rstrip("/")
        self.username = "admin"
        self.password = os.environ["WG_EASY_PASSWORD"]
        self.session = requests.Session()
        self._authenticated = False

    def login(self):
        resp = self.session.post(
            f"{self.base_url}/api/session",
            json={"password": self.password, "remember": False},
        )
        resp.raise_for_status()
        # Strip the Secure flag so cookies are sent over plain HTTP too
        # (needed when connecting directly to wg-easy inside Docker without TLS)
        for cookie in self.session.cookies:
            cookie.secure = False
        self._authenticated = True

    def _request(self, method, path, **kwargs):
        if not self._authenticated:
            self.login()
        url = f"{self.base_url}{path}"
        resp = self.session.request(method, url, **kwargs)
        if resp.status_code == 401:
            self._authenticated = False
            self.login()
            resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp

    def list_clients(self):
        return self._request("GET", "/api/client").json()

    def create_client(self, name: str):
        return self._request("POST", "/api/client", json={"name": name, "expiresAt": None}).json()

    def delete_client(self, client_id):
        return self._request("DELETE", f"/api/client/{client_id}").json()

    def get_client(self, client_id) -> dict:
        return self._request("GET", f"/api/client/{client_id}").json()

    def rename_client(self, client_id, new_name: str):
        c = self.get_client(client_id)
        skip = {"id", "userId", "interfaceId", "publicKey", "createdAt", "updatedAt", "endpoint"}
        payload = {k: v for k, v in c.items() if k not in skip}
        payload["name"] = new_name
        return self._request("POST", f"/api/client/{client_id}", json=payload).json()

    def get_client_config(self, client_id) -> tuple[bytes, str]:
        """Returns (config_bytes, filename)."""
        resp = self._request("GET", f"/api/client/{client_id}/configuration")
        cd = resp.headers.get("Content-Disposition", "")
        filename = f"peer-{client_id}.conf"
        if 'filename="' in cd:
            filename = cd.split('filename="')[1].rstrip('"')
        config = _patch_client_config(resp.content.decode("utf-8"))
        return config.encode("utf-8"), filename
