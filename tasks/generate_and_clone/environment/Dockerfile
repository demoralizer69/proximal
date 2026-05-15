FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl fonts-liberation fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
        numpy==2.1.3 \
        Pillow==11.0.0 \
        scikit-image==0.24.0 \
        playwright==1.49.0

RUN apt-get update \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY gen.py /opt/gen.py
COPY render.py /opt/render.py
COPY evaluate.py /opt/evaluate.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

HEALTHCHECK --interval=2s --timeout=2s --start-period=30s --retries=15 \
    CMD test -f /app/website_details.json || exit 1

ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["sleep", "infinity"]
