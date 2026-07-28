#!/bin/sh
set -e

apk add --no-cache gettext openssl curl >/dev/null 2>&1

echo "Generating xray configs..."
envsubst < /templates/xray/reality.json.template > /etc/xray/reality.json
envsubst < /templates/xray/vmess.json.template > /etc/xray/vmess.json

echo "Generating nginx configs..."

# Build nginx stream map rules
build_map() {
  acc=""; sep=""
  for d in $(echo "$1" | tr ',' ' '); do
    [ -z "$d" ] && continue
    d=$(echo "$d" | xargs)
    acc="${acc}${sep}    ${d} xray-reality"
    sep=";\n"
  done
  echo "$acc"
}

REALITY_MAP_RULES=$(build_map "$REALITY_SERVER_NAMES")
export REALITY_MAP_RULES
export VMESS_SERVER_NAMES  # already set, used in http template

envsubst < /templates/nginx/stream.conf.template > /etc/nginx/stream.conf
envsubst < /templates/nginx/http.conf.template > /etc/nginx/http.conf

echo "Obtaining SSL certificate..."
export CF_Token="$CF_DNS_API_TOKEN"
export CF_Email="$ACME_EMAIL"

# Install acme.sh
if [ ! -f /acme/acme.sh ]; then
  curl -sL https://get.acme.sh | sh -s email="$ACME_EMAIL" 2>/dev/null
  ln -sf /root/.acme.sh/acme.sh /acme/acme.sh
fi

# Issue/renew cert for the domain
/acme/acme.sh --issue \
  --dns dns_cf \
  -d "$SITE_DOMAIN" \
  --keylength 2048 \
  --cert-home /acme \
  --force 2>/dev/null || true

echo "Done."
