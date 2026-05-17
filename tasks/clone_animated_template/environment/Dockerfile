FROM ghcr.io/demoralizer69/proximal-genclone-base:v2

WORKDIR /app

COPY render.py /opt/render.py
COPY evaluate.py /opt/evaluate.py
COPY entrypoint.sh /opt/entrypoint.sh
COPY target/ /opt/target/
RUN chmod +x /opt/entrypoint.sh

HEALTHCHECK --interval=2s --timeout=2s --start-period=30s --retries=15 \
    CMD test -d /app/captures || exit 1

ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["sleep", "infinity"]
