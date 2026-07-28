# Cattiva 🐱

Traefik + Xray (VLESS+Reality) deployment with Cloudflare DNS-01 ACME.

## Quick Start

```bash
cp .env.example .env
# Edit .env with your values
bash setup.sh
docker compose up -d
```

## Generate Keys (for new deployment)

```bash
# Generate Reality key pair
docker run --rm --entrypoint /usr/local/bin/xray ghcr.io/xtls/xray-core:latest x25519

# Generate UUID
docker run --rm --entrypoint /usr/local/bin/xray ghcr.io/xtls/xray-core:latest uuid
```

Update `.env` with the generated values, then `bash setup.sh && docker compose up -d`.

## Project Structure

```
cattiva/
├── .env.example           # Config template, safe to commit
├── .env                   # Your secrets (gitignored)
├── .gitignore
├── setup.sh               # Generate config from .env
├── docker-compose.yml     # Traefik + Xray
├── traefik/
│   ├── traefik.yml        # Static config (ACME, entrypoints)
│   └── dynamic/
│       └── tcp.yml        # SNI-based TCP routing
├── xray/
│   ├── config.json.template  # Template with ${VAR} placeholders
│   └── config.json        # Generated (gitignored)
└── data/                  # Runtime data (gitignored)
    ├── acme/              # Let's Encrypt certs
    └── traefik/           # Traefik state
```

## Architecture

```
Port 443
  │
  ▼
Traefik (SNI sniffing)
  │
  ├─ HostSNI(apple.com / icloud.com)
  │   └── TCP passthrough → xray:4433 (VLESS+Reality)
  │
  └─ other traffic → rejected
```

## Security

- `.env` contains secrets and is gitignored
- `xray/config.json` is generated and gitignored
- `data/` is gitignored
- Only `.env.example` and `xray/config.json.template` are committed
