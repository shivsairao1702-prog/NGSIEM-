#!/usr/bin/env python3
"""Access review for NG-SIEM user management.

Compares the user and API client registers, and optionally a console export, with
config/role-assignment-policy.json, and reports every deviation as a finding.

    python3 scripts/access_review.py                      # review the shipped registers
    python3 scripts/access_review.py --console export.csv --as-of 2026-10-12
    python3 scripts/access_review.py --format json --strict

Exit status: 0 = no errors, 1 = at least one error (or any finding with --strict).
Standard library only.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

MODULE = Path(__file__).resolve().parent.parent

# Every finding code the tool can emit. Tests require each one to be exercised by the
# planted-issue datasets in sample-data/, so a check cannot silently stop working.
CODES = {
    "U01": ("error", "Persona is not defined in the policy"),
    "U02": ("error", "Matrix role does not match the persona's role"),
    "U03": ("error", "Named user has no SSO group"),
    "U04": ("error", "Account is still active after its end date"),
    "U05": ("error", "Access review is overdue"),
    "U06": ("error", "More holders than the persona allows"),
    "U07": ("warning", "Active holders differ from the planned headcount"),
    "U08": ("error", "Break-glass account test is overdue"),
    "C01": ("error", "Console account is not in the register"),
    "C02": ("warning", "Active register user is missing from the console"),
    "C03": ("error", "Console roles differ from the policy for the persona"),
    "C04": ("error", "Account disabled in the register is still present in the console"),
    "A01": ("error", "API client has no valid owner persona"),
    "A02": ("error", "API client scopes exceed the allowlist for its integration"),
    "A03": ("error", "API client secret rotation is overdue"),
    "A04": ("warning", "API client scopes have not been verified against the console"),
    "A05": ("error", "API client integration is not in the scope allowlist"),
}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    subject: str
    message: str


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def parse_date(value):
    return date.fromisoformat(value) if value else None


def split(value):
    return [v for v in (value or "").split(";") if v]


def make(code, subject, detail=""):
    sev, text = CODES[code]
    return Finding(code, sev, subject, f"{text}{': ' + detail if detail else ''}")


def review_users(policy, users, as_of):
    out = []
    personas = policy["personas"]
    cadence = policy["review"]["cadence_days"]
    priv_cadence = policy["review"]["privileged_cadence_days"]
    test_cadence = policy["authentication"]["break_glass"]["test_cadence_days"]
    active = [u for u in users if u["status"] == "active"]

    for u in users:
        uid, persona = u["user_id"], personas.get(u["persona"])
        if persona is None:
            out.append(make("U01", uid, f"persona '{u['persona']}'"))
        elif u["matrix_role"] != persona["matrix_role"]:
            out.append(make("U02", uid, f"has {u['matrix_role']}, persona {u['persona']} allows {persona['matrix_role']}"))
        if u["status"] != "active":
            continue
        if u["account_type"] == "named" and not u["sso_group"]:
            out.append(make("U03", uid))
        end = parse_date(u["end_date"])
        if end and end <= as_of:
            out.append(make("U04", uid, f"ended {end.isoformat()}"))
        limit = priv_cadence if (persona and persona["privileged"]) else cadence
        reviewed = parse_date(u["last_access_review"])
        if reviewed is None or as_of - reviewed > timedelta(days=limit):
            when = reviewed.isoformat() if reviewed else "never"
            out.append(make("U05", uid, f"last reviewed {when}, limit {limit} days"))
        if u["account_type"] == "break_glass":
            tested = parse_date(u["last_tested"])
            if tested is None or as_of - tested > timedelta(days=test_cadence):
                out.append(make("U08", uid, f"last tested {tested.isoformat() if tested else 'never'}"))

    counts = Counter(u["persona"] for u in active)
    for key, persona in personas.items():
        n = counts.get(key, 0)
        if n > persona["max_holders"]:
            out.append(make("U06", key, f"{n} holders, maximum {persona['max_holders']}"))
        if n != persona["headcount_planned"]:
            out.append(make("U07", key, f"{n} active, {persona['headcount_planned']} planned"))
    return out


def review_console(policy, users, console):
    out = []
    personas = policy["personas"]
    register = {u["user_id"]: u for u in users}
    console_by_id = {r["user_id"]: set(split(r["console_roles"])) for r in console}

    for uid, roles in console_by_id.items():
        u = register.get(uid)
        if u is None:
            out.append(make("C01", uid))
            continue
        if u["status"] != "active":
            out.append(make("C04", uid, f"register status '{u['status']}'"))
            continue
        persona = personas.get(u["persona"])
        if persona and roles != set(persona["console_roles"]):
            out.append(make("C03", uid, f"console {sorted(roles)}, policy {sorted(persona['console_roles'])}"))
    for uid, u in register.items():
        if u["status"] == "active" and uid not in console_by_id:
            out.append(make("C02", uid))
    return out


def review_clients(policy, clients, as_of):
    out = []
    api = policy["api_clients"]
    for c in clients:
        cid = c["client_id"]
        if c["status"] != "active":
            continue
        if c["owner_persona"] not in policy["personas"]:
            out.append(make("A01", cid, f"owner '{c['owner_persona']}'"))
        allowed = api["scope_allowlist"].get(c["integration"])
        if allowed is None:
            out.append(make("A05", cid, f"integration '{c['integration']}'"))
        else:
            extra = sorted(set(split(c["intended_scopes"])) - set(allowed))
            if extra:
                out.append(make("A02", cid, f"extra scopes {extra}"))
        rotated = parse_date(c["last_rotated"])
        days = int(c["rotation_days"] or api["rotation_days"])
        if rotated is None or as_of - rotated > timedelta(days=min(days, api["rotation_days"])):
            out.append(make("A03", cid, f"last rotated {rotated.isoformat() if rotated else 'never'}"))
        if c["scopes_verified"] != "yes":
            out.append(make("A04", cid))
    return out


def run_review(policy, users, clients, console=None, as_of=None):
    as_of = as_of or date.today()
    findings = review_users(policy, users, as_of) + review_clients(policy, clients, as_of)
    if console is not None:
        findings += review_console(policy, users, console)
    return sorted(findings, key=lambda f: (f.severity != "error", f.code, f.subject))


def to_markdown(findings, as_of, inputs):
    errors = sum(f.severity == "error" for f in findings)
    warnings = len(findings) - errors
    lines = [f"# Access review as of {as_of.isoformat()}", "",
             f"Inputs: {', '.join(inputs)}", "",
             f"**{errors} error(s), {warnings} warning(s)**", ""]
    if not findings:
        lines.append("No findings.")
    else:
        lines += ["| Severity | Code | Subject | Finding |", "|---|---|---|---|"]
        lines += [f"| {f.severity} | {f.code} | `{f.subject}` | {f.message} |" for f in findings]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--policy", default=MODULE / "config" / "role-assignment-policy.json")
    ap.add_argument("--users", default=MODULE / "config" / "user-register.csv")
    ap.add_argument("--clients", default=MODULE / "config" / "api-client-register.csv")
    ap.add_argument("--console", help="CSV export of console users: user_id,console_roles (semicolon separated)")
    ap.add_argument("--as-of", type=date.fromisoformat, default=date.today(), help="review date (YYYY-MM-DD)")
    ap.add_argument("--format", choices=["md", "json"], default="md")
    ap.add_argument("--strict", action="store_true", help="exit 1 on warnings as well as errors")
    args = ap.parse_args(argv)

    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
    console = read_csv(args.console) if args.console else None
    findings = run_review(policy, read_csv(args.users), read_csv(args.clients), console, args.as_of)

    inputs = [Path(args.users).name, Path(args.clients).name] + ([Path(args.console).name] if args.console else [])
    if args.format == "json":
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        print(to_markdown(findings, args.as_of, inputs), end="")
    failed = any(f.severity == "error" for f in findings) or (args.strict and findings)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
