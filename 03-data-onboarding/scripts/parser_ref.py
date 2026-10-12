#!/usr/bin/env python3
"""Reference model of config/parsers/cribl-datagen-syslog.cql.

The CQL parser only runs inside NG-SIEM, so CI cannot execute it. This model reads the
same file, takes the regex and static metadata from it (not from a copy), and applies the
rest of the logic in Python so that every behaviour in sample-data/datagen-syslog-cases.json
is checked on each push.

What it proves: the regex, the envelope handling, the branch order, the field names and
the absent-versus-empty rules. What it cannot prove: how LogScale itself behaves. Anything
that depends on that is listed in the parser's .meta.json under verify_in_tenant and in
docs/03-parser-walkthrough.md.

Usage:
    python3 scripts/parser_ref.py '<13>Oct 12 20:18:00 web01 sshd[1234]: ok'
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MODULE = Path(__file__).resolve().parent.parent
PARSER = MODULE / "config" / "parsers" / "cribl-datagen-syslog.cql"

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}
# MMM [ ]d HH:mm:ss : month, one space, an optional second space, day, time.
SYSLOG_TS = re.compile(r"^([A-Za-z]{3}) ( ?)(\d{1,2}) (\d{2}):(\d{2}):(\d{2})$")
EPOCH = re.compile(r"^\d{10}(\.\d+)?$")


def parser_text(path: Path = PARSER) -> str:
    return path.read_text(encoding="utf-8")


def extract_regex(text: str) -> str:
    """The regex argument of the regex() call, as a Python pattern."""
    m = re.search(r'regex\(regex="(.*?)",\s*field="_temp_line"', text, re.S)
    if not m:
        raise ValueError("regex(...) call on _temp_line not found in the parser")
    pattern = m.group(1).replace("\\\\", "\\")  # CQL string escaping -> regex
    return re.sub(r"\(\?<([A-Za-z_.]+)>",
                  lambda g: "(?P<" + g.group(1).replace(".", "_") + ">", pattern)


def static_metadata(text: str) -> dict:
    """Assignments in the STATIC METADATA section, e.g. Vendor := "Cribl"."""
    start = text.index("// STATIC METADATA")
    end = text.index("// PREPARSE")
    return dict(re.findall(r'^\|\s*([\w.]+)\s*:=\s*"([^"]*)"', text[start:end], re.M))


def parse_syslog_timestamp(value: str, assumed_year: int):
    """MMM [ ]d HH:mm:ss, UTC. RFC3164 has no year, so one is assumed (VERIFY what LogScale assumes)."""
    m = SYSLOG_TS.match(value)
    if not m or m.group(1) not in MONTHS:
        return None
    try:
        return datetime(assumed_year, MONTHS[m.group(1)], int(m.group(3)),
                        int(m.group(4)), int(m.group(5)), int(m.group(6)), tzinfo=timezone.utc)
    except ValueError:
        return None


def iso(dt: datetime) -> str:
    base = dt.strftime("%Y-%m-%dT%H:%M:%S")
    if dt.microsecond:
        base += ".%03d" % (dt.microsecond // 1000)
    return base + "Z"


def _flatten(obj, prefix):
    """parseJson(prefix=..., excludeEmpty=true, handleNull=discard)."""
    out = {}
    for key, val in obj.items():
        name = prefix + key
        if isinstance(val, dict):
            out.update(_flatten(val, name + "."))
        elif val is None or val == "":
            continue
        else:
            out[name] = str(val)
    return out


def parse_event(raw: str, ingest_time: datetime, path: Path = PARSER) -> dict:
    text = parser_text(path)
    rx = re.compile(extract_regex(text))
    ev = dict(static_metadata(text))

    # PREPARSE
    temp = None
    if re.search(r"^\s*\{", raw):
        try:
            obj = json.loads(raw)
        except ValueError:
            obj = None
        if isinstance(obj, dict):
            ev.update(_flatten(obj, "Vendor.envelope."))
            temp = ev.get("Vendor.envelope.event") or ev.get("Vendor.envelope._raw")
    else:
        temp = raw
    if temp is None:
        temp = raw
    ev["event.original"] = temp

    m = rx.search(temp)
    if m:
        for group, value in m.groupdict().items():
            if value is not None:
                ev[group.replace("_", ".", 1)] = value
    if "Vendor.app" not in ev:
        ev["error.message"] = "syslog regex did not match"

    # TIMESTAMP: envelope epoch first, then the syslog time
    if EPOCH.match(ev.get("Vendor.envelope.time", "")):
        ev["@timestamp"] = iso(datetime.fromtimestamp(float(ev["Vendor.envelope.time"]), timezone.utc))
    elif "Vendor.timestamp" in ev:
        parsed = parse_syslog_timestamp(ev["Vendor.timestamp"], ingest_time.year)
        if parsed:
            ev["@timestamp"] = iso(parsed)
        else:
            ev["@error"] = True
            ev["@error_msg"] = "parseTimestamp failed"

    # NORMALIZATION
    ev["event.kind"] = "event"
    ev["event.category[]"] = ["host"]
    ev["event.type[]"] = ["info"]

    # FIELD MAPPING
    if "Vendor.message" in ev:
        ev["message"] = ev["Vendor.message"]
    if "Vendor.host" in ev:
        ev["host.name"] = ev["host.hostname"] = ev["Vendor.host"].lower()
    if "Vendor.app" in ev:
        ev["process.name"] = ev["service.name"] = ev["Vendor.app"]
    if re.fullmatch(r"\d+", ev.get("Vendor.pid", "")):
        ev["process.pid"] = int(ev["Vendor.pid"])
    if re.fullmatch(r"\d+", ev.get("Vendor.priority", "")):
        pri = int(ev["Vendor.priority"])
        ev["log.syslog.priority"] = pri
        ev["log.syslog.facility.code"] = pri // 8
        ev["log.syslog.severity.code"] = pri - (pri // 8) * 8
        ev["event.severity"] = ev["log.syslog.severity.code"]

    # CLEANUP
    for name in ("Vendor.envelope.event", "Vendor.envelope._raw"):
        ev.pop(name, None)
    return ev


def year_rollover_skew_days(syslog_ts: str, ingest_time: datetime) -> int:
    """Days between the parsed time and ingest when the year is assumed to be the ingest year."""
    parsed = parse_syslog_timestamp(syslog_ts, ingest_time.year)
    return round((parsed - ingest_time).total_seconds() / 86400)


if __name__ == "__main__":
    line = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read().rstrip("\n")
    print(json.dumps(parse_event(line, datetime.now(timezone.utc)), indent=2, sort_keys=True))
