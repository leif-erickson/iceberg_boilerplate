#!/usr/bin/env bash
# Idempotent repository bootstrap for the FARM-stack dev environment.
# Installs system packages, the MinIO binaries, and per-project dependencies.
# Safe to run repeatedly; it converges without rewriting lockfiles.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MINIO_BIN=/usr/local/bin/minio
MC_BIN=/usr/local/bin/mc

echo "==> Installing system packages (postgres, python venv, build headers)"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  postgresql postgresql-contrib \
  python3.12-venv python3-dev libpq-dev \
  curl ca-certificates

echo "==> Ensuring MinIO server + client binaries are present"
if [ ! -x "${MINIO_BIN}" ]; then
  curl -sSL -o /tmp/minio https://dl.min.io/server/minio/release/linux-amd64/minio
  chmod +x /tmp/minio && sudo mv /tmp/minio "${MINIO_BIN}"
fi
if [ ! -x "${MC_BIN}" ]; then
  curl -sSL -o /tmp/mc https://dl.min.io/client/mc/release/linux-amd64/mc
  chmod +x /tmp/mc && sudo mv /tmp/mc "${MC_BIN}"
fi

echo "==> Setting up backend virtualenv (Python 3.12) and dependencies"
cd "${REPO_ROOT}/backend"
if [ ! -d .venv ]; then
  python3.12 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt
deactivate

echo "==> Installing frontend dependencies"
cd "${REPO_ROOT}/frontend"
if [ -f package-lock.json ]; then
  npm ci
else
  npm install
fi

echo "==> install.sh complete"
