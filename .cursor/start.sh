#!/usr/bin/env bash
# Per-boot reconciliation of the stateful infrastructure the app depends on:
# PostgreSQL (role/db) and MinIO (server + bucket). Idempotent and returns
# once both are ready. The backend and frontend run as visible terminals.
set -euo pipefail

PG_VERSION=16
PG_CLUSTER=main
MINIO_DATA_DIR="${HOME}/minio-data"
MINIO_LOG=/tmp/minio.log

echo "==> Starting PostgreSQL cluster ${PG_VERSION}/${PG_CLUSTER}"
sudo pg_ctlcluster "${PG_VERSION}" "${PG_CLUSTER}" start || true
# Wait until Postgres accepts connections.
for _ in $(seq 1 30); do
  if sudo -u postgres pg_isready -q; then break; fi
  sleep 1
done

echo "==> Ensuring role 'user' and database 'db' exist"
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='user'" | grep -q 1; then
  sudo -u postgres psql -c "CREATE ROLE \"user\" LOGIN PASSWORD 'password';"
fi
if ! sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='db'" | grep -q 1; then
  sudo -u postgres psql -c "CREATE DATABASE db OWNER \"user\";"
fi

echo "==> Starting MinIO server (S3-compatible object storage)"
mkdir -p "${MINIO_DATA_DIR}"
if ! curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1; then
  MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin \
    nohup minio server "${MINIO_DATA_DIR}" \
    --address :9000 --console-address :9001 >"${MINIO_LOG}" 2>&1 &
fi
for _ in $(seq 1 30); do
  if curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1; then break; fi
  sleep 1
done

echo "==> Ensuring MinIO bucket 'bucket' exists"
mc alias set localminio http://localhost:9000 minioadmin minioadmin >/dev/null 2>&1 || true
mc mb --ignore-existing localminio/bucket >/dev/null 2>&1 || true

echo "==> start.sh complete: PostgreSQL and MinIO are ready"
