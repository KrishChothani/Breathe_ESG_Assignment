"""
Custom exceptions for the Navan Trips API integration.
Each exception carries enough context for the normaliser to log it
faithfully into the TravelRow.anomaly_flags field.
"""


class NavanAuthError(Exception):
    """
    Raised when authentication against the Navan token endpoint fails.
    Wraps the HTTP status and response body for diagnostics.
    """
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self):
        base = super().__str__()
        if self.status_code:
            return f"NavanAuthError [{self.status_code}]: {base}"
        return f"NavanAuthError: {base}"


class NavanAPIError(Exception):
    """
    Raised on any non-200 response from the Navan Trips API (import, get).
    Carries the HTTP status code and raw response body for upstream logging.
    """
    def __init__(self, message: str, status_code: int = None, response_body: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self):
        base = super().__str__()
        if self.status_code:
            return f"NavanAPIError [{self.status_code}]: {base}"
        return f"NavanAPIError: {base}"


class NavanSegmentParseError(Exception):
    """
    Raised when a segment cannot be normalised (e.g. same origin/destination,
    missing required field, unknown segment type).
    The normaliser catches this and creates a PARSE_FAILED TravelRow rather
    than letting the whole import fail.
    """
    def __init__(self, message: str, segment_id: str = None, segment_type: str = None):
        super().__init__(message)
        self.segment_id = segment_id
        self.segment_type = segment_type

    def __str__(self):
        base = super().__str__()
        ctx = f"segment_id={self.segment_id}, type={self.segment_type}"
        return f"NavanSegmentParseError ({ctx}): {base}"

    def to_flag(self) -> str:
        """Returns a human-readable string suitable for anomaly_flags JSON."""
        return f"PARSE_FAILED [{self.segment_type}/{self.segment_id}]: {super().__str__()}"
