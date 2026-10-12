"""Checks for module 03: the Datagen syslog parser, its metadata and its agreement with module 01.

The CQL runs only inside NG-SIEM. scripts/parser_ref.py reads the real .cql file and models
its logic, so these tests fail if the file, the sample cases or the documented behaviour drift.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parent.parent
REPO = MODULE.parent
sys.path.insert(0, str(MODULE / "scripts"))
import parser_ref as ref  # noqa: E402

CQL = ref.parser_text()
META = json.loads((MODULE / "config/parsers/cribl-datagen-syslog.meta.json").read_text())
CASES = json.loads((MODULE / "sample-data/datagen-syslog-cases.json").read_text())["cases"]

# The regex validated in the lab tenant (parser 1.0.0), exactly as it appears in the CQL string.
VALIDATED_CQL_REGEX = (
    r"^(?:\\<(?<Vendor.priority>\\d+)\\>)?(?<Vendor.timestamp>[A-Za-z]{3}\\s+\\d{1,2}\\s+\\d{2}:\\d{2}:\\d{2})"
    r"\\s+(?<Vendor.host>\\S+)\\s+(?<Vendor.app>[^\\s\\[:]+)(?:\\[(?<Vendor.pid>[^\\]]+)\\])?:?\\s*"
    r"(?<Vendor.message>.*)"
)


def ingest(case):
    return datetime.fromisoformat(case["ingest_time"].replace("Z", "+00:00"))


def raw_of(case):
    return case["raw"] if "raw" in case else json.dumps(case["envelope"])


def run(case):
    return ref.parse_event(raw_of(case), ingest(case))


@pytest.mark.parametrize("case", CASES)
def test_case_expectations(case):
    ev = run(case)
    raw = raw_of(case)
    for field, want in case["expect"].items():
        want = raw if want == "$RAW" else want
        assert ev.get(field) == want, f"{case['id']}: {field} = {ev.get(field)!r}, expected {want!r}"


@pytest.mark.parametrize("case", CASES)
def test_case_absent_fields(case):
    ev = run(case)
    for field in case.get("absent", []):
        assert field not in ev, f"{case['id']}: {field} should be absent, got {ev[field]!r}"


def test_case_ids_unique():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))


def test_cases_cover_every_mapped_field():
    """Every field the FIELD MAPPING section produces is asserted by at least one case."""
    start, end = CQL.index("// FIELD MAPPING"), CQL.index("// CLEANUP")
    block = CQL[start:end]
    produced = set(re.findall(r"\|\s*([a-z][\w.]*)\s*:=", block)) | set(re.findall(r'as="([a-z][\w.]*)"', block))
    produced = {p for p in produced if not p.startswith("_temp")}
    asserted = set()
    for c in CASES:
        asserted |= set(c["expect"])
    missing = produced - asserted
    assert not missing, f"mapped but never asserted: {sorted(missing)}"
    assert {"host.name", "process.pid", "log.syslog.severity.code", "message"} <= produced


def test_regex_is_the_validated_one():
    m = re.search(r'regex\(regex="(.*?)",\s*field="_temp_line"', CQL, re.S)
    assert m and m.group(1) == VALIDATED_CQL_REGEX, "the regex changed; re-validate in a tenant and update this pin and docs/03"


def test_regex_is_anchored_and_non_strict():
    assert 'field="_temp_line", strict="false"' in CQL
    assert not re.search(r"^\s*\|\s*@rawstring\s*=\s*/", CQL, re.M), "bare filter form drops non-matching records"


def test_timestamp_format_accepts_padded_days():
    assert 'format="MMM [ ]d HH:mm:ss"' in CQL
    assert not re.search(r'format="MMM d HH', CQL)
    naive = re.compile(r"^[A-Za-z]{3} \d{1,2} \d{2}:\d{2}:\d{2}$")
    assert not naive.match("Sep  9 03:04:05"), "a plain d would reject padded days"
    assert ref.SYSLOG_TS.match("Sep  9 03:04:05") and ref.SYSLOG_TS.match("Sep 9 03:04:05")
    assert not ref.SYSLOG_TS.match("Sep   9 03:04:05"), "three spaces are not valid RFC3164 padding"


def test_template_placeholder_removed():
    assert "REQUIRED_INPUT" not in re.sub(r"//.*", "", CQL), "template line must not remain as code"


def test_sections_in_order():
    names = ["STATIC METADATA", "PREPARSE", "TIMESTAMP", "NORMALIZATION", "FIELD MAPPING", "CLEANUP"]
    positions = [CQL.index("// " + n) for n in names]
    assert positions == sorted(positions)


def test_envelope_fields_do_not_collide_with_vendor_fields():
    assert 'prefix="Vendor.envelope."' in CQL
    assert 'prefix="Vendor."' not in CQL


def test_temp_fields_and_envelope_copies_are_dropped():
    assigned = set(re.findall(r"\|?\s*(_temp_\w+)\s*:=", CQL)) | set(re.findall(r'as="(_temp_\w+)"', CQL))
    drop = re.search(r"drop\(\[(.*?)\]\)", CQL).group(1)
    dropped = {d.strip() for d in drop.split(",")}
    assert assigned <= dropped, f"temporary fields left on events: {sorted(assigned - dropped)}"
    assert {"Vendor.envelope.event", "Vendor.envelope._raw"} <= dropped


def test_event_original_is_set_after_unwrapping():
    assert CQL.index("event.original := _temp_line") > CQL.index("coalesce([Vendor.envelope.event")
    assert "event.original := @rawstring" not in CQL


# ---- metadata and agreement with module 01 -------------------------------------------------

def module01_tags():
    doc = (REPO / "01-architecture/docs/06-naming-and-tagging.md").read_text()
    return set(re.findall(r"^\|\s*`#([A-Za-z.]+)`", doc, re.M))


def test_static_metadata_complete():
    md = ref.static_metadata(CQL)
    for key in ("Vendor", "Parser.version", "ecs.version", "Cps.version", "event.module", "event.dataset", "observer.type"):
        assert md.get(key), f"{key} missing from STATIC METADATA"
    for key in ("Parser.version", "ecs.version", "Cps.version"):
        assert re.fullmatch(r"\d+\.\d+\.\d+", md[key]), key
    assert md["event.dataset"].startswith(md["event.module"] + "."), "module 01 naming: event.dataset is module.dataset"


def test_meta_matches_parser():
    md = ref.static_metadata(CQL)
    assert META["parser_version"] == md["Parser.version"]
    for field in META["tag_fields"]:
        assert field in md or re.search(r"\|\s*" + re.escape(field) + r"\s*:=", CQL), f"tag field {field} never set"


def test_tag_fields_are_module01_tags():
    allowed = module01_tags()
    assert {"Vendor", "event.module", "event.dataset", "observer.type"} <= allowed
    assert set(META["tag_fields"]) <= allowed, sorted(set(META["tag_fields"]) - allowed)
    for high_cardinality in ("host.name", "host.hostname", "process.name", "process.pid", "message", "Vendor.host"):
        assert high_cardinality not in META["tag_fields"]


def test_test_parser_is_barred_from_production_repositories():
    assert META["production_repositories_allowed"] is False
    policy = (REPO / "01-architecture/config/containment-policy.json")
    assert policy.exists()


def test_verify_list_covers_unverified_constructs():
    joined = " ".join(META["verify_in_tenant"]).lower()
    for needle in ("fractional", "year", "floor", "vendor", "observer.type"):
        assert needle in joined, f"{needle} is unverified in the parser but missing from verify_in_tenant"


# ---- behaviours that need their own assertion ----------------------------------------------

def test_year_rollover_hazard_is_real():
    skew = ref.year_rollover_skew_days("Dec 31 23:59:59", datetime(2027, 1, 1, 0, 0, 10, tzinfo=timezone.utc))
    assert skew >= 360, "a December line ingested in January lands almost a year in the future if the ingest year is assumed"
    assert abs(ref.year_rollover_skew_days("Oct 12 20:18:00", datetime(2026, 10, 12, 20, 18, 5, tzinfo=timezone.utc))) == 0


def test_malformed_json_is_flagged_not_dropped():
    raw = '{"time": 1791836280, "event": '
    ev = ref.parse_event(raw, datetime(2026, 10, 12, tzinfo=timezone.utc))
    assert ev["error.message"] == "syslog regex did not match"
    assert ev["event.original"] == raw
    assert "host.name" not in ev


def test_unwrapped_and_wrapped_give_same_fields():
    line = "<13>Oct 12 20:18:00 web01 sshd[1234]: ok"
    t = datetime(2026, 10, 12, 20, 18, 5, tzinfo=timezone.utc)
    bare = ref.parse_event(line, t)
    wrapped = ref.parse_event(json.dumps({"time": 1791836280, "host": "cribl-worker-01", "event": line}), t)
    for field in ("host.name", "process.name", "process.pid", "message", "@timestamp", "event.original",
                  "log.syslog.facility.code", "event.dataset"):
        assert bare[field] == wrapped[field], field


def test_every_event_carries_the_tag_fields():
    for case in CASES:
        ev = run(case)
        for field in ("Vendor", "event.module", "event.dataset", "observer.type", "event.kind", "ecs.version", "Cps.version"):
            assert field in ev, f"{case['id']} lacks {field}"
