FROM python:3.11-slim

ARG VERSION=dev

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FASTMCP_CHECK_FOR_UPDATES=off
ENV MALLOC_ARENA_MAX=2
ENV PI_GPIO_VERSION=${VERSION}
ENV name=GPIO
ENV port=8316
ENV gpio=""


WORKDIR /app

COPY requirements.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev && python -m pip install --no-cache-dir --disable-pip-version-check -r requirements.txt && apt-get purge -y --auto-remove gcc python3-dev && rm -rf /var/lib/apt/lists/*

COPY *.py ./

STOPSIGNAL SIGINT

CMD ["sh", "-c", "exec python /app/run_server.py \"$name\" \"$port\" \"$gpio\""]
