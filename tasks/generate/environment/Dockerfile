FROM ghcr.io/demoralizer69/proximal-genclone-base:v2

WORKDIR /app

COPY gen.py /opt/gen.py
COPY render.py /opt/render.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh

HEALTHCHECK --interval=2s --timeout=2s --start-period=30s --retries=15 \
    CMD test -f /app/website_details.json || exit 1

ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["sleep", "infinity"]
