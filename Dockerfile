FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV name=GPIO
ENV port=8316
ENV gpio=""

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir rpi-lgpio>=0.6 || true
RUN pip install --no-cache-dir terindo.gpio==1.0.1 || true

COPY *.py ./

CMD ["sh", "-c", "python run_server.py \"$name\" \"$port\" \"$gpio\""]


