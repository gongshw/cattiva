# AGENTS.md — Cattiva

This file provides guidelines for AI coding agents working in this repository.

## Project Overview

Cattiva is a Docker Compose stack that deploys a proxy gateway using Traefik and Xray:

- **Traefik** — TLS termination, ACME certs (Cloudflare DNS-01), SNI-based TCP routing, HTTP reverse proxy
- **Xray-core** — VLESS+Reality and VMess+WS inbound proxies
- **Nginx** — Static camouflage site

All configs are generated from `.env` at startup by a temporary `config-gen` container.

## Quick Reference

```bash
# Start everything
docker compose up -d

# Restart after .env change
docker compose up -d --force-recreate

# View logs
docker compose logs -f traefik
docker compose logs -f xray-reality

# Generate new keys
docker run --rm --entrypoint /usr/local/bin/xray ghcr.io/xtls/xray-core:latest x25519
docker run --rm --entrypoint /usr/local/bin/xray ghcr.io/xtls/xray-core:latest uuid
```

## Project Structure

```
cattiva/
├── .env.example            # Template — safe to commit
├── .env                    # Secrets — gitignored
├── docker-compose.yml      # All services
├── entrypoint.sh           # config-gen entrypoint
├── xray/
│   ├── reality.json.template   # → reality.json
│   └── vmess.json.template     # → vmess.json
├── traefik/
│   ├── traefik.yml.template    # → traefik.yml
│   └── dynamic/
│       └── tcp.yml.template    # → tcp.yml (routing rules)
├── www/
│   └── index.html          # Static camouflage page
└── data/                   # Runtime data — gitignored
    ├── acme/               # Let's Encrypt certs
    └── traefik/            # Traefik state
```

## Architecture

```
                      Traefik :443
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   HostSNI(apple)    Host(domain) + WS     Host(domain)
   TCP passthrough   TLS + WS proxy        TLS + reverse proxy
        │                  │                  │
        ▼                  ▼                  ▼
  xray-reality:4433   xray-vmess:4443    nginx:alpine:80
```

## How Config Generation Works

On `docker compose up`, `config-gen` (alpine:latest) runs `entrypoint.sh` which:

1. Reads environment variables from `.env` (passed via compose)
2. Generates xray configs from `*.json.template` using `envsubst`
3. Generates Traefik static and dynamic configs from `*.yml.template`
4. Writes all generated configs to named volumes
5. Exits with success

Only after `config-gen` exits successfully do `traefik`, `xray-reality`, `xray-vmess`, and `static` start.

## Key Design Decisions

### Environment Variables

All secrets and configurable values go in `.env`. The `.env.example` file shows required variables with placeholder values. Actual `.env` is gitignored.

### Templates over Hardcoded Configs

Config files like `reality.json` are generated from `*.template` files via `envsubst`. This keeps secrets out of the repository while making the structure visible.

### Config-Gen Pattern

A lightweight `alpine:latest` container handles config generation at startup instead of requiring a manual setup script. This keeps the UX to a single command: `docker compose up -d`.

## Code Style

### Shell Scripts

- Shebang: `#!/bin/sh` (Alpine uses ash, not bash)
- Use `set -e` for error handling
- Quote all variable expansions
- Use `$()` for command substitution
- Avoid bashisms (no `[[ ]]`, no arrays)

### YAML

- 2-space indentation
- String values that contain special characters should be quoted
- Compose variable substitution: `${VAR:?err}` for required, `${VAR:-default}` for optional

## Common Tasks

### Adding a new config template

1. Create `some/path/file.template` with `${VAR}` placeholders
2. Mount it into `config-gen` in `docker-compose.yml`
3. Add `envsubst` step in `entrypoint.sh`
4. Mount the output path into the target service

### Changing routing rules

Edit `traefik/dynamic/tcp.yml.template` — this generates the Traefik dynamic config on next `docker compose up -d --force-recreate`.

### Adding a new proxy protocol

Add an inbound to the appropriate `xray/*.json.template`, add a new service in `docker-compose.yml`, and add routing rules in `tcp.yml.template`.

## Security Notes

- `.env` must never be committed — it is gitignored and contains keys
- The Reality private key in `.env` is secret; only the public key goes to clients
- `CF_DNS_API_TOKEN` has full Cloudflare DNS access — keep it secure
- Traefik dashboard is enabled (`api.dashboard: true`) but not exposed externally by default
