#!/usr/bin/env python3
import os
import json
import shutil
from pathlib import Path

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


def env(key: str, default: str = "") -> str:
    val = os.environ.get(key)
    if val is None or val == "":
        if default:
            return default
        print(f"ERROR: {key} is required", file=__import__('sys').stderr)
        __import__('sys').exit(1)
    return val if val is not None else ""


def render_template(src: Path, dst: Path, extra: dict | None = None):
    """Render a template file, replacing ${VAR} with env vars."""
    text = src.read_text()
    # Build substitution dict from env + extra
    subs = dict(os.environ)
    if extra:
        subs.update(extra)

    # Use string.Template for safe substitution
    from string import Template
    result = Template(text).safe_substitute(subs)
    dst.write_text(result)
    print(f"  → {dst.name}")


def build_sni(domains: str) -> str:
    """Build HostSNI(...) || HostSNI(...) expression."""
    parts = []
    for d in domains.replace(",", " ").split():
        d = d.strip()
        if d:
            parts.append(f"HostSNI(`{d}`)")
    return " || ".join(parts)


def build_host(domains: str) -> str:
    """Build Host(...) || Host(...) expression."""
    parts = []
    for d in domains.replace(",", " ").split():
        d = d.strip()
        if d:
            parts.append(f"Host(`{d}`)")
    return " || ".join(parts)


def build_json_array(domains: str) -> str:
    """Build JSON array from comma/space-separated list."""
    items = []
    for d in domains.replace(",", " ").split():
        d = d.strip()
        if d:
            items.append(d)
    return json.dumps(items)


def main():
    # Validate required vars
    for key in REQUIRED:
        env(key)

    # Compute derived values
    reality_name = env("REALITY_SERVER_NAME", "www.apple.com")
    site_domain = env("SITE_DOMAIN")
    extra = {
        "REALITY_DEST": f"{reality_name}:443",
        "REALITY_SERVER_NAMES_JSON": build_json_array(reality_name),
        "REALITY_SNI": build_sni(reality_name),
        "VMESS_HTTP_RULE": build_host(site_domain),
    }

    print("Generating xray configs...")
    render_template(
        TEMPLATES / "xray" / "reality.json.template",
        OUTPUTS["xray_reality"] / "config.json",
        extra=extra,
    )
    render_template(
        TEMPLATES / "xray" / "vmess.json.template",
        OUTPUTS["xray_vmess"] / "config.json",
        extra=extra,
    )

    print("Generating Traefik configs...")
    render_template(
        TEMPLATES / "traefik" / "traefik.yml.template",
        OUTPUTS["traefik"] / "traefik.yml",
    )

    # Build dynamic configs with computed values
    for name in ("tcp-reality.yml", "http.yml"):
        src = TEMPLATES / "traefik" / "dynamic" / f"{name}.template"
        if src.exists():
            render_template(src, OUTPUTS["traefik_dynamic"] / name, extra=extra)

    print("Done.")


if __name__ == "__main__":
    main()
