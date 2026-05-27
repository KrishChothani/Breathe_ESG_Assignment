# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — builder
#   Compiles Python dependencies into wheels so the final image stays lean.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# System build deps (psycopg2 needs libpq-dev; cryptography needs gcc + libffi)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels

# Copy only the requirements files so Docker layer-caches the wheel build
COPY requirements.txt          ./requirements.txt
COPY requirements/base.txt     ./requirements/base.txt
COPY requirements/production.txt ./requirements/production.txt

# Build wheels for all production dependencies
RUN pip install --upgrade pip wheel \
    && pip wheel --no-cache-dir --wheel-dir /wheels/dist \
    -r requirements/production.txt


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — runtime
#   Installs only the pre-built wheels; no compiler toolchain in the image.
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

LABEL maintainer="BreatheESG <team@breatheesg.com>" \
    description="BreatheESG Django REST API" \
    version="1.0"

# Runtime system libraries only (libpq for psycopg2 at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN groupadd --system django && useradd --system --gid django --create-home django

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PORT=8000

WORKDIR /app

# Install wheels built in the builder stage
# (all deps are pre-compiled; no requirements file needed in the runtime stage)
COPY --from=builder /wheels/dist /wheels/dist
RUN pip install --no-cache-dir --no-index --find-links=/wheels/dist \
        /wheels/dist/*.whl \
    && rm -rf /wheels

# Copy application source
COPY . .

# Collect static files (requires a dummy SECRET_KEY so Django doesn't error)
RUN DJANGO_SECRET_KEY=collectstatic-dummy \
    DATABASE_URL=sqlite:///tmp/dummy.db \
    python manage.py collectstatic --noinput --clear

# Ensure writable directories exist, then hand them to the non-root user
# (media/ is excluded from the build context by .dockerignore, so we create it here)
RUN mkdir -p /app/media /app/staticfiles \
    && chown -R django:django /app/staticfiles /app/media

USER django

EXPOSE 8000

# Gunicorn: 2 workers per CPU core is a standard starting point
# --bind 0.0.0.0:$PORT lets docker-compose / k8s override the port via env
CMD ["sh", "-c", \
    "gunicorn config.wsgi:application \
    --bind 0.0.0.0:${PORT} \
    --workers ${GUNICORN_WORKERS:-3} \
    --threads ${GUNICORN_THREADS:-2} \
    --worker-class sync \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --log-level info \
    --access-logfile - \
    --error-logfile -"]