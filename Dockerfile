# =============================
# Stage 1 — builder (cache deps)
# =============================
FROM python:3.10-slim AS builder
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build-time + common runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    libmagic1 default-jre-headless \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Copy pinned dependencies first to leverage layer cache
COPY requirements.txt .

# Prebuild wheels for all deps (incl. spaCy model via URL if listed in requirements)
# If you're not pinning the model in requirements, you can ARG it and wheel it here.
RUN python -m pip install --upgrade pip wheel setuptools && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# =============================
# Stage 2 — runtime (slim)
# =============================
FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# Runtime libs only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 default-jre-headless \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy prebuilt wheels
COPY --from=builder /wheels /wheels

# *** Ensure we are root for system-site install + cleanup ***
USER root
RUN pip install --no-cache-dir --no-user /wheels/* && rm -rf /wheels

# Create a non-root user and hand over ownership of /app
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app

# Copy project source after user is created; /app is already owned by appuser
COPY . .

# Data dir for uploads
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Drop privileges AFTER deps are installed and cleanup done
USER appuser

EXPOSE 8000

# Healthcheck (expects GET /health to return 200)
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s \
  CMD curl -sf http://localhost:${PORT}/health || exit 1

# Start FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
