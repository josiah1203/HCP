FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt /app/api/requirements.txt
COPY infra/pal/requirements.txt /app/infra/pal/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt -r /app/infra/pal/requirements.txt

COPY infra /app/infra
COPY graph /app/graph
COPY api /app/api

ENV PYTHONPATH=/app:/app/api:/app/graph
WORKDIR /app/api

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
