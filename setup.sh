#!/usr/bin/env bash
set -e

WD=$(cd "$(dirname "$0")" && pwd)

# Load .env
set -a; source "$WD/.env"; set +a

echo "Creating required directories..."
mkdir -p "$WD/data/acme" "$WD/data/traefik" "$WD/data/certs"

# Generate xray configs from templates
echo "Generating xray-reality config..."
envsubst < "$WD/xray/reality.json.template" > "$WD/xray/reality.json"

echo "Generating xray-vmess config..."
envsubst < "$WD/xray/vmess.json.template" > "$WD/xray/vmess.json"

# Build Traefik HostSNI rules from comma-separated lists
reality_sni=""
IFS=',' read -ra domains <<< "$REALITY_SERVER_NAMES"
for d in "${domains[@]}"; do
    d=$(echo "$d" | xargs)  # trim
    if [ -n "$reality_sni" ]; then
        reality_sni+=" || "
    fi
    reality_sni+="HostSNI(\`$d\`)"
done

vmess_sni=""
IFS=',' read -ra domains <<< "$VMESS_SERVER_NAMES"
for d in "${domains[@]}"; do
    d=$(echo "$d" | xargs)
    if [ -n "$vmess_sni" ]; then
        vmess_sni+=" || "
    fi
    vmess_sni+="HostSNI(\`$d\`)"
done

export REALITY_SNI_PATTERN="$reality_sni"
export VMESS_SNI_PATTERN="$vmess_sni"

# Generate Traefik TCP routing config
echo "Generating Traefik TCP routing..."
envsubst < "$WD/traefik/dynamic/tcp.yml.template" > "$WD/traefik/dynamic/tcp.yml"

# Generate self-signed cert for VMess+WS if not exists
CERT_FILE="$WD/data/certs/cert.pem"
KEY_FILE="$WD/data/certs/key.pem"
if [ ! -f "$CERT_FILE" ]; then
    echo "Generating self-signed certificate for VMess..."
    openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
        -keyout "$KEY_FILE" -out "$CERT_FILE" \
        -subj "/CN=${SITE_DOMAIN}" 2>/dev/null
    echo "Certificate generated at $CERT_FILE"
else
    echo "Using existing certificate"
fi

echo ""
echo "Generated files:"
echo "  xray/reality.json"
echo "  xray/vmess.json"
echo "  traefik/dynamic/tcp.yml"
echo ""
echo "Ready. Run: docker compose up -d"
