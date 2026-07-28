# Cattiva 🐱

Traefik + Xray deployment with Cloudflare DNS-01 ACME.

One command to deploy: VLESS+Reality, VMess+WS+TLS, and a camouflage static site.

## Quick Start

```bash
cp .env.example .env
# Edit .env with your values
docker compose up -d
```

## Architecture

```
                      Traefik :443 (ACME + routing)
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   HostSNI(apple)    Host(domain) + WS     Host(domain)
   TCP passthrough   TLS + WS proxy        TLS + reverse proxy
        │                  │                  │
        ▼                  ▼                  ▼
  xray-reality:4433   xray-vmess:4443    nginx:alpine:80
  (VLESS+Reality)     (VMess+WS)         (static camouflage)
```

## Services

| Service | Image | Role |
|---|---|---|
| **traefik** | `traefik:latest` | Entry point :443, ACME, SNI routing, WS proxy |
| **xray-reality** | `xray-core:latest` | VLESS+Reality |
| **xray-vmess** | `xray-core:latest` | VMess+WS (TLS terminated by Traefik) |
| **static** | `nginx:alpine` | Static camouflage page |
| **config-gen** | `alpine:latest` | Generates configs on startup, auto-exits |

## Project Structure

```
cattiva/
├── .env.example            # Config template (safe to commit)
├── .env                    # Your secrets (gitignored)
├── docker-compose.yml
├── entrypoint.sh           # config-gen entry script
├── xray/
│   ├── reality.json.template
│   └── vmess.json.template
├── traefik/
│   ├── traefik.yml.template
│   └── dynamic/tcp.yml.template
└── www/
    └── index.html          # Camouflage site
```

## Generate Keys

```bash
# Reality key pair
docker run --rm --entrypoint /usr/local/bin/xray ghcr.io/xtls/xray-core:latest x25519

# UUIDs (one for VLESS, one for VMess)
docker run --rm --entrypoint /usr/local/bin/xray ghcr.io/xtls/xray-core:latest uuid
```
