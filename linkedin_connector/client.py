"""Thin LinkedIn REST client. Every LinkedIn-specific detail lives here."""
import os
import re
from pathlib import Path

import httpx

API = "https://api.linkedin.com"
VERSION = os.getenv("LINKEDIN_API_VERSION", "202608")
MAX_POST_CHARS = 3000

# Characters LinkedIn's "little text" format treats as reserved. '#' is kept
# when it starts a hashtag so hashtags still work.
_RESERVED = re.compile(r"([\\|{}@\[\]()<>*_~]|#(?!\w))")


def escape_commentary(text: str) -> str:
    return _RESERVED.sub(r"\\\1", text)


class LinkedInError(RuntimeError):
    pass


class LinkedInClient:
    def __init__(self, token: str):
        self.http = httpx.Client(timeout=30)
        self.headers = {
            "Authorization": f"Bearer {token}",
            "LinkedIn-Version": VERSION,
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def _check(self, r: httpx.Response) -> httpx.Response:
        if r.status_code >= 400:
            raise LinkedInError(f"LinkedIn {r.status_code}: {r.text[:500]}")
        return r

    def whoami(self) -> dict:
        r = self._check(self.http.get(f"{API}/v2/userinfo", headers=self.headers))
        d = r.json()
        return {"urn": f"urn:li:person:{d['sub']}", "name": d.get("name", "")}

    def upload_image(self, owner_urn: str, path: str) -> str:
        body = {"initializeUploadRequest": {"owner": owner_urn}}
        r = self._check(self.http.post(
            f"{API}/rest/images?action=initializeUpload",
            headers=self.headers, json=body))
        value = r.json()["value"]
        data = Path(path).expanduser().read_bytes()
        self._check(self.http.put(value["uploadUrl"], content=data,
                                  headers={"Authorization": self.headers["Authorization"]}))
        return value["image"]

    def create_post(self, author_urn: str, text: str,
                    image_urn: str | None = None, alt_text: str = "") -> str:
        if len(text) > MAX_POST_CHARS:
            raise LinkedInError(f"Post is {len(text)} chars; limit is {MAX_POST_CHARS}.")
        body = {
            "author": author_urn,
            "commentary": escape_commentary(text),
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }
        if image_urn:
            body["content"] = {"media": {"id": image_urn, "altText": alt_text}}
        r = self._check(self.http.post(f"{API}/rest/posts", headers=self.headers, json=body))
        return r.headers.get("x-restli-id", "")
