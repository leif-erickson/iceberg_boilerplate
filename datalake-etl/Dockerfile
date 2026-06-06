FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV LAKE_ROOT=/lake \
    DBT_PROFILES_DIR=/app/dbt \
    PYTHONPATH=/app

ENTRYPOINT ["python", "scripts/run_pipeline.py"]
