# 06 - Audit and monitoring

An access review catches drift every 30 to 90 days. Monitoring catches the changes that matter within minutes. This document lists what to watch; the detection logic itself is built in module 06 (detections as code).

## Data sources

| Source | Where it lands | Notes |
|---|---|---|
| Falcon platform audit activity (user, role and API client changes, sign-ins) | First-party data | **VERIFY** which of these events are available in NG-SIEM for your tenant and how they are named |
| Okta system log (group membership, application assignment, MFA policy, admin actions) | `repo-identity` (module 01) | Planned as SRC-01; delivery evidence pending |
| Entra ID audit and sign-in logs | `repo-identity` | SRC-02 |
| Vault audit log (secret reads and rotations) | Not onboarded | Needed to detect API client secret misuse. Add as a source if the vault supports it |

No event names or CQL are given here because they have not been verified against a tenant. Module 06 turns each row below into a rule once the real field names are known.

## Events to monitor

| ID | Event | Why it matters | Source | Severity | Handling |
|---|---|---|---|---|---|
| M01 | Member added to or removed from any `grp-ngsiem-*` group in Okta | Group membership is access; this is the quietest privilege escalation path | Okta | High for privileged groups, medium otherwise | Match to an approved ticket within one business day |
| M02 | Falcon application assignment, SSO or MFA policy changed in Okta | Weakens the control everything else relies on | Okta | High | Page the on-call security lead |
| M03 | Break-glass account sign-in | By design always an incident | Falcon | Critical | Page on-call, follow the IdP outage runbook |
| M04 | User created, deleted or role changed in Falcon | Must have a matching request | Falcon | High for privileged roles | Match to a ticket, otherwise investigate |
| M05 | API client created, scopes changed or secret regenerated | Creates a credential that bypasses MFA | Falcon | High | Match to an approved request |
| M06 | API client used from an unexpected network location or at an unusual time | Credential theft or misuse | Falcon / vault | Medium | Verify with the owner persona |
| M07 | Repeated failed sign-ins or lockouts for a privileged user | Targeted attack on a privileged account | Okta / Falcon | Medium | Contact the user, review the IdP log |
| M08 | Sign-in by a user whose register row is `disabled` | Leaver process failure or stolen credentials | Okta / Falcon | Critical | Disable, investigate, review activity |
| M09 | Correlation rule, parser or retention changed by someone outside the persona that owns it | Defence evasion by weakening detection or deleting evidence | Falcon | High | Match to a reviewed change |
| M10 | Containment action executed | Containment is powerful and rare | Falcon | Informational, high if outside the approved workflow | Compare to the Fusion approval record (module 01, ADR-009) |

## Rules for these detections

- Falcon audit events depend on available first-party audit telemetry. Okta and Entra ID are third-party sources that require onboarding, consume ingest allowance and can experience delivery gaps. These rules depend on their availability; monitor source health.
- Each detection names an owner persona and a response action. A detection without both is not finished.
- Privileged identities and break-glass accounts are tagged in a lookup file (`lk_privileged_users.csv`, naming per module 01) so rules can raise severity by identity without hard-coding names.
- Alerts about the SOC's own access go to the security lead as well as the SOC queue, because an analyst should not be the only reviewer of an alert about their own account.

## Retention of audit evidence

Retention of first-party audit data follows the Falcon licence (module 01, `04-retention-and-repositories.md`). Okta and Entra logs sit in `repo-identity` at 365 days. Access review reports and tickets are kept for at least the audit period outside the SIEM, because the SIEM is not the system of record for approvals.

## Metrics

Tracked at each review, in the report header or alongside it:

| Metric | Healthy |
|---|---|
| Errors in the access review | 0 |
| Median time to disable a leaver | Under 4 hours |
| Access changes with no matching ticket (M01, M04, M05) | 0 |
| Days since the last break-glass test | Under 90 |
| API clients with unverified scopes | 0 once the console is checked |
