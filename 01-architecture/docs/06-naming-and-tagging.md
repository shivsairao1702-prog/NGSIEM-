# 06 - Naming and tagging

## Two kinds of rules

- **Platform conventions** come from the vendor schema (ECS-based CPS tags and fields). Follow them exactly so out-of-the-box parsers, detections and dashboards work.
- **Project conventions** are Northwind Labs' own naming for objects it creates. They are a choice, not a vendor rule, and exist so the environment stays searchable and auditable.

## Platform conventions: tags

Fields that start with `#` are tags. Each unique combination of tag values forms a datasource, a separate group of data on disk. Tags are what a search uses to decide which data to read, so they must be low cardinality.

| Tag | Meaning | Example values | Required |
|---|---|---|---|
| `#Vendor` | Company that makes the product | fortinet, paloalto, microsoft, okta, cisco, zscaler, aws, cato | Yes |
| `#event.module` | The product from that vendor | fortigate, ngfw, entraid, sso, asa, zia, cloudtrail | Yes |
| `#event.dataset` | Specific log type within the product, written `module.dataset` | fortigate.traffic | When it applies |
| `#observer.type` | What kind of device produced the log | firewall, proxy, iam, edr, vpn, waf, sase, os, dlp | Yes |
| `#event.kind` | Type of record | event (normal log) or alert (security finding) | Yes |
| `#event.outcome` | Whether the action succeeded | success, failure, unknown | Only when an outcome makes sense |
| `#ecs.version` | ECS version the parser follows | for example 8.11.0 | Yes |
| `#Cps.version` | CPS version the parser follows | for example 1.0.0 | Yes |

The study notes list 46 allowed values for `#observer.type`. **VERIFY** the current list in the vendor documentation.

## Northwind Labs source tagging

| Product | `#Vendor` | `#event.module` | `#event.dataset` (where used) |
|---|---|---|---|
| FortiGate (traffic) | fortinet | fortigate | fortigate.traffic |
| FortiGate (UTM/event) | fortinet | fortigate | fortigate.utm |
| Zscaler Internet Access | zscaler | zia | zia.web |
| Microsoft Entra ID | microsoft | entraid | entraid.signin |
| Microsoft Windows | microsoft | windows | windows.security |
| Okta SSO | okta | sso | okta.system |
| AWS CloudTrail | aws | cloudtrail | cloudtrail.management |

The `#event.dataset` names for FortiGate UTM, Zscaler, Entra ID, Windows, Okta and CloudTrail are project examples that follow the `module.dataset` pattern. Check what the out-of-the-box parser actually sets and use that value.

## Platform conventions: common ECS fields

| Field | Holds |
|---|---|
| `source.ip` / `source.port` | Where the connection came from |
| `destination.ip` / `destination.port` | Where it went |
| `user.name` / `user.domain` | Who did it |
| `host.name` / `host.hostname` | Which machine |
| `network.transport` | tcp, udp |
| `url.original` / `url.domain` | Web activity |
| `process.name` / `process.command_line` | What ran |
| `file.hash.sha256` | File identity |
| `observer.hostname` | The device that logged it, such as the firewall name |

## Project conventions: object naming

| Object | Pattern | Examples |
|---|---|---|
| Repository | `repo-<domain>[-<qualifier>]` | `repo-identity`, `repo-net-traffic` |
| View | `view-<audience>` | `view-soc-all`, `view-audit` |
| Custom parser | `<vendor>-<product>-<dataset>-custom` | `fortinet-fortigate-utm-custom` |
| Lookup file | `lk_<purpose>.csv` | `lk_vip_users.csv`, `lk_known_scanners.csv` |
| Correlation rule | `NW-<TACTIC>-<NNN> <short title>` | `NW-CA-001 Impossible travel on SSO` |
| Fusion workflow | `FSOAR-<trigger>-<action>` | `FSOAR-identity-alert-contain-host` |
| Saved search / dashboard | `<team>-<topic>` | `soc-failed-logins-by-source` |
| HEC token / connector | `<source>-<env>` | `zia-prod` |
| API client | `apic-<integration>` | `apic-fusion-ticketing` |

Rule tactic codes in `NW-<TACTIC>-<NNN>` use short MITRE ATT&CK tactic abbreviations, for example CA (credential access), LM (lateral movement), EX (exfiltration), PE (privilege escalation).

## Rules for all names

1. Lowercase with hyphens for infrastructure objects; no spaces, no environment-specific secrets, no personal names.
2. Never put tokens, tenant identifiers or internal hostnames in any object name or description.
3. A name must say what the object is for, not who made it.
4. One naming change is one pull request, so renames are reviewed.

## Multiple environments

If a second tenant (for example a test tenant) is added, keep identical object names in both and distinguish by tenant, not by suffix. This keeps detections and dashboards portable between environments. Use the CI workflow at the repository root, extended in module 06, to promote content from test to production.
