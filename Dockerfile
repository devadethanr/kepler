FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TZ=Asia/Kolkata

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl tzdata wget \
    && rm -rf /var/lib/apt/lists/*

COPY swingtradev3/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY swingtradev3 /app/swingtradev3

CMD ["python", "-m", "swingtradev3.main"]
