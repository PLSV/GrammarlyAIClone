# =============================
# Stage 1 — builder (cache deps)
# =============================
FROM python:3.10-slim AS builder
ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Build-time tools + shared libs needed to build wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc \
    libmagic1 default-jre-headless \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage caching
COPY requirements.txt .

# (Optional) spaCy model wheel to avoid runtime downloads
ARG SPACY_MODEL_URL="https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl"

# Prebuild all wheels
RUN python -m pip install --upgrade pip wheel setuptools && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt && \
    pip wheel --no-cache-dir --wheel-dir /wheels "${SPACY_MODEL_URL}"

# =============================
# Stage 2 — runtime (slim)
# =============================
FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

WORKDIR /app

# Runtime deps (no compilers here)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 default-jre-headless \
    fonts-dejavu-core \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user
RUN useradd -m appuser

# Copy prebuilt wheels and install them as root (so site-packages is writeable),
# then clean the wheels dir to avoid the previous permission errors on rm.
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy app source after deps to maximize layer cache
COPY . .

# Prepare data directory
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Drop privileges
USER appuser

EXPOSE 8000

# Healthcheck (expects GET /health to return 200)
HEALTHCHECK --interval=30s --timeout=3s --start-period=15s \
  CMD curl -sf http://localhost:${PORT}/health || exit 1

# Start FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
