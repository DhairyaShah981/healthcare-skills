#!/usr/bin/env python3
"""
lint_voice_agent.py — RTL-001 to RTL-017 linter for Retell / Vapi agent JSON.

Usage:
    python lint_voice_agent.py path/to/agent.json
    python lint_voice_agent.py --json path/to/agent.json   # machine-readable output
    python lint_voice_agent.py --strict path/to/agent.json # WARN promoted to ERROR

Exit codes:
    0 — all checks pass
    1 — one or more ERROR findings
    2 — JSON parse failure
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from typing import Any

ALLOWED_PARAM_TYPES = {"string", "number", "integer", "boolean", "array", "object"}
ALLOWED_ANALYSIS_TYPES = {"string", "number", "boolean", "enum"}
BCP47_RE = re.compile(r"^[a-z]{2,3}(-[A-Z]{2}|-[0-9]{3})?$")
NGROK_LOCAL_RE = re.compile(
    r"(ngrok\.(io|app)|\blocalhost\b|\b127\.0\.0\.1\b|\.local(?::|/|$))", re.I
)
PLACEHOLDER_RE = re.compile(r"<<[A-Z0-9_]+>>")


@dataclass
class Finding:
    rule: str
    severity: str
    message: str
    path: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def lint(agent: dict[str, Any]) -> list[Finding]:
    out: list[Finding] = []
    cf = agent.get("conversationFlow", {}) or {}
    tools = agent.get("tools", []) or []
    tools_by_name = {t.get("name"): t for t in tools if isinstance(t, dict)}

    # RTL-001
    if "is_transfer_cf" not in cf:
        out.append(Finding("RTL-001", "ERROR", "conversationFlow.is_transfer_cf is missing",
                           "conversationFlow.is_transfer_cf"))

    # RTL-006
    if not cf.get("start_node_id"):
        out.append(Finding("RTL-006", "ERROR", "conversationFlow.start_node_id is missing",
                           "conversationFlow.start_node_id"))

    nodes = cf.get("nodes", []) or []
    node_ids = [n.get("id") for n in nodes if isinstance(n, dict)]
    if node_ids and cf.get("start_node_id") and cf["start_node_id"] not in node_ids:
        out.append(Finding("RTL-006", "ERROR",
                           f"start_node_id '{cf['start_node_id']}' does not match any node",
                           "conversationFlow.start_node_id"))

    # RTL-005
    seen: set[str] = set()
    for i, nid in enumerate(node_ids):
        if nid in seen:
            out.append(Finding("RTL-005", "ERROR", f"duplicate node id '{nid}'",
                               f"conversationFlow.nodes[{i}].id"))
        seen.add(nid)

    # RTL-003, RTL-014
    for i, n in enumerate(nodes):
        if isinstance(n, dict) and n.get("type") == "function":
            tid = n.get("tool_id")
            if not tid:
                out.append(Finding("RTL-014", "ERROR", "function node has empty tool_id",
                                   f"conversationFlow.nodes[{i}].tool_id"))
            elif tid not in tools_by_name and tid not in {t.get("id") for t in tools if isinstance(t, dict)}:
                out.append(Finding("RTL-003", "ERROR",
                                   f"function node references unknown tool '{tid}'",
                                   f"conversationFlow.nodes[{i}].tool_id"))

    # RTL-004, RTL-013
    edges = cf.get("edges", []) or []
    edge_ids: set[str] = set()
    node_id_set = set(node_ids)
    for i, e in enumerate(edges):
        if not isinstance(e, dict):
            continue
        eid = e.get("id")
        if eid in edge_ids:
            out.append(Finding("RTL-013", "ERROR", f"duplicate edge id '{eid}'",
                               f"conversationFlow.edges[{i}].id"))
        edge_ids.add(eid)
        dst = e.get("destination_node_id")
        if dst and dst not in node_id_set:
            out.append(Finding("RTL-004", "ERROR",
                               f"edge destination_node_id '{dst}' does not resolve",
                               f"conversationFlow.edges[{i}].destination_node_id"))

    # Tools-related rules
    for i, t in enumerate(tools):
        if not isinstance(t, dict):
            continue
        url = t.get("url", "")
        if url and not url.startswith("https://") and not PLACEHOLDER_RE.search(url):
            out.append(Finding("RTL-009", "ERROR", f"tool url is not https: {url}",
                               f"tools[{i}].url"))
        if url and NGROK_LOCAL_RE.search(url) and not PLACEHOLDER_RE.search(url):
            out.append(Finding("RTL-016", "ERROR",
                               f"tool url contains ngrok / localhost / .local: {url}",
                               f"tools[{i}].url"))
        if "webhook_secret" in t and isinstance(t["webhook_secret"], str) and not PLACEHOLDER_RE.search(t["webhook_secret"]):
            out.append(Finding("RTL-017", "WARN", "webhook_secret appears to be plaintext",
                               f"tools[{i}].webhook_secret"))
        params = t.get("parameters", {}) or {}
        required = params.get("required")
        if "parameters" in t and (required is None or (isinstance(required, list) and not required)):
            out.append(Finding("RTL-002", "ERROR",
                               f"tools[{i}] '{t.get('name')}' has empty parameters.required",
                               f"tools[{i}].parameters.required"))
        props = params.get("properties", {}) or {}
        for pname, pdef in props.items() if isinstance(props, dict) else []:
            if not isinstance(pdef, dict):
                continue
            if not pdef.get("description"):
                out.append(Finding("RTL-011", "ERROR",
                                   f"parameter '{pname}' is missing description",
                                   f"tools[{i}].parameters.properties.{pname}.description"))
            ptype = pdef.get("type")
            if ptype and ptype not in ALLOWED_PARAM_TYPES:
                out.append(Finding("RTL-012", "ERROR",
                                   f"parameter '{pname}' has invalid type '{ptype}'",
                                   f"tools[{i}].parameters.properties.{pname}.type"))

    # RTL-007
    for i, p in enumerate(agent.get("post_call_analysis_data", []) or []):
        if isinstance(p, dict) and p.get("type") not in ALLOWED_ANALYSIS_TYPES:
            out.append(Finding("RTL-007", "ERROR",
                               f"post_call_analysis_data[{i}].type='{p.get('type')}' not in allowed set",
                               f"post_call_analysis_data[{i}].type"))

    # RTL-008
    lang = agent.get("language")
    if lang and not BCP47_RE.match(str(lang)):
        out.append(Finding("RTL-008", "ERROR",
                           f"language '{lang}' is not BCP-47 (try 'en-US', 'es-MX')",
                           "language"))

    return out


def report_human(findings: list[Finding]) -> str:
    if not findings:
        return "All 17 rules pass. Ready to deploy.\n"
    lines = []
    for f in findings:
        lines.append(f"  {f.rule}  {f.severity:<5}  {f.message}\n    → {f.path}")
    errors = sum(1 for f in findings if f.severity == "ERROR")
    warns = sum(1 for f in findings if f.severity == "WARN")
    verdict = "BLOCK DEPLOY" if errors else "OK (with warnings)" if warns else "OK"
    lines.append(f"\n{len(findings)} findings — {errors} ERROR, {warns} WARN")
    lines.append(f"Verdict: {verdict}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true",
                    help="promote WARN findings to ERROR")
    args = ap.parse_args()

    try:
        with open(args.path, encoding="utf-8") as f:
            agent = json.load(f)
    except json.JSONDecodeError as e:
        print(f"RTL-000 JSON parse failure: {e}", file=sys.stderr)
        return 2

    findings = lint(agent)
    if args.strict:
        for f in findings:
            if f.severity == "WARN":
                f.severity = "ERROR"

    if args.json:
        print(json.dumps([f.to_dict() for f in findings], indent=2))
    else:
        print(report_human(findings))

    return 1 if any(f.severity == "ERROR" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
