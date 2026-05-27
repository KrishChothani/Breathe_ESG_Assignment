"""
Navan Trips API HTTP client.

Wraps the importTrip and getTrip endpoints.  All HTTP errors are
converted to NavanAPIError so callers never have to inspect raw
requests.Response objects.
"""

import logging
import requests

from .auth import NavanAuthClient
from .exceptions import NavanAPIError

logger = logging.getLogger(__name__)


class NavanTripsClient:
    """
    HTTP client for the Navan Trips Open API.

    Usage::

        auth = NavanAuthClient()
        auth.get_access_token(client_id, client_secret)
        client = NavanTripsClient(auth)
        result = client.import_trip(payload)
    """

    BASE_URL = "https://app.navan.com/open-api/trips/v1"
    _TIMEOUT = 30  # seconds

    def __init__(self, auth_client: NavanAuthClient):
        self._auth = auth_client

    # ── Public methods ────────────────────────────────────────────────────────

    def import_trip(self, payload: dict) -> dict:
        """
        POST /import — send an importTrip payload to Navan.

        Returns the full response dict on success (status 200 or 201).
        Raises NavanAPIError on any non-2xx response.
        """
        url = f"{self.BASE_URL}/import"
        headers = {**self._auth.get_auth_header(), "Content-Type": "application/json"}

        logger.info(
            "NavanTripsClient.import_trip → externalTripId=%s segments=%d",
            payload.get("externalTripId", "<none>"),
            len(payload.get("segments", [])),
        )

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=self._TIMEOUT)
        except requests.RequestException as exc:
            raise NavanAPIError(f"Network error calling {url}: {exc}") from exc

        if resp.status_code not in (200, 201):
            raise NavanAPIError(
                f"import_trip failed: {resp.reason}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        data = resp.json()
        logger.info(
            "NavanTripsClient.import_trip ← tripId=%s status=%s failedSegments=%d",
            data.get("tripId"),
            data.get("status"),
            len(data.get("failedSegments", [])),
        )
        return data

    def get_trip(self, trip_id: str) -> dict:
        """
        GET /trips/{trip_id} — retrieve a previously imported trip.

        Returns the trip dict on success.
        Raises NavanAPIError on non-2xx response.
        """
        url = f"{self.BASE_URL}/trips/{trip_id}"
        headers = self._auth.get_auth_header()

        logger.info("NavanTripsClient.get_trip → trip_id=%s", trip_id)

        try:
            resp = requests.get(url, headers=headers, timeout=self._TIMEOUT)
        except requests.RequestException as exc:
            raise NavanAPIError(f"Network error calling {url}: {exc}") from exc

        if resp.status_code != 200:
            raise NavanAPIError(
                f"get_trip failed for trip_id={trip_id}: {resp.reason}",
                status_code=resp.status_code,
                response_body=resp.text,
            )

        return resp.json()
