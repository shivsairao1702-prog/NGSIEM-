/*
Cribl Datagen Syslog - TEST parser (mock ingest pipeline validation)
Parser.version 1.1.1 (1.0.0 was the version validated in the lab tenant)

Minimal parser: proves data flows and fields extract. Not production-hardened.
Source: Cribl Datagen `syslog.log` -> Cribl Stream -> Falcon Cribl data connector
Input formats handled: bare RFC3164 line, or the Cribl envelope {"time":..,"host":..,"event":"<raw syslog>"}.
NOT handled: RFC5424, ISO timestamps, tags such as pam_unix(sshd:auth). See docs/03-parser-walkthrough.md.

Changes from 1.0.0
  - event.dataset added (module 01 requires #event.dataset as module.dataset)
  - envelope fields parsed under Vendor.envelope. so they cannot overwrite or leak into host.name
  - event.original now holds the syslog line, not the envelope
  - envelope event/_raw dropped after use (they duplicated @rawstring)
  - events the syslog regex does not match are flagged with error.message
  - syslog priority decoded into facility and severity (UNVERIFIED in a tenant, see marker below)
*/

// ============================================================================
// STATIC METADATA
// ============================================================================
| Vendor := "Cribl"            // VERIFY against https://developer.crowdstrike.com/docs/ng-siem/vendors
| Parser.version := "1.1.1"
| ecs.version := "8.17.0"
| Cps.version := "1.0.0" // Legacy baseline; full compliance remains unverified
| event.module := "syslog"
| event.dataset := "syslog.generic"
| observer.type := "forwarder"  // VERIFY against the allowed #observer.type list

// ============================================================================
// PREPARSE
// ============================================================================
// Cribl's CrowdStrike Falcon Next-Gen SIEM destination wraps each event as {"time":..,"host":..,"event":"<raw syslog>"}.
// The Falcon connector may or may not unwrap it first. Handle both: if it arrives wrapped
// and you only run the syslog regex, nothing extracts while ingestion still looks healthy.
| case {
    @rawstring = /^\s*\{/
        | parseJson(prefix="Vendor.envelope.", excludeEmpty="true", handleNull="discard")
        | _temp_line := coalesce([Vendor.envelope.event, Vendor.envelope._raw]);
    * | _temp_line := @rawstring;
}

// Wrapped but carrying neither event nor _raw: fall back to the whole record so nothing is lost.
| case {
    _temp_line != *
        | _temp_line := @rawstring;
    * | *;
}

| event.original := _temp_line

// RFC3164: <13>Apr 23 14:30:45 hostname app[1234]: message
// strict="false" so a non-matching line is passed through instead of silently discarded;
// the bare `| @rawstring = /.../` form in the template is a filter and drops the record.
| regex(regex="^(?:\\<(?<Vendor.priority>\\d+)\\>)?(?<Vendor.timestamp>[A-Za-z]{3}\\s+\\d{1,2}\\s+\\d{2}:\\d{2}:\\d{2})\\s+(?<Vendor.host>\\S+)\\s+(?<Vendor.app>[^\\s\\[:]+)(?:\\[(?<Vendor.pid>[^\\]]+)\\])?:?\\s*(?<Vendor.message>.*)", field="_temp_line", strict="false")

// Flag lines the regex did not match. Without this they ingest "healthy" with no fields.
| case {
    Vendor.app != *
        | error.message := "syslog regex did not match";
    * | *;
}

// ============================================================================
// TIMESTAMP
// ============================================================================
// The template's `Vendor.timestamp := Vendor.REQUIRED_INPUT` line is DELETED - the regex
// above already populates Vendor.timestamp via its named capture.
| case {
    // Cribl envelope epoch (seconds, often fractional). Only present if wrapped. No timezone
    // argument: epoch is absolute. VERIFY fractional values parse with format="seconds".
    Vendor.envelope.time = /^\d{10}(\.\d+)?$/
        | parseTimestamp(field="Vendor.envelope.time", format="seconds");

    // `MMM [ ]d` not `MMM d`: RFC3164 space-pads single-digit days ("Sep  9"), and a plain
    // `d` silently fails to parse every 1st-9th of the month.
    // RFC3164 carries no year and no timezone: UTC is an ASSUMPTION about the sender.
    Vendor.timestamp = *
        | parseTimestamp(field="Vendor.timestamp", format="MMM [ ]d HH:mm:ss", timezone="UTC");

    * | *;
}

// ============================================================================
// NORMALIZATION
// ============================================================================
// Generic values for a test source; real sources set these from the event content.
| event.kind := "event"
| array:append(array="event.category[]", values=["host"])
| array:append(array="event.type[]", values=["info"])

// ============================================================================
// FIELD MAPPING
// ============================================================================
| case { Vendor.message = * | message := Vendor.message; * | *; }
| case { Vendor.host = * | host.name := lower(Vendor.host) | host.hostname := lower(Vendor.host); * | *; }
| case { Vendor.app = * | process.name := Vendor.app | service.name := Vendor.app; * | *; }
// process.pid is integer-typed - parse, don't assign.
| case { Vendor.pid = /^\d+$/ | parseInt(field="Vendor.pid", as="process.pid", radix=10); * | *; }

// UNVERIFIED in a tenant: priority = facility * 8 + severity. Remove this block if it errors.
| case {
    Vendor.priority = /^\d+$/
        | parseInt(field="Vendor.priority", as="_temp_pri", radix=10)
        | _temp_ratio := _temp_pri / 8
        | math:floor(field="_temp_ratio", as="_temp_fac")
        | log.syslog.priority := _temp_pri
        | log.syslog.facility.code := _temp_fac
        | log.syslog.severity.code := _temp_pri - (_temp_fac * 8)
        | event.severity := log.syslog.severity.code;
    * | *;
}

// ============================================================================
// CLEANUP
// ============================================================================
| drop([_temp_line, _temp_pri, _temp_ratio, _temp_fac, Vendor.envelope.event, Vendor.envelope._raw])

/*
VALIDATE (SOP Step 4) - Advanced Event Search, Past 15 Minutes:

    #dataConnectionID = "<YOUR_DATA_CONNECTION_ID>"
    | table([@timestamp, @ingesttimestamp, host.hostname, process.name, process.pid, message])

Pass = events appear, those columns are populated, no @error:true.

If host.hostname / process.name are EMPTY but events arrive, the envelope branch is the
thing to check - inspect @rawstring in one event to see whether it starts with `{`.
Events flagged error.message = "syslog regex did not match" are lines the regex rejected.
*/
