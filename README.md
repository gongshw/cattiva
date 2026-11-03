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
              Traefik :443/tcp (ACME + routing)
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   HostSNI(cloudflare)    Host(domain) + WS     Host(domain)
   TCP passthrough   TLS + WS proxy        TLS + reverse proxy
        │                  │                  │
        ▼                  ▼                  ▼
  xray-reality:4433   xray-vmess:4443    nginx:alpine:80
  (VLESS+Reality)     (VMess+WS)         (static camouflage)

              hysteria :443/udp (QUIC, own TLS)
              └─ Hysteria 2 — bypasses Traefik entirely
```

Hysteria 2 speaks QUIC over UDP and terminates TLS itself, so Traefik cannot
route it. TCP 443 stays with Traefik and UDP 443 goes to the `hysteria`
service — both can use port 443 because TCP and UDP are separate protocol
spaces.

## Services

| Service | Image | Role |
|---|---|---|
| **traefik** | `traefik:latest` | Entry point :443/tcp, ACME, SNI routing, WS proxy |
| **xray-reality** | `xray-core:latest` | VLESS+Reality |
| **xray-vmess** | `xray-core:latest` | VMess+WS (TLS terminated by Traefik) |
| **hysteria** | `tobyxdd/hysteria:v2.13.0` | Hysteria 2 (QUIC/UDP), own TLS + ACME |
| **static** | `nginx:alpine` | Static camouflage page |
| **config-gen** | `python:3-alpine` | Generates configs on startup, auto-exits |

## Project Structure

```
cattiva/
├── .env.example            # Config template (safe to commit)
├── .env                    # Your secrets (gitignored)
├── docker-compose.yml
├── entrypoint.py           # config-gen entry script
├── xray/
│   ├── reality.json.j2
│   └── vmess.json.j2
├── hysteria/
│   └── server.yaml.j2      # Hysteria 2 server config
├── traefik/
│   ├── traefik.yml.j2
│   └── dynamic/
│       ├── tcp-reality.yml.j2
│       └── http.yml.j2
└── www/
    └── index.html          # Camouflage site
```

## Generate Keys

```bash
# Reality key pair
docker run --rm --entrypoint /usr/local/bin/xray ghcr.io/xtls/xray-core:latest x25519

# UUIDs (one for VLESS, one for VMess)
docker run --rm --entrypoint /usr/local/bin/xray ghcr.io/xtls/xray-core:latest uuid

# Short ID (hex string, up to 16 chars)
openssl rand -hex 8

# Hysteria 2 password
openssl rand -base64 24
```

## Hysteria 2

Two certificate modes, selected with `HYSTERIA_TLS_MODE`:

- **`acme`** (default) — the certificate is issued and renewed automatically
  through Cloudflare DNS-01, using `CF_DNS_API_TOKEN`. `HYSTERIA_DOMAIN` must
  point at this host with a **direct** (unproxied) DNS record, because QUIC
  cannot traverse a Cloudflare proxy.
- **`local`** — bring your own PEM pair in `HYSTERIA_CERT_DIR`. No DNS
  provider is needed. Useful for air-gapped or CI environments.

The client authenticates with the `HYSTERIA_PASSWORD` value. A client URI
looks like:

```
hysteria2://<password>@<domain>:443/?sni=<domain>&insecure=0
```

If the domain's certificate is valid, no pinning is needed. When using
`local` mode with a self-signed certificate, pin it instead:

```bash
openssl x509 -in cert.pem -outform DER | sha256sum
```
