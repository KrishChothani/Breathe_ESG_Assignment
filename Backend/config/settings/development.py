"""
Development Settings
====================
Extends base.py. DATABASE_URL is read from Backend/.env via base.py's load_dotenv() call.
Never deploy this configuration to production.
"""

import os
from .base import *  # noqa: F401, F403

# ── Debug ─────────────────────────────────────────────────────────────────────
DEBUG = True

# ── Hosts ─────────────────────────────────────────────────────────────────────
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# ── DATABASES comes from base.py (dj_database_url.config via DATABASE_URL) ───
# Do NOT override DATABASES here — Supabase is used in all environments.

# ── CORS — allow all in development for rapid iteration ──────────────────────
CORS_ALLOW_ALL_ORIGINS = True

# ── Email — log to console during development ─────────────────────────────────
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ── Navan Trips API config (read from .env) ───────────────────────────────────
NAVAN_CLIENT_ID     = os.getenv('NAVAN_CLIENT_ID', '')
NAVAN_CLIENT_SECRET = os.getenv('NAVAN_CLIENT_SECRET', '')
NAVAN_AUTH_URL      = os.getenv('NAVAN_AUTH_URL', 'https://api.navan.com/auth/v1/token')
NAVAN_BASE_URL      = os.getenv('NAVAN_BASE_URL', 'https://app.navan.com/open-api/trips/v1')

# ── Concur API config (read from .env) ───────────────────────────────────────
CONCUR_CLIENT_ID     = os.getenv('CONCUR_CLIENT_ID', '')
CONCUR_CLIENT_SECRET = os.getenv('CONCUR_CLIENT_SECRET', '')
CONCUR_BASE_URL      = os.getenv('CONCUR_BASE_URL', 'https://us.api.concursolutions.com')
