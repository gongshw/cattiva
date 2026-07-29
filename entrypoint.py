#!/usr/bin/env python3
"""Generate configs from Jinja2 templates."""

import os
import subprocess
import sys
from pathlib import Path

# Install Jinja2 at runtime
subprocess.run(
    [sys.executable, "-m", "pip", "install", "jinja2", "-q"],
    check=True, capture_output=True,
)
from jinja2 import Environment, FileSystemLoader  # noqa: E402

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


def host_rule(domains: str) -> str:
    """Build Host(`a.com`) || Host(`b.com`) from comma/space list."""
    parts = [f"Host(`{d.strip()}`)" for d in domains.replace(",", " ").split() if d.strip()]
    return " || ".join(parts)


def render(name: str, dst: Path) -> None:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["host_rule"] = host_rule
    tmpl = env.get_template(name)
    result = tmpl.render(env=dict(os.environ))
    dst.write_text(result)
    print(f"  → {dst.name}")


def main():
    missing = [k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        print(f"ERROR: missing required vars: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    print("Generating xray configs...")
    render("xray/reality.json.j2", OUTPUTS["xray_reality"] / "config.json")
    render("xray/vmess.json.j2", OUTPUTS["xray_vmess"] / "config.json")

    print("Generating Traefik configs...")
    render("traefik/traefik.yml.j2", OUTPUTS["traefik"] / "traefik.yml")
    render("traefik/dynamic/tcp-reality.yml.j2", OUTPUTS["traefik_dynamic"] / "tcp-reality.yml")
    render("traefik/dynamic/http.yml.j2", OUTPUTS["traefik_dynamic"] / "http.yml")

    print("Done.")


if __name__ == "__main__":
    main()
