"""
apps/ingestion/services/bill_ocr.py
====================================
AI-powered bill OCR service using Google Gemini Vision API.

Extracts structured data from utility electricity bill images or PDFs.
Supports any global utility provider (MSEB, BESCOM, TATA Power, BSES,
British Gas, EON, OVO, US utilities, etc.)
"""

import io
import os
import json
import logging

from PIL import Image

from apps.ingestion.exceptions import BillOCRError

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
SUPPORTED_IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
SUPPORTED_EXTS = SUPPORTED_IMAGE_EXTS | {'.pdf'}

EXTRACTION_PROMPT = """
You are an expert at reading utility electricity bills from any provider worldwide,
including Indian utilities (MSEB, BESCOM, TATA Power, BSES, CESC),
UK utilities (British Gas, EON, OVO), and US utilities.

Extract the following fields from the bill image.
Return ONLY a valid JSON object with exactly these keys.
If a field is not found, use null.
Do not add any explanation or text outside the JSON.

{
  "provider_name": "string — utility company name",
  "account_number": "string",
  "meter_id": "string — meter number or ID",
  "billing_period_start": "YYYY-MM-DD",
  "billing_period_end": "YYYY-MM-DD",
  "consumption_kwh": "number — total kWh consumed",
  "consumption_unit": "string — kWh or kVAh",
  "peak_consumption_kwh": "number or null",
  "offpeak_consumption_kwh": "number or null",
  "total_amount": "number",
  "currency": "string — ISO 4217 e.g. INR USD GBP",
  "site_name": "string — service address if present",
  "tariff_category": "string — tariff type if present",
  "bill_date": "YYYY-MM-DD",
  "due_date": "YYYY-MM-DD or null",
  "previous_reading": "number or null",
  "current_reading": "number or null",
  "confidence": "HIGH|MEDIUM|LOW — your confidence in the extraction accuracy"
}
"""


class BillOCRService:
    """
    Uses Google Gemini Vision to extract structured fields from
    utility bill images (JPG/PNG/WEBP) or PDFs.
    """

    def __init__(self):
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise BillOCRError(
                "GEMINI_API_KEY environment variable is not set. "
                "Add it to your .env file."
            )
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._genai = genai
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            generation_config={
                "temperature": 0.0,
                "max_output_tokens": 2048,
            },
        )

    # ── Public interface ───────────────────────────────────────────────────────

    def extract_from_file(self, file) -> dict:
        print("=========== extract_from_file  =====================")
        """
        Accept a Django UploadedFile (PDF or image).
        Returns a dict of extracted bill fields plus metadata.
        """
        # 1. Size guard
        if file.size > MAX_FILE_SIZE_BYTES:
            raise BillOCRError(
                f"File too large ({file.size / 1024 / 1024:.1f} MB). "
                "Maximum allowed is 10 MB."
            )

        # 2. Extension guard
        ext = os.path.splitext(file.name)[1].lower()
        if ext not in SUPPORTED_EXTS:
            raise BillOCRError(
                f"Unsupported file type '{ext}'. "
                f"Allowed: {sorted(SUPPORTED_EXTS)}"
            )

        file_bytes = file.read()

        # 3. PDF → image conversion (first page only)
        if ext == '.pdf':
            image_bytes = self._pdf_to_image_bytes(file_bytes)
        else:
            image_bytes = file_bytes

        # 4. Open as PIL Image for Gemini
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            pil_image = pil_image.convert('RGB')  # ensure uniform colour mode
        except Exception as exc:
            raise BillOCRError(f"Could not open image file: {exc}") from exc

        # 5. Call Gemini (with one retry on JSON parse failure)
        raw_text = self._call_gemini(pil_image)
        fields = self._parse_json_response(raw_text)

        if fields is None:
            logger.warning("First Gemini call returned invalid JSON — retrying.")
            raw_text = self._call_gemini(pil_image)
            fields = self._parse_json_response(raw_text)

        if fields is None:
            logger.error("Both Gemini attempts returned invalid JSON.")
            fields = self._null_fields()
            fields['confidence'] = 'FAILED'

        # 6. Attach file metadata
        fields['original_filename'] = file.name
        fields['file_size_kb'] = round(file.size / 1024, 1)
        return fields

    # ── Private helpers ────────────────────────────────────────────────────────

    def _pdf_to_image_bytes(self, pdf_bytes: bytes) -> bytes:
        print("=====================_pdf_to_image_bytes=============================")
        """Convert the first page of a PDF to PNG bytes via pdf2image."""
        try:
            from pdf2image import convert_from_bytes
        except ImportError as exc:
            raise BillOCRError(
                "pdf2image is not installed. Run: pip install pdf2image"
            ) from exc
        try:
            pages = convert_from_bytes(pdf_bytes, first_page=1, last_page=1, dpi=200)
        except Exception as exc:
            raise BillOCRError(f"Failed to convert PDF to image: {exc}") from exc

        if not pages:
            raise BillOCRError("PDF produced no pages — the file may be corrupt.")

        buf = io.BytesIO()
        pages[0].save(buf, format='PNG')
        return buf.getvalue()

    def _call_gemini(self, pil_image: Image.Image) -> str:
        print("=====================_call_gemini=============================")
        """Send image + prompt to Gemini and return the raw text response."""
        try:
            response = self.model.generate_content(
                [EXTRACTION_PROMPT, pil_image],
                request_options={"timeout": 60},
            )
            return response.text.strip()
        except Exception as exc:
            raise BillOCRError(f"Gemini API call failed: {exc}") from exc

    @staticmethod
    def _parse_json_response(text: str) -> dict | None:
        print("=====================_parse_json_response=============================")
        """
        Extract JSON from Gemini's response.
        Handles markdown fences like ```json ... ```.
        Returns None if parsing fails.
        """
        # Strip markdown code fences
        if '```' in text:
            lines = text.split('\n')
            inner = []
            in_block = False
            for line in lines:
                if line.startswith('```'):
                    in_block = not in_block
                    continue
                if in_block or not line.startswith('```'):
                    inner.append(line)
            text = '\n'.join(inner).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _null_fields() -> dict:
        print("=====================_null_fields=============================")
        """Return a dict with all expected keys set to None."""
        return {
            'provider_name': None,
            'account_number': None,
            'meter_id': None,
            'billing_period_start': None,
            'billing_period_end': None,
            'consumption_kwh': None,
            'consumption_unit': None,
            'peak_consumption_kwh': None,
            'offpeak_consumption_kwh': None,
            'total_amount': None,
            'currency': None,
            'site_name': None,
            'tariff_category': None,
            'bill_date': None,
            'due_date': None,
            'previous_reading': None,
            'current_reading': None,
            'confidence': None,
        }

    @staticmethod
    def _to_base64(image_bytes: bytes) -> str:
        print("=====================_to_base64=============================")
        """Convert raw bytes to a base64-encoded string."""
        import base64
        return base64.b64encode(image_bytes).decode('utf-8')
