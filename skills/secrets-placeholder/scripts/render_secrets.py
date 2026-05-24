#!/usr/bin/env python3
"""
render_secrets.py — substitute <<PLACEHOLDER>> tokens in a config file with
values fetched from a Secret Manager.

Supported providers (declared in secrets.<env>.yaml):
  - gcp_secret_manager     (requires `google-cloud-secret-manager`)
  - aws_secretsmanager     (requires `boto3`)
  - env                    (reads from environment variables — for local dev only)
  - file                   (reads from a local .env file — for local dev only)

Usage:
    python render_secrets.py --env prod agent.committed.json > /tmp/agent.rendered.json
    python render_secrets.py --env dev  agent.committed.json --in-place
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Callable

# Optional imports (skip silently; fail at use time with a clear message).
try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

PLACEHOLDER_RE = re.compile(r"<<([A-Z0-9_]+)>>")


# ── providers ────────────────────────────────────────────────────────────

def _provider_gcp(project: str) -> Callable[[str, str], str]:
    try:
        from google.cloud import secretmanager  # type: ignore
    except ImportError:
        sys.exit("google-cloud-secret-manager not installed; pip install google-cloud-secret-manager")
    client = secretmanager.SecretManagerServiceClient()

    def fetch(secret: str, version: str = "latest") -> str:
        name = f"projects/{project}/secrets/{secret}/versions/{version}"
        return client.access_secret_version(name=name).payload.data.decode("utf-8")

    return fetch


def _provider_aws(region: str | None) -> Callable[[str, str], str]:
    try:
        import boto3  # type: ignore
    except ImportError:
        sys.exit("boto3 not installed; pip install boto3")
    client = boto3.client("secretsmanager", region_name=region) if region else boto3.client("secretsmanager")

    def fetch(secret: str, version: str = "AWSCURRENT") -> str:
        resp = client.get_secret_value(SecretId=secret, VersionStage=version)
        return resp.get("SecretString", "")

    return fetch


def _provider_env() -> Callable[[str, str], str]:
    def fetch(secret: str, version: str = "") -> str:
        val = os.environ.get(secret)
        if val is None:
            sys.exit(f"env var {secret} not set")
        return val
    return fetch


def _provider_file(path: str) -> Callable[[str, str], str]:
    env: dict[str, str] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"\'')

    def fetch(secret: str, version: str = "") -> str:
        if secret not in env:
            sys.exit(f"{path}: missing {secret}")
        return env[secret]
    return fetch


# ── core ─────────────────────────────────────────────────────────────────

def load_mapping(env_yaml: Path) -> tuple[Callable[[str, str], str], dict[str, dict]]:
    if yaml is None:
        sys.exit("pyyaml not installed; pip install pyyaml")
    cfg = yaml.safe_load(env_yaml.read_text(encoding="utf-8"))
    provider = cfg.get("provider")
    mapping = cfg.get("mapping", {})

    if provider == "gcp_secret_manager":
        fetch = _provider_gcp(cfg["project"])
    elif provider == "aws_secretsmanager":
        fetch = _provider_aws(cfg.get("region"))
    elif provider == "env":
        fetch = _provider_env()
    elif provider == "file":
        fetch = _provider_file(cfg["path"])
    else:
        sys.exit(f"unknown provider: {provider}")
    return fetch, mapping


def render(text: str, fetch: Callable[[str, str], str], mapping: dict[str, dict]) -> str:
    cache: dict[str, str] = {}

    def replace(m: re.Match[str]) -> str:
        token = m.group(1)
        if token in cache:
            return cache[token]
        spec = mapping.get(token)
        if not spec:
            sys.exit(f"placeholder <<{token}>> not declared in mapping")
        value = fetch(spec["secret"], spec.get("version", ""))
        cache[token] = value
        return value

    return PLACEHOLDER_RE.sub(replace, text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", help="committed config file with <<PLACEHOLDERS>>")
    ap.add_argument("--env", required=True, help="environment label (dev/staging/prod)")
    ap.add_argument("--secrets-dir", default="secrets",
                    help="directory containing secrets.<env>.yaml")
    ap.add_argument("--in-place", action="store_true",
                    help="write rendered output back to <file> (DANGEROUS — only for dev)")
    ap.add_argument("--strict", action="store_true",
                    help="fail if any placeholder remains unsubstituted")
    args = ap.parse_args()

    env_yaml = Path(args.secrets_dir) / f"secrets.{args.env}.yaml"
    if not env_yaml.exists():
        sys.exit(f"no secrets file: {env_yaml}")

    fetch, mapping = load_mapping(env_yaml)
    text = Path(args.file).read_text(encoding="utf-8")
    rendered = render(text, fetch, mapping)

    if args.strict and PLACEHOLDER_RE.search(rendered):
        sys.exit("unsubstituted placeholders remain")

    if args.in_place:
        Path(args.file).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
