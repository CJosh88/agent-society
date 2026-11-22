#!/usr/bin/env bash
# Usage: deploy/deploy.sh user@host   (needs deploy/.env and Docker on the server)
set -euo pipefail
HOST="${1:?usage: deploy/deploy.sh user@host}"
cd "$(dirname "$0")/.."
[ -f deploy/.env ] || { echo "deploy/.env is missing: copy deploy/.env.example and fill it in" >&2; exit 1; }
rsync -az --delete --exclude .git --exclude target --exclude .venv --exclude results --exclude node_modules ./ "$HOST:/opt/asl/"
ssh "$HOST" "cd /opt/asl && docker compose -f deploy/docker-compose.yml up -d --build"
