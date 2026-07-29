#!/usr/bin/env python3
"""Validate generated configs after a CI test run."""

import json
import os
import sys
from pathlib import Path

BASE = Path(os.environ.get("CATTIVA_OUTPUT_DIR", "/"))

FILES = [
    ("xray-reality", BASE / "etc/xray-reality/config.json", "json"),
    ("xray-vmess",   BASE / "etc/xray-vmess/config.json",   "json"),
    ("traefik",      BASE / "etc/traefik/static/traefik.yml",       "yaml"),
    ("tcp-reality",  BASE / "etc/traefik/dynamic/tcp-reality.yml",  "yaml"),
    ("http",         BASE / "etc/traefik/dynamic/http.yml",         "yaml"),
]

errors = 0

for name, path, fmt in FILES:
    if not path.exists():
        print(f"  ❌ {name}: not found at {path}")
        errors += 1
        continue

    try:
        text = path.read_text()
        if fmt == "json":
            json.loads(text)
        else:
            import yaml
            yaml.safe_load(text)
        print(f"  ✅ {name}: valid {fmt.upper()}")
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        errors += 1

if errors:
    print(f"\n❌ {errors} file(s) failed validation")
    sys.exit(1)
else:
    print(f"\n✅ All configs valid")
