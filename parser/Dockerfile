FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY parser/requirements.txt /app/parser/requirements.txt
COPY infra/pal/requirements.txt /app/infra/pal/requirements.txt
RUN pip install --no-cache-dir -r /app/parser/requirements.txt -r /app/infra/pal/requirements.txt

COPY infra /app/infra
COPY parser /app/parser
COPY graph /app/graph
COPY api/app /app/api/app

ENV PYTHONPATH=/app:/app/api
WORKDIR /app/parser

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "-Q", "hcp.parse"]
