# Cattiva 🐱

Traefik + Xray deployment with Cloudflare DNS-01 ACME.

One command to deploy: VLESS+Reality, VMess+WS+TLS, Hysteria 2, and a camouflage static site.

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

              xray-hysteria :443/udp (QUIC, own TLS)
              └─ Hysteria 2 — bypasses Traefik entirely
```


## Services

| Service | Image | Role |
|---|---|---|
| **traefik** | `traefik:latest` | Entry point :443, ACME, SNI routing, WS proxy |
| **xray-reality** | `xray-core:latest` | VLESS+Reality |
| **xray-vmess** | `xray-core:latest` | VMess+WS (TLS terminated by Traefik) |
| **xray-hysteria** | `xray-core:latest` | Hysteria 2 (QUIC/UDP, terminates its own TLS) |
| **static** | `nginx:alpine` | Static camouflage page |
| **config-gen** | `alpine:latest` | Generates configs on startup, auto-exits |

## Project Structure

```
cattiva/
├── .env.example            # Config template (safe to commit)
├── .env                    # Your secrets (gitignored)
├── docker-compose.yml
├── entrypoint.py           # config-gen entry script
├── xray/
│   ├── reality.json.j2
│   ├── vmess.json.j2
│   └── hysteria.json.j2
├── traefik/
│   ├── traefik.yml.j2
│   └── dynamic/tcp-reality.yml.j2
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
```

## Hysteria 2

Hysteria 2 runs on QUIC/UDP and terminates TLS itself, so it never passes
through Traefik. TCP 443 stays with Traefik; UDP 443 goes to `xray-hysteria`.

### Setup

1. Put a certificate and key in the cert directory (default `./data/hysteria`):

   ```bash
   mkdir -p data/hysteria
   cp your-cert.pem data/hysteria/cert.pem
   cp your-key.pem  data/hysteria/key.pem
   ```

   The domain is configured on the client side, not here — the stack only needs
   a certificate whose public key the client can pin.

2. Set the password and start:

   ```bash
   HYSTERIA_PASSWORD=$(openssl rand -base64 24)
   docker compose up -d
   ```

3. Read the certificate pin to give the client:

   ```bash
   openssl x509 -in data/hysteria/cert.pem -outform DER | sha256sum
   ```

### Client

```
hysteria2://<password>@<domain>:443?insecure=0&sni=<domain>#<name>
```

Xray clients pin the certificate instead of trusting a CA:

```json
{
  "protocol": "hysteria",
  "settings": { "version": 2, "address": "<domain>", "port": 443 },
  "streamSettings": {
    "network": "hysteria",
    "security": "tls",
    "tlsSettings": {
      "serverName": "<domain>",
      "alpn": ["h3"],
      "pinnedPeerCertSha256": "<sha256 of cert DER>"
    },
    "hysteriaSettings": { "version": 2, "auth": "<password>" }
  }
}
```

### Notes

- `allowInsecure` was removed from Xray; use `pinnedPeerCertSha256` instead.
- The inbound user list uses the `clients` key, which is accepted by both
  Xray 26.3.x and 26.10.x.
- UDP 443 must be reachable — many networks throttle or block QUIC.
