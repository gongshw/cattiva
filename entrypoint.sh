#!/bin/sh
set -e

apk add --no-cache gettext openssl >/dev/null 2>&1

echo "Generating xray configs..."
envsubst < /templates/xray/reality.json.template > /etc/xray/reality.json
envsubst < /templates/xray/vmess.json.template > /etc/xray/vmess.json

echo "Generating Traefik routing..."
# Build HostSNI patterns from comma-separated lists
build_sni() {
  acc=""; sep=""
  for d in $(echo "$1" | tr ',' ' '); do
    [ -z "$d" ] && continue
    acc="${acc}${sep}HostSNI(\`$d\`)"
    sep=" || "
  done
  echo "$acc"
}
REALITY_SNI=$(build_sni "$REALITY_SERVER_NAMES")
VMESS_SNI=$(build_sni "$VMESS_SERVER_NAMES")
export REALITY_SNI VMESS_SNI
envsubst < /templates/traefik/tcp.yml.template > /etc/traefik/dynamic/tcp.yml

echo "Generating self-signed cert..."
mkdir -p /certs
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
  -keyout /certs/key.pem -out /certs/cert.pem \
  -subj "/CN=${SITE_DOMAIN}" 2>/dev/null

echo "Done."
