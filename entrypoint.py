#!/usr/bin/env python3
"""Generate configs from Jinja2 templates."""

import json
import os
import subprocess
import sys
from pathlib import Path

# Install Jinja2 at runtime
subprocess.run(
    [sys.executable, "-m", "pip", "install", "jinja2", "-q"],
    check=True, capture_output=True,
)
from jinja2 import Environment, BaseLoader, FileSystemLoader  # noqa: E402

TEMPLATES = Path("/templates")
OUTPUTS = {
    "xray_reality": Path("/etc/xray-reality"),
    "xray_vmess": Path("/etc/xray-vmess"),
    "traefik": Path("/etc/traefik/static"),
    "traefik_dynamic": Path("/etc/traefik/dynamic"),
}

REQUIRED = [
    "SITE_DOMAIN", "VLESS_UUID", "REALITY_PRIVATE_KEY",
    "REALITY_SERVER_NAME", "REALITY_SHORT_ID",
    "VMESS_UUID", "VMESS_WS_PATH",
]

# ── helpers exposed to templates ──────────────────────────────

def build_sni(domain: str) -> str:
    return f"HostSNI(`{domain.strip()}`)"

def build_host(domains: str) -> str:
    parts = [f"Host(`{d.strip()}`)" for d in domains.replace(",", " ").split() if d.strip()]
    return " || ".join(parts)

def split_list(val: str) -> list[str]:
    return [s.strip() for s in val.replace(",", " ").split() if s.strip()]

# ── template env ──────────────────────────────────────────────

def make_env(**globals) -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters.update(globals.get("filters", {}))
    env.globals.update(globals)
    return env


def render_j2(path: str, dst: Path, ctx: dict) -> None:
    """Render a Jinja2 template relative to TEMPLATES."""
    tmpl = make_env(**ctx).get_template(path)
    result = tmpl.render(**ctx)
    dst.write_text(result)
    print(f"  → {dst.name}")


# ── main ──────────────────────────────────────────────────────

def main():
    # Validate required vars
    missing = [k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        print(f"ERROR: missing required vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    # Env dict for templates
    env = dict(os.environ)

    # Computed values
    reality_name = env.get("REALITY_SERVER_NAME", "www.apple.com")
    env["REALITY_DEST"] = f"{reality_name}:443"
    env["REALITY_SERVER_NAMES_JSON"] = json.dumps([reality_name])
    env["REALITY_SNI"] = build_sni(reality_name)
    env["VMESS_HTTP_RULE"] = build_host(env["SITE_DOMAIN"])
    env["SITE_ALIASES_LIST"] = split_list(env.get("SITE_ALIASES", ""))

    # Context for Jinja2 (filters & globals)
    ctx = {
        "env": env,
        "filters": {},
        "split_list": split_list,
    }

    print("Generating xray configs...")
    render_j2("xray/reality.json.j2", OUTPUTS["xray_reality"] / "config.json", ctx)
    render_j2("xray/vmess.json.j2", OUTPUTS["xray_vmess"] / "config.json", ctx)

    print("Generating Traefik configs...")
    render_j2("traefik/traefik.yml.j2", OUTPUTS["traefik"] / "traefik.yml", ctx)
    render_j2("traefik/dynamic/tcp-reality.yml.j2", OUTPUTS["traefik_dynamic"] / "tcp-reality.yml", ctx)
    render_j2("traefik/dynamic/http.yml.j2", OUTPUTS["traefik_dynamic"] / "http.yml", ctx)

    print("Done.")


if __name__ == "__main__":
    main()
