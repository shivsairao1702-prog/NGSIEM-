# 01 - User model

This document defines who and what can access NG-SIEM at Northwind Labs, in which account types, with which roles. Roles and permissions are defined in module 01 (`../../01-architecture/docs/05-rbac.md`); this module covers how people and systems come to hold them, and how that is kept correct over time.

## Account types

| Type | Count | Authenticates with | Rules |
|---|---|---|---|
| Named human | 12 | SSO through Okta, MFA enforced at the IdP | One person, one account. Never shared. |
| Break-glass | 2 | Local credentials sealed in the vault | Used only when SSO is unavailable. Every use is an incident. Tested every 90 days. |
| API client | 4 | Client ID and a secret held in the vault | Non-human. One per integration, minimal scopes, owned by a persona. |

There are no shared, generic or "temporary" accounts. Anything that is not a person is an API client.

## Personas

Values are taken from `../config/role-assignment-policy.json`. The module 01 role is the capability set from `../../01-architecture/config/rbac-matrix.csv`.

| Persona | Module 01 role | Planned | Max | Privileged | Approvers |
|---|---|---|---|---|---|
| `soc_l1` | `analyst_l1` | 4 | 8 | no | SOC manager |
| `soc_l2_ir` | `analyst_l2_ir` | 2 | 4 | yes | SOC manager, security lead |
| `detection_engineer` | `detection_engineer` | 2 | 4 | no | SOC manager |
| `platform_engineer` | `platform_engineer` | 2 | 3 | yes | security lead, CISO |
| `auditor` | `analyst_read_only` | 1 | 2 | no | compliance lead |
| `falcon_platform_owner` | `falcon_admin` | 1 | 2 | yes | CISO |
| `break_glass` | `falcon_admin` | 2 | 2 | yes | CISO |

"Planned" is the headcount in module 01. "Max" is the ceiling the review tool enforces; exceeding it is an error, differing from "Planned" is a warning.

## What makes a persona privileged

Privilege is **derived**, not asserted. A role is privileged if module 01 grants it any of: user and role management, API client management, repository and retention management, parser management, connector and HEC token management, log collector fleet management, or host containment. A test fails if the policy flags drift from the matrix.

Consequences: L2 responders count as privileged because they can contain hosts, even though they cannot change the platform. Detection engineers are not privileged because they cannot change ingestion, retention, users or containment.

## Principles

1. **Least privilege.** Start from the lowest role that does the job (module 01, `05-rbac.md`).
2. **No standing admin for daily work.** The Falcon platform owner holds no SOC role and uses administrator rights only for user, role and API client administration. SOC work is done by the analyst, engineer and responder personas.
3. **Separation of duties.** For privileged roles the requester, approver and implementer are three different people.
4. **Group membership is access.** Because roles follow IdP groups (ADR-002), the IdP groups `grp-ngsiem-*` are as sensitive as the roles themselves and are monitored accordingly (`06-audit-and-monitoring.md`).
5. **The register is intended state; the console is truth.** Each access review reconciles the two (`05-access-reviews.md`).

## Identifiers

| Object | Pattern | Example |
|---|---|---|
| Named user | `nw-<persona>-<nn>` | `nw-soc-l1-01` |
| Break-glass | `nw-bg-<nn>` | `nw-bg-01` |
| IdP group | `grp-ngsiem-<persona>` | `grp-ngsiem-soc-l1` |
| API client | `apic-<integration>` | `apic-fusion-containment` |

All identifiers are synthetic. They contain no personal names, so the registers can be published safely.

## Out of scope

Multi-tenant and parent/child CID management, customer-facing access and managed-service-provider access are not modelled. They would add a tenant dimension to every register and are better added as a separate module.
