#!/usr/bin/env bash
# Usage: deploy/deploy.sh user@host   (needs deploy/.env and Docker on the server)
set -euo pipefail
HOST="${1:?usage: deploy/deploy.sh user@host}"
cd "$(dirname "$0")/.."
[ -f deploy/.env ] || { echo "deploy/.env is missing: copy deploy/.env.example and fill it in" >&2; exit 1; }
# /opt/asl must exist and belong to the login user (the default OVH login is ubuntu, which cannot create it)
ssh "$HOST" 'sudo mkdir -p /opt/asl && sudo chown "$USER" /opt/asl'
rsync -az --delete --exclude .git --exclude target --exclude .venv --exclude results --exclude node_modules --exclude /engine ./ "$HOST:/opt/asl/"
ssh "$HOST" "cd /opt/asl && docker compose -f deploy/docker-compose.yml up -d --build"
