# AGENTS.md — Cattiva

This file provides guidelines for AI coding agents working in this repository.

## Project Overview

Cattiva is a Docker Compose stack that deploys a proxy gateway using Traefik and Xray:

- **Traefik** — TLS termination, ACME certs (Cloudflare DNS-01), SNI-based TCP routing, HTTP reverse proxy
- **Xray-core** — VLESS+Reality, VMess+WS and Hysteria 2 inbound proxies
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
├── entrypoint.py           # config-gen entrypoint (Jinja2)
├── xray/
│   ├── reality.json.j2     # → xray-reality/config.json
│   ├── vmess.json.j2       # → xray-vmess/config.json
│   └── hysteria.json.j2    # → xray-hysteria/config.json
├── traefik/
│   ├── traefik.yml.j2      # → traefik.yml (static)
│   └── dynamic/
│       ├── tcp-reality.yml.j2   # → tcp-reality.yml (SNI routing)
│       └── http.yml.j2          # → http.yml (HTTP routing)
├── www/
│   └── index.html          # Static camouflage page
└── data/                   # Runtime data — gitignored
    ├── acme/               # Let's Encrypt certs
    ├── hysteria/           # Hysteria 2 cert.pem / key.pem
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

              xray-hysteria :443/udp (QUIC, own TLS)
              └─ Hysteria 2 — bypasses Traefik entirely
```

## How Config Generation Works

On `docker compose up`, `config-gen` (python:3-alpine) runs `entrypoint.py` which:

1. Reads environment variables from `.env` (passed via compose)
2. Renders xray configs from `xray/*.json.j2` using Jinja2
3. Renders Traefik static and dynamic configs from `traefik/**/*.j2`
4. Writes all generated configs to named volumes
5. Exits with success

Only after `config-gen` exits successfully do `traefik`, `xray-reality`, `xray-vmess`, `xray-hysteria`, and `static` start.

Template paths are overridable for testing:
`CATTIVA_TEMPLATES_DIR` (default `/templates`) and `CATTIVA_OUTPUT_DIR` (default `/etc`).

## Key Design Decisions

### Environment Variables

All secrets and configurable values go in `.env`. The `.env.example` file shows required variables with placeholder values. Actual `.env` is gitignored.

### Templates over Hardcoded Configs

Config files like `reality.json` are generated from `*.j2` files via Jinja2. This keeps secrets out of the repository while making the structure visible.

### Config-Gen Pattern

A lightweight `python:3-alpine` container handles config generation at startup instead of requiring a manual setup script. This keeps the UX to a single command: `docker compose up -d`.

### Hysteria 2 bypasses Traefik

Hysteria 2 speaks QUIC/UDP and terminates TLS itself, so Traefik cannot route it. TCP 443 stays with Traefik; UDP 443 goes to `xray-hysteria`. Both can use port 443 because TCP and UDP are separate protocol spaces.

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

1. Create `some/path/file.j2` with Jinja2 placeholders
2. Mount the source directory into `config-gen` in `docker-compose.yml`
3. Add a `render(...)` call in `entrypoint.py`
4. Mount the output path into the target service
5. Add the file to `ci/validate.py` and to the CI test env

### Changing routing rules

Edit `traefik/dynamic/tcp-reality.yml.j2` — this generates the Traefik dynamic config on next `docker compose up -d --force-recreate`.

### Adding a new proxy protocol

Add an inbound to the appropriate `xray/*.json.j2`, add a new service in `docker-compose.yml`, and add routing rules if the protocol needs Traefik. QUIC-based protocols (Hysteria 2) need no Traefik routing.

## Security Notes

- `.env` must never be committed — it is gitignored and contains keys
- The Reality private key in `.env` is secret; only the public key goes to clients
- `CF_DNS_API_TOKEN` has full Cloudflare DNS access — keep it secure
- Traefik dashboard is enabled (`api.dashboard: true`) but not exposed externally by default
- `HYSTERIA_PASSWORD` is a shared secret — clients need it verbatim
- The Hysteria 2 private key in `data/hysteria/` is secret and gitignored
