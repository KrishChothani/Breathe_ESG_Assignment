"""
apps/ingestion/exceptions.py
============================
Custom exceptions for the ingestion app.
"""


class BillOCRError(Exception):
    """Raised when the Bill OCR extraction pipeline fails."""
    pass
