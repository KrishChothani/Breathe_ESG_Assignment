"""
Navan OAuth2 client-credentials authentication.

Token is cached in-process with a 60-second safety margin on the expiry.
All callers should use get_auth_header() rather than caching the token
themselves — this guarantees automatic refresh on expiry.
"""

import time
import logging
import requests

from .exceptions import NavanAuthError

logger = logging.getLogger(__name__)

AUTH_URL = "https://api.navan.com/auth/v1/token"
# Safety margin (seconds) to refresh before the token actually expires
_EXPIRY_BUFFER = 60


class NavanAuthClient:
    """
    Handles OAuth2 client-credentials flow for the Navan API.

    Usage::

        auth = NavanAuthClient()
        token = auth.get_access_token(client_id, client_secret)
        headers = auth.get_auth_header()
    """

    def __init__(self, auth_url: str = AUTH_URL):
        self._auth_url = auth_url
        self._access_token: str | None = None
        self._expires_at: float = 0.0        # Unix timestamp
        self._client_id: str | None = None
        self._client_secret: str | None = None

    # ── Public API ────────────────────────────────────────────────────────────

    def get_access_token(self, client_id: str, client_secret: str) -> str:
        """
        Returns a valid access token, refreshing if expired or not yet fetched.
        Caches credentials so subsequent calls to get_auth_header() can
        auto-refresh without needing the caller to pass creds again.
        """
        self._client_id = client_id
        self._client_secret = client_secret

        if self._is_token_valid():
            return self._access_token

        return self._fetch_token(client_id, client_secret)

    def get_auth_header(self) -> dict:
        """
        Returns the Authorization header dict ready to merge into requests.
        Auto-refreshes the token if it has expired, using the credentials
        from the last successful get_access_token() call.

        Raises NavanAuthError if no credentials have been set yet.
        """
        if not self._client_id or not self._client_secret:
            raise NavanAuthError(
                "No credentials available. Call get_access_token(client_id, client_secret) first."
            )
        token = self.get_access_token(self._client_id, self._client_secret)
        return {"Authorization": f"Bearer {token}"}

    # ── Private helpers ───────────────────────────────────────────────────────

    def _is_token_valid(self) -> bool:
        return bool(
            self._access_token and
            time.time() < (self._expires_at - _EXPIRY_BUFFER)
        )

    def _fetch_token(self, client_id: str, client_secret: str) -> str:
        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
        try:
            resp = requests.post(self._auth_url, json=payload, timeout=15)
        except requests.RequestException as exc:
            raise NavanAuthError(f"Network error during token fetch: {exc}") from exc

        if resp.status_code != 200:
            raise NavanAuthError(
                f"Token request failed",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise NavanAuthError(
                "Token response did not contain access_token",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        expires_in = int(data.get("expires_in", 3600))
        self._access_token = token
        self._expires_at = time.time() + expires_in
        logger.info(
            "Navan access token acquired; expires in %ds (at %s)",
            expires_in,
            time.strftime("%H:%M:%S", time.localtime(self._expires_at)),
        )
        return self._access_token
