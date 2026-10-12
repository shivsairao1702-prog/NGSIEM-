# 04 - API clients

Everything that is not a person authenticates as an API client. Clients are listed in `../config/api-client-register.csv` and checked against `../config/role-assignment-policy.json`.

## Inventory

| Client | Purpose | Owner persona | Intended scopes |
|---|---|---|---|
| `apic-fusion-containment` | Fusion workflow host containment after approval (module 01, ADR-009) | `platform_engineer` | `hosts:read`, `hosts:write` |
| `apic-fusion-ticketing` | Fusion workflow ticket creation from alerts | `platform_engineer` | `alerts:read` |
| `apic-ci-rule-deploy` | CI deployment of reviewed correlation rules | `detection_engineer` | `correlation-rules:write` |
| `apic-falconpy-inventory` | Scheduled host inventory export | `platform_engineer` | `hosts:read` |

**Scope names are placeholders.** They describe the intent. The exact names in the console differ and must be recorded after verification; until then every client carries review warning `A04`, which is deliberate.

## Rules

| # | Rule | Enforced by |
|---|---|---|
| 1 | One client per integration, named `apic-<integration>` | Test and review tool |
| 2 | Scopes are a subset of the allowlist for that integration | Review error `A02` |
| 3 | Every client has an owner persona that exists in the policy | Review error `A01` |
| 4 | An integration not in the allowlist cannot have a client until the allowlist is changed by pull request | Review error `A05` |
| 5 | The secret is stored in the vault. The register holds a reference (`vault://...`), never a value | Test and Gitleaks |
| 6 | The secret is rotated at least every 90 days | Review error `A03` |
| 7 | Scopes are verified against the console and the register is updated | Review warning `A04` |
| 8 | No client is created for a person's convenience: a script a person runs uses that person's access | Process |

## Lifecycle

| Stage | Steps |
|---|---|
| Request | The owner names the integration, the exact actions it needs and the system that will hold the secret. A platform engineer proposes the minimal scope list. |
| Approve | Security lead approves. For clients that can contain hosts or change rules (`apic-fusion-containment`, `apic-ci-rule-deploy`) the CISO is also an approver. |
| Create | A platform engineer creates the client with only the approved scopes, stores the secret in the vault, and adds the register row and the allowlist entry in one pull request. |
| Verify | Compare the console scopes with the register and set `scopes_verified` to `yes`. |
| Rotate | Every 90 days, or immediately on suspected exposure. |
| Retire | Revoke in the console, delete the vault entry, set the register status to `retired`. A retired client is excluded from checks. |

## Rotation

1. Create the new secret (if the console supports two active secrets at once; **VERIFY**).
2. Store it in the vault under the existing reference.
3. Restart or redeploy every consumer so it reads the new value.
4. Confirm the consumer works, then revoke the old secret.
5. Update `last_rotated` in the register.

If two secrets cannot be active at once, schedule rotation in a maintenance window and expect a short gap.

## If a secret is exposed

1. Revoke the client's secret immediately. Do not wait to confirm misuse.
2. Rotate and redeploy.
3. Search the audit log for use of the client between the exposure and the revocation, and for any client or role created in that window.
4. Record an incident. If the secret reached a Git repository, remove it from history as well as from the file: deleting a line is not enough.
5. Add or tighten the control that failed (Gitleaks rule, pre-commit hook, review of the workflow definition).

This repository uses Gitleaks in CI and an optional pre-commit hook to catch this class of mistake before it is pushed.

## Why one client per integration

A shared client turns every integration into the weakest one: a leak in the ticketing bot would expose containment. Separate clients mean separate scopes, separate rotation, and an audit trail that says which integration did what. The cost is a few more rows in the register, which the review tool handles.
