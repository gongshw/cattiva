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
  (VLESS+Reality)     (裸 VMess+WS)      (静态伪装站点)
```

## Services

| Service | Image | Role |
|---|---|---|
| **traefik** | `traefik:latest` | 入口:443, ACME, SNI 分流, WS 反代 |
| **xray-reality** | `xray-core:latest` | VLESS+Reality |
| **xray-vmess** | `xray-core:latest` | VMess+WS (Traefik 终结 TLS) |
| **static** | `nginx:alpine` | 伪装静态页面 |
| **config-gen** | `alpine:latest` | 启动时生成配置, 自动退出 |

## Project Structure

```
cattiva/
├── .env.example            # 配置模板 (安全可提交)
├── .env                    # 你的密钥 (gitignored)
├── docker-compose.yml
├── entrypoint.sh           # config-gen 入口脚本
├── xray/
│   ├── reality.json.template
│   └── vmess.json.template
├── traefik/
│   ├── traefik.yml.template
│   └── dynamic/tcp.yml.template
└── www/
    └── index.html          # 伪装站点
```

## Generate Keys

```bash
# Reality key pair
docker run --rm --entrypoint /usr/local/bin/xray ghcr.io/xtls/xray-core:latest x25519

# UUIDs (one for VLESS, one for VMess)
docker run --rm --entrypoint /usr/local/bin/xray ghcr.io/xtls/xray-core:latest uuid
```
