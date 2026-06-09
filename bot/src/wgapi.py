import os
import requests


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
        return self._request("GET", "/api/wireguard/client").json()

    def create_client(self, name: str):
        clients_before = {client["id"] for client in self.list_clients()}
        result = self._request(
            "POST",
            "/api/wireguard/client",
            json={"name": name, "expiresAt": None},
        ).json()

        if result.get("id") or result.get("clientId"):
            return result

        # Older wg-easy API versions only return {"success": true}.
        created = [
            client
            for client in self.list_clients()
            if client["id"] not in clients_before and client.get("name") == name
        ]
        if len(created) != 1:
            raise RuntimeError("Peer was created, but its config could not be identified")
        return created[0]

    def delete_client(self, client_id):
        return self._request("DELETE", f"/api/wireguard/client/{client_id}").json()

    def get_client(self, client_id) -> dict:
        return self._request("GET", f"/api/wireguard/client/{client_id}").json()

    def rename_client(self, client_id, new_name: str):
        c = self.get_client(client_id)
        skip = {"id", "userId", "interfaceId", "publicKey", "createdAt", "updatedAt", "endpoint"}
        payload = {k: v for k, v in c.items() if k not in skip}
        payload["name"] = new_name
        return self._request("POST", f"/api/wireguard/client/{client_id}", json=payload).json()

    def get_client_config(self, client_id) -> tuple[bytes, str]:
        """Returns (config_bytes, filename)."""
        resp = self._request("GET", f"/api/wireguard/client/{client_id}/configuration")
        cd = resp.headers.get("Content-Disposition", "")
        filename = f"peer-{client_id}.conf"
        if 'filename="' in cd:
            filename = cd.split('filename="')[1].rstrip('"')
        return resp.content, filename
