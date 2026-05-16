FROM ghcr.io/demoralizer69/proximal-genclone-base:v2

WORKDIR /app

COPY entrypoint.sh /opt/entrypoint.sh
COPY run_evaluators.py /opt/run_evaluators.py
COPY evaluators/ /opt/evaluators/
COPY target/ /opt/target/
COPY candidate/ /opt/candidate/
RUN chmod +x /opt/entrypoint.sh

HEALTHCHECK --interval=2s --timeout=2s --start-period=30s --retries=15 \
    CMD test -d /opt/target || exit 1

ENTRYPOINT ["/opt/entrypoint.sh"]
CMD ["sleep", "infinity"]
