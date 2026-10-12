# CrowdStrike Falcon Next-Gen SIEM lab

A hands-on, documented build of CrowdStrike Falcon Next-Gen SIEM (NG-SIEM), from architecture through user management, data onboarding, detection content and automation. Every module is designed around one fictional organisation, so the modules fit together and no real tenant data appears anywhere.

## The scenario: Northwind Labs

500 users, 300 endpoints, nine third-party log sources (Okta, Entra ID, Microsoft 365, AWS CloudTrail, FortiGate, Zscaler, Windows domain controllers, Linux servers), a small in-house SOC. Sources, repository names, tags, roles and retention are defined once in module 01 and reused by every later module.

## Modules

| # | Module | Covers | Status |
|---|---|---|---|
| 01 | [Architecture](01-architecture) | Data flow, sizing, retention and repository design, RBAC design, naming and tagging, ADRs | Complete |
| 02 | [User management](02-user-management) | SSO, personas and roles, joiner/mover/leaver, API clients, break-glass accounts, access reviews and a reconciliation tool | Complete |
| 03 | Data onboarding | HEC, data connectors, Falcon Log Collector, custom parsers, field validation | Planned |
| 04 | Collector fleet health | Collector deployment and versions, ingest health, silent-source alerting | Planned |
| 05 | Enrichment and threat intel | Lookup files, threat intel feeds, enrichment | Planned |
| 06 | Detections as code | CQL correlation rules, MITRE mapping, test data | Planned |
| 07 | Dashboards and searches | Saved, scheduled and dashboard content | Planned |
| 08 | Cost and retention optimisation | Ingest filtering, tiering, licence headroom | Planned |
| 09 | Fusion SOAR workflows | Phishing triage, host containment, ticketing, chat alerts | Planned |

## How a module is laid out

```text
NN-module-name/
├── README.md       goal, design, steps, outcomes
├── docs/           numbered documents and diagrams
├── config/         configuration, parsers, rules, workflows
├── sample-data/    synthetic logs and calculators
└── tests/          checks that run in CI
```

## Validation

Each module with a `tests/` folder is tested automatically on every push by `.github/workflows/validate.yml`, together with a Gitleaks secret scan, Markdown lint, an offline link check and a render check of every Mermaid diagram (each block is extracted to its own file first, so a failure names the diagram). To run one module locally:

```bash
pip install -r requirements-dev.txt
cd 01-architecture && pytest -q
```

## Conventions

- All data is synthetic. No tokens, customer IDs, tenant names, real IPs or hostnames, enforced by tests and `.gitignore`.
- Numbers in documents come from a workbook or config file and are checked against it by tests.
- Planning values (compression ratio, filter reduction, growth) are labelled ESTIMATE until replaced by measured telemetry. Permissions are labelled design intent until verified against the console.
- Anything that depends on licence, vendor limits or console behaviour is marked **VERIFY** until checked against current CrowdStrike documentation.
