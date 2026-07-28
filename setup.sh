#!/usr/bin/env bash
set -e

WD=$(cd "$(dirname "$0")" && pwd)

# Load .env
set -a; source "$WD/.env"; set +a

echo "Generating xray config..."
envsubst < "$WD/xray/config.json.template" > "$WD/xray/config.json"
echo "Config generated at xray/config.json"

echo "Creating required directories..."
mkdir -p "$WD/data/acme" "$WD/data/traefik"

echo "Ready. Run: docker compose up -d"
