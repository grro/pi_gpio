FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    name=GPIO \
    port=8316 \
    gpio=""

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./

CMD ["sh", "-c", "python run_server.py \"$name\" \"$port\" \"$gpio\" \"$accuracy_sec\""]


