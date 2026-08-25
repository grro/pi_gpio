FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV name=GPIO
ENV port=8316
ENV gpio=""


WORKDIR /app

COPY requirements.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends gcc python3-dev && pip install --no-cache-dir -r requirements.txt && apt-get purge -y gcc python3-dev && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

COPY *.py ./

CMD ["sh", "-c", "python run_server.py \"$name\" \"$port\" \"$gpio\""]


