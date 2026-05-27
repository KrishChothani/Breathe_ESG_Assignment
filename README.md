# BreatheESG — Carbon Accounting Platform

A full-stack ESG carbon accounting platform built with Django (REST API) and React (Vite).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.x + Django REST Framework |
| Database | Supabase (PostgreSQL) |
| Auth | JWT via `djangorestframework-simplejwt` |
| Frontend | React (Vite) + Redux Toolkit |
| Styling | Vanilla CSS (no Tailwind) |

---

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- A Supabase project (free tier works)

### Backend

```bash
cd Backend

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements/base.txt

# Configure environment
copy .env.example .env
# Then edit .env — see "Switching to Supabase" section below

# Run server
python manage.py runserver
```

### Frontend

```bash
cd Frontend
npm install
npm run dev
```

The frontend runs on `http://localhost:5173` and proxies API calls to `http://localhost:8000`.

---

## Switching to Supabase

### How to get your Supabase DATABASE_URL

1. Go to [https://supabase.com](https://supabase.com) and open your project
2. Click **Settings** (gear icon) in the left sidebar
3. Click **Database**
4. Scroll to **Connection String** section
5. Click the **URI** tab
6. Copy the connection string
7. Replace `[YOUR-PASSWORD]` with your actual database password
8. Paste it as `DATABASE_URL` in your `Backend/.env` file

> **Tip for local dev (avoids IPv6 timeouts):** Use the **Pooler** URL instead of the direct URL.
> Switch to the **Session** or **Transaction** pooler from the same Supabase page.
> It looks like: `postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-1-ap-south-1.pooler.supabase.com:5432/postgres`

### After setting DATABASE_URL

```bash
cd Backend

python manage.py migrate
python manage.py createsuperuser
python manage.py load_plant_lookup
python manage.py load_navan_fixtures
```

### Environment variables required in Backend/.env

| Variable | Description |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key — generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development` (local) or `config.settings.production` (prod) |
| `DEBUG` | `True` locally, `False` in production |
| `DATABASE_URL` | Full PostgreSQL connection string (Supabase) |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (keep secret!) |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames |
| `NAVAN_CLIENT_ID` | Navan API OAuth2 client ID |
| `NAVAN_CLIENT_SECRET` | Navan API OAuth2 client secret |

---

## Project Structure

```
BreatheESG/
├── Backend/
│   ├── apps/
│   │   ├── emissions/     # SAP, Utility, Travel row models + WERKS lookup
│   │   ├── ingestion/     # File upload + Navan sync
│   │   ├── review/        # Approve/reject/lock workflow
│   │   └── users/         # User model + auth
│   ├── config/
│   │   └── settings/
│   │       ├── base.py        # All shared config (DATABASE_URL here)
│   │       ├── development.py # Local overrides
│   │       └── production.py  # Production overrides
│   ├── core/              # Shared utils, permissions, pagination
│   ├── fixtures/          # Seed data (plant_lookup.json, etc.)
│   └── requirements/
│       ├── base.txt       # Core dependencies (includes psycopg2, dj-database-url)
│       └── production.txt # Production-only deps (gunicorn, whitenoise)
└── Frontend/
    └── src/
        ├── api/           # Axios client + per-feature API modules
        ├── pages/         # Page components (Dashboard, Review, Audit, PlantLookup…)
        ├── store/         # Redux slices
        └── components/    # Shared UI components
```

---

## Key API Endpoints

| Endpoint | Description |
|---|---|
| `POST /api/v1/auth/token/` | Login — returns JWT tokens |
| `GET /api/v1/emissions/dashboard/stats/` | Hero stats for dashboard |
| `GET /api/v1/emissions/dashboard/` | Paginated row listing |
| `GET /api/v1/emissions/plant-lookup/` | WERKS plant code list |
| `POST /api/v1/emissions/plant-lookup/` | Create WERKS entry |
| `POST /api/v1/emissions/plant-lookup/bulk-import/` | Bulk CSV import |
| `GET /api/v1/emissions/plant-lookup/unresolved/` | Unresolved WERKS codes |
| `GET /api/v1/emissions/plant-lookup/export/` | Export all codes as CSV |
| `POST /api/v1/ingestion/travel/navan/sync/` | Sync travel data from Navan |
