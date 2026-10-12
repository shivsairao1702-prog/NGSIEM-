"""Tests for module 02 (user management).

Three groups:
  1. the review tool finds exactly the problems planted in sample-data/
  2. the shipped registers and policy are clean and internally consistent
  3. module 02 stays consistent with module 01 (roles, privilege, headcounts)
"""
import csv
import importlib.util
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
M01 = ROOT.parent / "01-architecture"
AS_OF = date(2026, 10, 12)

spec = importlib.util.spec_from_file_location("access_review", ROOT / "scripts" / "access_review.py")
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)


def read_text(p):
    return Path(p).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def policy():
    return json.loads(read_text(ROOT / "config" / "role-assignment-policy.json"))


@pytest.fixture(scope="module")
def users():
    return ar.read_csv(ROOT / "config" / "user-register.csv")


@pytest.fixture(scope="module")
def clients():
    return ar.read_csv(ROOT / "config" / "api-client-register.csv")


@pytest.fixture(scope="module")
def planted(policy):
    d = ROOT / "sample-data"
    return ar.run_review(policy, ar.read_csv(d / "user-register-with-issues.csv"),
                         ar.read_csv(d / "api-client-register-with-issues.csv"),
                         ar.read_csv(d / "console-export-with-issues.csv"), AS_OF)


@pytest.fixture(scope="module")
def matrix():
    with open(M01 / "config" / "rbac-matrix.csv", newline="", encoding="utf-8") as fh:
        return {r["capability"]: r for r in csv.DictReader(fh)}


# ------------------------------------------------------------ 1. tool behaviour
# Independent oracle: every error below was planted by hand in sample-data/.
PLANTED_ERRORS = {
    ("U01", "nw-intern-01"), ("U02", "nw-soc-l1-02"), ("U03", "nw-soc-l1-03"), ("U04", "nw-soc-l1-04"),
    ("U05", "nw-deteng-01"), ("U05", "nw-platform-02"), ("U06", "falcon_platform_owner"), ("U08", "nw-bg-02"),
    ("C01", "nw-shadow-01"), ("C03", "nw-soc-l1-01"), ("C04", "nw-deteng-02"),
    ("A01", "apic-fusion-containment-legacy"), ("A02", "apic-falconpy-inventory-write"),
    ("A03", "apic-fusion-ticketing-old"), ("A05", "apic-chatops-bot"),
}


def test_tool_finds_every_planted_error_and_no_other_error(planted):
    errors = {(f.code, f.subject) for f in planted if f.severity == "error"}
    assert errors == PLANTED_ERRORS, f"missing {PLANTED_ERRORS - errors}, unexpected {errors - PLANTED_ERRORS}"


def test_full_findings_match_the_locked_expected_file(planted):
    expected = json.loads(read_text(ROOT / "sample-data" / "expected-findings.json"))
    assert sorted([f.code, f.subject] for f in planted) == sorted(expected)


def test_every_finding_code_is_exercised_by_the_planted_data(planted):
    emitted = {f.code for f in planted}
    assert emitted == set(ar.CODES), f"never exercised: {set(ar.CODES) - emitted}"


def test_severity_in_findings_matches_the_code_table(planted):
    for f in planted:
        assert f.severity == ar.CODES[f.code][0]


def run_cli(*args):
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "access_review.py"), *args],
                          capture_output=True, text=True)


def test_cli_exit_codes():
    d = ROOT / "sample-data"
    clean = run_cli("--as-of", "2026-10-12", "--console", str(d / "console-export-clean.csv"))
    assert clean.returncode == 0, clean.stdout
    strict = run_cli("--as-of", "2026-10-12", "--strict")
    assert strict.returncode == 1, "--strict must fail on the unverified-scope warnings"
    bad = run_cli("--as-of", "2026-10-12", "--users", str(d / "user-register-with-issues.csv"))
    assert bad.returncode == 1


def test_review_dates_matter():
    # Shipped data is clean on the review date but goes stale: reviews and rotations expire.
    pol = json.loads(read_text(ROOT / "config" / "role-assignment-policy.json"))
    users = ar.read_csv(ROOT / "config" / "user-register.csv")
    clients = ar.read_csv(ROOT / "config" / "api-client-register.csv")
    later = {f.code for f in ar.run_review(pol, users, clients, None, date(2027, 3, 1)) if f.severity == "error"}
    assert {"U05", "U08", "A03"} <= later


# ------------------------------------------------------------ 2. shipped data
def test_shipped_registers_have_no_errors(policy, users, clients):
    findings = ar.run_review(policy, users, clients, None, AS_OF)
    assert [f for f in findings if f.severity == "error"] == []


def test_only_remaining_findings_are_unverified_scopes(policy, users, clients):
    findings = ar.run_review(policy, users, clients, None, AS_OF)
    assert {f.code for f in findings} == {"A04"}
    assert len(findings) == len(clients)


def test_clean_console_export_reconciles_with_register(policy, users, clients):
    console = ar.read_csv(ROOT / "sample-data" / "console-export-clean.csv")
    findings = ar.run_review(policy, users, clients, console, AS_OF)
    assert not [f for f in findings if f.code.startswith("C")]


def test_no_shared_or_generic_accounts(users):
    ids = [u["user_id"] for u in users]
    assert len(ids) == len(set(ids)), "duplicate user ids"
    assert all(re.fullmatch(r"nw-[a-z0-9]+(-[a-z0-9]+)*", i) for i in ids)
    assert not [i for i in ids if re.search(r"(shared|generic|admin\d*$|test)", i)]


def test_every_named_user_uses_sso_and_only_break_glass_is_local(users):
    for u in users:
        if u["account_type"] == "named":
            assert u["sso_group"], u["user_id"]
        else:
            assert u["account_type"] == "break_glass" and u["persona"] == "break_glass" and not u["sso_group"]


def test_break_glass_limits_agree_between_policy_sections(policy):
    assert policy["authentication"]["break_glass"]["max_accounts"] == policy["personas"]["break_glass"]["max_holders"]
    assert policy["authentication"]["break_glass"]["max_accounts"] <= 2


def test_privileged_review_is_stricter_than_standard(policy):
    r = policy["review"]
    assert r["privileged_cadence_days"] < r["cadence_days"] <= 90
    assert policy["lifecycle"]["leaver_disable_hours"] <= 24
    assert policy["authentication"]["sso_required_for_named_users"] is True
    assert policy["authentication"]["phishing_resistant_mfa_for_privileged"] is True


def test_every_api_client_follows_naming_scope_and_secret_rules(policy, clients):
    allow = policy["api_clients"]["scope_allowlist"]
    assert {c["integration"] for c in clients} <= set(allow)
    for c in clients:
        assert c["client_id"] == f"apic-{c['integration']}"
        assert c["secret_storage_ref"].startswith("vault://"), "store a reference, never a secret"
        assert int(c["rotation_days"]) <= policy["api_clients"]["rotation_days"] <= 90
        assert set(c["intended_scopes"].split(";")) <= set(allow[c["integration"]])


def test_one_api_client_per_integration(clients):
    integrations = [c["integration"] for c in clients]
    assert len(integrations) == len(set(integrations))


# ------------------------------------------------------------ 3. consistency with module 01
def roles_with(matrix, capability):
    return {k for k, v in matrix[capability].items() if k != "capability" and v == "Y"}


def test_every_persona_maps_to_a_role_in_the_module_01_matrix(policy, matrix):
    matrix_roles = set(next(iter(matrix.values()))) - {"capability"}
    for key, p in policy["personas"].items():
        assert p["matrix_role"] in matrix_roles, f"{key} -> {p['matrix_role']} not in module 01 matrix"


def test_privileged_flag_is_derived_from_module_01_capabilities(policy, matrix):
    privileged_roles = set()
    for cap in policy["privileged_capabilities"]:
        assert cap in matrix, f"{cap} is not a module 01 capability"
        privileged_roles |= roles_with(matrix, cap)
    for key, p in policy["personas"].items():
        assert p["privileged"] == (p["matrix_role"] in privileged_roles), (
            f"{key}: privileged={p['privileged']} but module 01 says role {p['matrix_role']} "
            f"{'has' if p['matrix_role'] in privileged_roles else 'has no'} privileged capability")


def test_user_and_api_admin_stays_with_the_falcon_owner_persona(policy, matrix):
    holders = {k for k, p in policy["personas"].items()
               if p["matrix_role"] in roles_with(matrix, "manage_users_and_roles")}
    assert holders == {"falcon_platform_owner", "break_glass"}


def test_only_l2_owner_and_break_glass_can_hold_containment(policy, matrix):
    holders = {k for k, p in policy["personas"].items()
               if p["matrix_role"] in roles_with(matrix, "contain_host_rtr")}
    assert holders == {"soc_l2_ir", "falcon_platform_owner", "break_glass"}


def test_headcounts_match_module_01_persona_table(policy):
    rbac_doc = read_text(M01 / "docs" / "05-rbac.md")
    labels = {
        "soc_l1": "SOC Analyst L1", "soc_l2_ir": "SOC Analyst L2 / Incident responder",
        "detection_engineer": "Detection engineer", "platform_engineer": "Platform engineer",
        "auditor": "Auditor / compliance", "falcon_platform_owner": "Falcon platform owner",
    }
    for key, label in labels.items():
        row = re.search(rf"\| {re.escape(label)} \| (\d+) \|", rbac_doc)
        assert row, f"{label} missing from module 01 docs/05-rbac.md"
        assert int(row.group(1)) == policy["personas"][key]["headcount_planned"], key


def test_registers_match_planned_headcounts(policy, users):
    active = {}
    for u in users:
        if u["status"] == "active":
            active[u["persona"]] = active.get(u["persona"], 0) + 1
    for key, p in policy["personas"].items():
        assert active.get(key, 0) == p["headcount_planned"], key


def test_containment_policy_roles_in_module_01_are_real_personas(policy):
    cp = json.loads(read_text(M01 / "config" / "containment-policy.json"))
    matrix_roles = {p["matrix_role"] for p in policy["personas"].values()}
    assert cp["approval"]["approver_role"] in matrix_roles
    assert cp["rollback"]["lift_containment_role"] in matrix_roles


def test_containment_api_client_exists_and_is_minimally_scoped(policy, clients):
    c = next(c for c in clients if c["integration"] == "fusion-containment")
    assert set(c["intended_scopes"].split(";")) == {"hosts:read", "hosts:write"}
    assert c["owner_persona"] in policy["personas"]


def test_module_readme_counts_match_registers(users, clients):
    readme = read_text(ROOT / "README.md")
    named = sum(u["account_type"] == "named" for u in users)
    bg = sum(u["account_type"] == "break_glass" for u in users)
    assert f"{named} named users" in readme
    assert f"{bg} break-glass accounts" in readme
    assert f"{len(clients)} API clients" in readme


def test_user_model_doc_table_matches_the_policy(policy):
    doc = read_text(ROOT / "docs" / "01-user-model.md")
    for key, p in policy["personas"].items():
        row = re.search(rf"\| `{key}` \| `{p['matrix_role']}` \| (\d+) \| (\d+) \| (yes|no) \|", doc)
        assert row, f"{key} row missing or role differs in docs/01-user-model.md"
        assert int(row.group(1)) == p["headcount_planned"], key
        assert int(row.group(2)) == p["max_holders"], key
        assert (row.group(3) == "yes") == p["privileged"], key


def test_review_doc_lists_every_finding_code():
    doc = read_text(ROOT / "docs" / "05-access-reviews.md")
    for code, (severity, _) in ar.CODES.items():
        row = re.search(rf"\| {code} \| (error|warning) \|", doc)
        assert row, f"{code} missing from docs/05-access-reviews.md"
        assert row.group(1) == severity, f"{code}: doc says {row.group(1)}, tool says {severity}"


def test_adr_007_states_the_real_number_of_finding_codes():
    adr = read_text(ROOT / "docs" / "07-decisions-adr.md")
    words = {17: "Seventeen"}
    assert words[len(ar.CODES)] in adr


def test_monitoring_doc_has_ten_events_and_tools_for_each_access_path():
    doc = read_text(ROOT / "docs" / "06-audit-and-monitoring.md")
    ids = re.findall(r"^\| (M\d\d) \|", doc, flags=re.MULTILINE)
    assert ids == [f"M{i:02d}" for i in range(1, 11)]


def test_readme_quotes_the_real_planted_finding_counts(planted):
    errors = sum(f.severity == "error" for f in planted)
    warnings = len(planted) - errors
    assert f"{errors} errors and {warnings} warnings" in read_text(ROOT / "README.md")
