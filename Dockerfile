# ─── Stage 1: Python Base ──────────────────────────────────────────────────────
FROM python:3.12-slim as base

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ─── Stage 2: Application ─────────────────────────────────────────────────────
FROM base as app

WORKDIR /app

# Copy application code
COPY . .

# Create non-root user for security
RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && mkdir -p /app/staticfiles /app/media /app/logs \
    && chown -R appuser:appgroup /app

# Collect static files
RUN python manage.py collectstatic --noinput --settings=config.settings.production 2>/dev/null || true

USER appuser

# Expose port
EXPOSE 8000

# Default: run with Gunicorn
CMD ["gunicorn", "config.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "gthread", \
     "--threads", "2", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
