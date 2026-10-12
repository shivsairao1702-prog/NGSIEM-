"""Consistency checks for the ngsiem-architecture project.

The sizing workbook is the source of truth for every number quoted in the docs.
These tests fail if a document drifts from the workbook, if a repository is given
two retention periods, or if the RBAC matrix breaks a separation-of-duties rule.
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import pytest
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parent.parent
WORKBOOK = ROOT / "sample-data" / "sizing-calculator.xlsx"
RBAC = ROOT / "config" / "rbac-matrix.csv"
DOCS = ROOT / "docs"

SIZING_FIRST_ROW = 5
COMPRESSION_CELL = ("Assumptions", "B5")


def read(path):
    return Path(path).read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def wb():
    # data_only=True reads the values cached by the last recalculation.
    return load_workbook(WORKBOOK, data_only=True)


@pytest.fixture(scope="module")
def sources(wb):
    s = wb["Sizing"]
    rows = []
    r = SIZING_FIRST_ROW
    while s.cell(r, 1).value and str(s.cell(r, 1).value).startswith("SRC-"):
        rows.append(
            dict(
                id=s.cell(r, 1).value,
                category=s.cell(r, 3).value,
                repo=s.cell(r, 5).value,
                ingest=s.cell(r, 10).value,
                retention=s.cell(r, 11).value,
            )
        )
        r += 1
    return rows


@pytest.fixture(scope="module")
def summary(wb):
    m = wb["Summary"]
    return {m.cell(r, 1).value: m.cell(r, 2).value for r in range(4, 16)}


# ---------------------------------------------------------------- workbook
def test_workbook_has_cached_values_and_no_errors(wb):
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                assert not (isinstance(cell.value, str) and cell.value.startswith("#")), (
                    f"error value {cell.value} in {ws.title}!{cell.coordinate}"
                )
    assert wb["Summary"]["B9"].value is not None, "workbook was not recalculated before commit"


def test_every_source_is_listed(sources):
    assert len(sources) == 9


def test_one_retention_period_per_repository(sources):
    retention = defaultdict(set)
    for s in sources:
        retention[s["repo"]].add(s["retention"])
    mixed = {repo: sorted(v) for repo, v in retention.items() if len(v) > 1}
    assert not mixed, f"retention is set per repository; mixed values in {mixed}"


def test_category_breakdown_sums_to_total(wb):
    m = wb["Summary"]
    assert m["A26"].value == "TOTAL"
    assert m["B26"].value == pytest.approx(m["B9"].value, abs=1e-6)
    assert m["B27"].value == "OK"


def test_growth_headroom_is_arithmetically_consistent(summary):
    after = summary["Ingest after filtering (GB/day)"]
    grown = summary["Ingest incl. growth buffer (GB/day)"]
    free = summary["Free third-party tier (GB/day)"]
    assert summary["Headroom vs free tier - today (GB/day)"] == pytest.approx(free - after)
    assert summary["Headroom vs free tier - with growth (GB/day)"] == pytest.approx(free - grown)


# ---------------------------------------------------------------- docs vs workbook
def test_headline_numbers_in_docs_match_workbook(summary):
    sizing = read(DOCS / "03-sizing.md")
    readme = read(ROOT / "README.md")
    adr = read(DOCS / "07-decisions-adr.md")
    expected = {
        "raw": f"{summary['Raw ingest (GB/day)']:.2f}",
        "filtered": f"{summary['Ingest after filtering (GB/day)']:.2f}",
        "grown": f"{summary['Ingest incl. growth buffer (GB/day)']:.2f}",
        "saved": f"{summary['Saved by pre-ingest filtering (GB/day)']:.2f}",
    }
    for label, value in expected.items():
        assert value in sizing, f"{label} {value} missing from docs/03-sizing.md"
    assert expected["filtered"] in readme and expected["grown"] in readme
    assert expected["filtered"] in adr and expected["grown"] in adr


def test_repository_table_in_sizing_doc_matches_workbook(sources, wb):
    sizing = read(DOCS / "03-sizing.md")
    compression = wb[COMPRESSION_CELL[0]][COMPRESSION_CELL[1]].value
    ingest, retention = defaultdict(float), {}
    for s in sources:
        ingest[s["repo"]] += s["ingest"]
        retention[s["repo"]] = s["retention"]
    for repo in ingest:
        row = re.search(rf"\| {re.escape(repo)} \| ([\d.]+) \| (\d+) \| ([\d.]+) \|", sizing)
        assert row, f"{repo} missing from repository table in docs/03-sizing.md"
        assert float(row.group(1)) == pytest.approx(ingest[repo], abs=0.001)
        assert int(row.group(2)) == retention[repo]
        assert float(row.group(3)) == pytest.approx(ingest[repo] * retention[repo] / compression, abs=0.06)


def test_retention_table_in_retention_doc_matches_workbook(sources):
    doc = read(DOCS / "04-retention-and-repositories.md")
    retention = {s["repo"]: s["retention"] for s in sources}
    for repo, days in retention.items():
        row = re.search(rf"\| `{re.escape(repo)}` \|[^\n]*\| (\d+) days \|", doc)
        assert row, f"{repo} missing from docs/04-retention-and-repositories.md"
        assert int(row.group(1)) == days, f"{repo}: doc says {row.group(1)} days, workbook says {days}"


def test_docs_only_reference_repositories_that_exist(sources):
    known = {s["repo"] for s in sources}
    for path in [*DOCS.glob("*.md"), ROOT / "README.md"]:
        for name in set(re.findall(r"repo-[a-z]+(?:-[a-z]+)*", read(path))):
            assert name in known, f"{path.name} references unknown repository {name}"


def test_every_source_path_in_dataflow_doc_exists_in_workbook(sources):
    doc = read(DOCS / "02-data-flow.md")
    for s in sources:
        assert s["id"] in doc, f"{s['id']} missing from docs/02-data-flow.md"


# ---------------------------------------------------------------- RBAC matrix
@pytest.fixture(scope="module")
def rbac():
    with open(RBAC, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {r["capability"]: r for r in rows}


def roles_with(rbac, capability):
    row = rbac[capability]
    return {k for k, v in row.items() if k != "capability" and v == "Y"}


def test_rbac_matrix_values_are_only_y_or_n(rbac):
    for cap, row in rbac.items():
        for role, value in row.items():
            if role != "capability":
                assert value in {"Y", "N"}, f"{cap}/{role} has invalid value {value!r}"


def test_read_only_role_cannot_change_anything(rbac):
    read_only_allowed = {"search_events_in_assigned_views", "view_detections_and_cases"}
    for cap, row in rbac.items():
        if cap not in read_only_allowed:
            assert row["analyst_read_only"] == "N", f"read-only role can {cap}"


def test_user_and_api_client_management_is_falcon_admin_only(rbac):
    assert roles_with(rbac, "manage_users_and_roles") == {"falcon_admin"}
    assert roles_with(rbac, "manage_api_clients") == {"falcon_admin"}


def test_containment_is_not_granted_to_l1_or_read_only(rbac):
    granted = roles_with(rbac, "contain_host_rtr")
    assert granted == {"analyst_l2_ir", "falcon_admin", "api_client_fusion"}


def test_ingest_and_retention_changes_are_not_analyst_powers(rbac):
    for cap in ("manage_parsers", "manage_data_connectors_and_hec_tokens", "manage_repositories_and_retention"):
        granted = roles_with(rbac, cap)
        assert granted == {"platform_engineer", "falcon_admin"}, f"{cap} granted to {granted}"


def test_detection_engineers_cannot_change_ingestion(rbac):
    for cap in ("manage_parsers", "manage_data_connectors_and_hec_tokens", "manage_repositories_and_retention"):
        assert rbac[cap]["detection_engineer"] == "N"


def test_automation_client_has_minimal_scope(rbac):
    allowed = {"run_fusion_workflow_actions", "contain_host_rtr"}
    granted = {cap for cap in rbac if rbac[cap]["api_client_fusion"] == "Y"}
    assert granted == allowed, f"API client over-privileged: {granted - allowed}"


def test_every_capability_has_a_console_mapping_row(rbac):
    mapping_path = ROOT / "config" / "rbac-console-mapping.csv"
    with open(mapping_path, newline="", encoding="utf-8") as fh:
        mapping = {r["capability"]: r for r in csv.DictReader(fh)}
    assert set(mapping) == set(rbac), f"matrix and mapping differ: {set(mapping) ^ set(rbac)}"
    for cap, row in mapping.items():
        intended = {k for k, v in rbac[cap].items() if k != "capability" and v == "Y"}
        assert set(filter(None, row["intended_roles"].split(";"))) == intended, f"{cap}: intended roles drifted"
        assert row["verified"] in {"yes", "no"}
        if row["verified"] == "yes":
            for field in ("console_role_or_permission", "console_location", "verified_on", "verified_by"):
                assert row[field].strip(), f"{cap} marked verified but {field} is empty"


def test_rbac_docs_state_verification_status():
    assert "design intent" in read(DOCS / "05-rbac.md").lower()
    assert re.search(r"has \*{0,2}not\*{0,2} been verified", read(DOCS / "08-rbac-verification.md"))


# ---------------------------------------------------------------- containment policy
@pytest.fixture(scope="module")
def policy():
    return json.loads(read(ROOT / "config" / "containment-policy.json"))


def test_containment_requires_endpoint_correlation(policy):
    er = policy["entity_resolution"]
    assert er["required"] is True
    assert er["require_single_match"] is True
    assert er["on_no_match_or_ambiguous"].startswith("do_not_contain")
    assert len(er["methods_in_order"]) >= 2
    assert 0 < er["max_time_skew_seconds"] <= 600


def test_containment_requires_confidence_and_approval(policy):
    assert policy["confidence"]["min_independent_signals"] >= 2
    assert policy["confidence"]["min_severity"] in {"high", "critical"}
    assert policy["approval"]["required_by_default"] is True
    assert "do_not_contain" in policy["approval"]["on_timeout"]


def test_automatic_containment_is_off_and_strictly_bounded(policy):
    auto = policy["auto_containment"]
    assert auto["enabled"] is False
    cond = auto["allowed_only_when"]
    assert cond["min_severity"] == "critical"
    assert cond["min_independent_signals"] > policy["confidence"]["min_independent_signals"]
    assert cond["not_vip_user"] is True and cond["not_excluded"] is True


def test_critical_assets_are_never_contained(policy):
    never = set(policy["exclusions"]["never_contain_asset_tags"])
    assert {"domain-controller", "tier0-server"} <= never
    assert policy["blast_radius"]["max_containments_per_hour"] <= 5
    assert policy["audit"]["log_every_decision"] and policy["audit"]["include_non_actions"]
    assert policy["rollback"]["auto_lift"] is False


def test_policy_roles_exist_and_may_contain(policy, rbac):
    allowed = roles_with(rbac, "contain_host_rtr")
    assert policy["approval"]["approver_role"] in allowed
    assert policy["rollback"]["lift_containment_role"] in allowed


def test_adr_009_documents_every_guardrail():
    adr = read(DOCS / "07-decisions-adr.md")
    assert "## ADR-009" in adr
    section = adr.split("## ADR-009", 1)[1].lower()
    for phrase in ("endpoint identity correlation", "confidence threshold", "approval",
                   "exclusions", "blast-radius", "audit and rollback", "config/containment-policy.json"):
        assert phrase in section, f"ADR-009 does not mention {phrase!r}"
