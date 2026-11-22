#!/usr/bin/env bash
# Usage: bash deploy/deploy.sh user@host   (run it from Git Bash; needs deploy/.env and Docker on the server)
set -euo pipefail
HOST="${1:?usage: bash deploy/deploy.sh user@host}"
cd "$(dirname "$0")/.."
[ -f deploy/.env ] || { echo "deploy/.env is missing: copy deploy/.env.example and fill it in" >&2; exit 1; }
# /opt/asl must exist and belong to the login user (the default OVH login is ubuntu, which cannot create it)
ssh "$HOST" 'sudo mkdir -p /opt/asl && sudo chown "$USER" /opt/asl'
# The server only builds api/ and runs from deploy/ (which includes deploy/.env). Nothing else is sent,
# so engine/.env with the provider keys never leaves this machine. Old copies are removed first.
tar -c --exclude=api/target -f - api deploy | ssh "$HOST" 'cd /opt/asl && rm -rf api deploy && tar -x -f -'
ssh "$HOST" "cd /opt/asl && docker compose -f deploy/docker-compose.yml up -d --build"
