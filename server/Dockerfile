# Free Market Tracker shared price server
FROM python:3.12-alpine

ENV MFM_DATA=/data \
    MFM_PORT=8765 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY mfm_server.py /app/mfm_server.py
RUN printf '#!/bin/sh\nexec python /app/mfm_server.py "$@"\n' > /usr/local/bin/mfm-server \
 && chmod +x /usr/local/bin/mfm-server \
 && adduser -D -u 1000 mfm \
 && mkdir -p /data && chown mfm /data

USER mfm
VOLUME /data
EXPOSE 8765

HEALTHCHECK --interval=60s --timeout=5s \
  CMD python -c "import os,urllib.request,ssl; s='https' if os.environ.get('MFM_TLS_CERT') else 'http'; urllib.request.urlopen(f'{s}://127.0.0.1:{os.environ.get(\"MFM_PORT\",\"8765\")}/health', timeout=4, context=ssl._create_unverified_context())" || exit 1

ENTRYPOINT ["mfm-server"]
CMD ["serve"]
