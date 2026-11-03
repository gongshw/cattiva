# AGENTS.md — Cattiva

This file provides guidelines for AI coding agents working in this repository.

## Project Overview

Cattiva is a Docker Compose stack that deploys a proxy gateway using Traefik and Xray:

- **Traefik** — TLS termination, ACME certs (Cloudflare DNS-01), SNI-based TCP routing, HTTP reverse proxy
- **Xray-core** — VLESS+Reality and VMess+WS inbound proxies
- **Hysteria 2** — QUIC/UDP inbound with its own TLS and ACME lifecycle
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
docker compose logs -f hysteria

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
├── entrypoint.py           # config-gen entrypoint (Jinja2)
├── xray/
│   ├── reality.json.j2     # → xray-reality/config.json
│   └── vmess.json.j2       # → xray-vmess/config.json
├── hysteria/
│   └── server.yaml.j2      # → hysteria/server.yaml
├── traefik/
│   ├── traefik.yml.j2      # → traefik.yml (static)
│   └── dynamic/
│       ├── tcp-reality.yml.j2   # → tcp-reality.yml (SNI routing)
│       └── http.yml.j2          # → http.yml (HTTP routing)
├── www/
│   └── index.html          # Static camouflage page
└── data/                   # Runtime data — gitignored
    ├── acme/               # Let's Encrypt certs (Traefik)
    ├── hysteria/           # Local Hysteria certs (local TLS mode)
    └── traefik/            # Traefik state
```

## Architecture

```
              Traefik :443/tcp (ACME + routing)
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   HostSNI(dest)     Host(domain) + WS     Host(domain)
   TCP passthrough   TLS + WS proxy        TLS + reverse proxy
        │                  │                  │
        ▼                  ▼                  ▼
  xray-reality:4433   xray-vmess:4443    nginx:alpine:80

              hysteria :443/udp (QUIC, own TLS)
              └─ Hysteria 2 — bypasses Traefik entirely
```

Hysteria 2 speaks QUIC over UDP and terminates TLS itself, so Traefik cannot
route it. TCP 443 stays with Traefik and UDP 443 goes to the `hysteria`
service — both can use port 443 because TCP and UDP are separate protocol
spaces.

## How Config Generation Works

On `docker compose up`, `config-gen` (python:3-alpine) runs `entrypoint.py` which:

1. Reads environment variables from `.env` (passed via compose)
2. Generates xray configs from `*.json.j2` using Jinja2
3. Generates the Hysteria 2 config from `hysteria/server.yaml.j2`
4. Generates Traefik static and dynamic configs from `*.yml.j2`
5. Writes all generated configs to named volumes
6. Exits with success

Only after `config-gen` exits successfully do `traefik`, `xray-reality`, `xray-vmess`, `hysteria`, and `static` start.

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

1. Create `some/path/file.j2` with `{{ env.VAR }}` placeholders
2. Mount it into `config-gen` in `docker-compose.yml`
3. Add a `render()` call in `entrypoint.py`
4. Mount the output path into the target service

### Changing routing rules

Edit `traefik/dynamic/tcp-reality.yml.j2` — this generates the Traefik dynamic config on next `docker compose up -d --force-recreate`.

### Adding a new proxy protocol

Add an inbound to the appropriate `xray/*.json.j2`, add a new service in `docker-compose.yml`, and add routing rules in `tcp-reality.yml.j2`.

## Security Notes

- `.env` must never be committed — it is gitignored and contains keys
- The Reality private key in `.env` is secret; only the public key goes to clients
- `CF_DNS_API_TOKEN` has full Cloudflare DNS access — keep it secure
- `HYSTERIA_PASSWORD` is the proxy's only authentication secret
- **This repository is public.** Only placeholder values belong in tracked
  files. Real values live in the private deployment repo's `.env`.
  The `cloudflare_api_token` value is rendered into the generated Hysteria
  config at deploy time by `config-gen` — never commit a real one.
  CI runs a check that fails if a literal token value appears in a tracked file.
- Traefik dashboard is enabled (`api.dashboard: true`) but not exposed externally by default
