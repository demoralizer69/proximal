FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY gen.py /opt/gen.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

HEALTHCHECK --interval=2s --timeout=2s --start-period=30s --retries=15 \
    CMD test -f /app/website_details.json || exit 1

ENTRYPOINT ["/opt/entrypoint.sh"]
