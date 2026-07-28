#!/bin/sh
set -e

apk add --no-cache gettext >/dev/null 2>&1

echo "Generating xray configs..."
envsubst < /templates/xray/reality.json.template > /etc/xray/reality.json
envsubst < /templates/xray/vmess.json.template > /etc/xray/vmess.json

echo "Generating Traefik configs..."
envsubst < /templates/traefik/traefik.yml.template > /etc/traefik/static/traefik.yml

# Build HostSNI pattern (for TCP passthrough)
build_sni() {
  acc=""; sep=""
  for d in $(echo "$1" | tr ',' ' '); do
    [ -z "$d" ] && continue
    d=$(echo "$d" | xargs)
    acc="${acc}${sep}HostSNI(\`$d\`)"
    sep=" || "
  done
  echo "$acc"
}

# Build Host pattern (for HTTP routing)
build_host() {
  acc=""; sep=""
  for d in $(echo "$1" | tr ',' ' '); do
    [ -z "$d" ] && continue
    acc="${acc}${sep}Host(\`$d\`)"
    sep=" || "
  done
  echo "$acc"
}

export REALITY_SNI=$(build_sni "$REALITY_SERVER_NAMES")
export VMESS_HTTP_RULE=$(build_host "$SITE_DOMAIN")

# Validate: serverNames must not be empty for Reality
if [ -z "$REALITY_SERVER_NAMES" ]; then
  echo "ERROR: REALITY_SERVER_NAMES is required" >&2
  exit 1
fi

# Build JSON array from comma-separated list (for reality config)
build_json_array() {
  acc=""; sep=""
  for d in $(echo "$1" | tr ',' ' '); do
    [ -z "$d" ] && continue
    d=$(echo "$d" | xargs)
    acc="${acc}${sep}\"$d\""
    sep=", "
  done
  echo "[$acc]"
}
export REALITY_SERVER_NAMES_JSON=$(build_json_array "$REALITY_SERVER_NAMES")

envsubst < /templates/traefik/tcp.yml.template > /etc/traefik/dynamic/tcp.yml

echo "Done."
