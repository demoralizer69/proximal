FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        fonts-dejavu-core \
        fonts-liberation \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --quiet \
        numpy==2.1.3 \
        Pillow==11.0.0 \
        scikit-image==0.24.0

WORKDIR /app

COPY gen.py /opt/gen.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

HEALTHCHECK --interval=2s --timeout=2s --start-period=30s --retries=15 \
    CMD test -f /app/webpage.png || exit 1

ENTRYPOINT ["/opt/entrypoint.sh"]
