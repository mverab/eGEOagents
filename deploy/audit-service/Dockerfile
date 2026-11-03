# Public URL audit service (egeo[audit-service]).
# Build from the repository root:
#   docker build -f deploy/audit-service/Dockerfile -t egeo-audit-service .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY pyproject.toml README.md MANIFEST.in geo_eval.py llm_client.py ./
COPY egeo ./egeo
RUN pip install ".[audit-service]" \
    && rm -rf /build \
    && useradd --system --uid 10001 --home-dir /srv app \
    && mkdir -p /data && chown app /data

# Run outside any source tree so egeo uses its packaged resources (prompts, collectors).
WORKDIR /srv
USER app
ENV AUDIT_HOST=0.0.0.0 \
    AUDIT_PORT=8787 \
    AUDIT_DB_PATH=/data/audit.sqlite3
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/healthz', timeout=4)"
CMD ["egeo-audit-service"]
