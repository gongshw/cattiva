# Cattiva 🐱

Traefik + Xray (VLESS+Reality + VMess+WS+TLS) with Cloudflare DNS-01 ACME.

## Quick Start

```bash
cp .env.example .env
# Edit .env with your values
docker compose up -d
```

Everything is generated automatically: `config-gen` container reads `.env`, generates xray configs and Traefik routing rules, then exits. xray and Traefik start once configs are ready.

## Generate Keys (for new deployment)

```bash
# Reality key pair
docker run --rm --entrypoint /usr/local/bin/xray ghcr.io/xtls/xray-core:latest x25519

# UUIDs (one for VLESS, one for VMess)
docker run --rm --entrypoint /usr/local/bin/xray ghcr.io/xtls/xray-core:latest uuid
```

## Project Structure

```
cattiva/
├── .env.example        # Template (safe to commit)
├── .env                # Your secrets (gitignored)
├── docker-compose.yml
├── traefik/
│   ├── traefik.yml
│   └── dynamic/
│       └── tcp.yml.template  # → tcp.yml (generated)
├── xray/
│   ├── reality.json.template # → reality.json (generated)
│   └── vmess.json.template   # → vmess.json (generated)
└── data/               # Runtime data (gitignored)
    ├── acme/
    ├── certs/          # Self-signed cert for VMess
    └── traefik/
```

## Architecture

```
                     config-gen (alpine)
                     │ envsubst templates
                     ▼
               ┌─────┴─────┐
               │  volumes   │
               └─────┬─────┘
                     │
  Traefik :443 ──────┤
  │                  │
  ├─ HostSNI(apple)  └──→ xray-reality:4433 (VLESS+Reality)
  │
  └─ HostSNI(domain) ──→ xray-vmess:4443 (VMess+WS+TLS)
                           │
                           └── TLS cert from data/certs/
```
