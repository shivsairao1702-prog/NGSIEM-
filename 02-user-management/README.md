# 02 - User management

Part of the [NG-SIEM lab](../README.md). How people and systems get access to NG-SIEM at Northwind Labs, and how that access is kept correct: SSO, personas and roles, joiner/mover/leaver, API clients, break-glass accounts, access reviews and monitoring of changes to access.

It builds on module 01: personas, roles and headcounts come from [`01-architecture`](../01-architecture), and tests fail if the two drift apart. All identities are synthetic.

## Goal

Make access to the SIEM provable. For every account, human or not, the design says why it exists, which role it holds, who approved it, when it was last reviewed, and what happens when that review is missed. A tool checks the registers against the policy and the console and reports every difference.

## Design at a glance

| Item | Design |
|---|---|
| Accounts | 12 named users, 2 break-glass accounts, 4 API clients |
| Sign-in | SAML SSO with Okta, MFA at the IdP, phishing-resistant MFA for privileged users |
| Local accounts | Break-glass only, sealed in the vault, tested every 90 days |
| Access control | IdP group `grp-ngsiem-<persona>` decides who can sign in; a platform engineer assigns the console role from an approved ticket |
| Privileged | Derived from module 01 capabilities, reviewed every 30 days (others every 90) |
| Leavers | Disabled within 4 hours of the HR notice |
| API clients | One per integration, scope allowlist, owner persona, 90-day rotation, secret held in the vault |
| Review | `scripts/access_review.py` compares registers, policy and console export: 17 finding codes |

## Contents

| Path | What it covers |
|---|---|
| [`docs/01-user-model.md`](docs/01-user-model.md) | Account types, personas, what makes a role privileged |
| [`docs/02-authentication-and-sso.md`](docs/02-authentication-and-sso.md) | SSO design, requirements, break-glass accounts, IdP outage runbook |
| [`docs/03-joiner-mover-leaver.md`](docs/03-joiner-mover-leaver.md) | Joiner, mover, leaver and emergency access processes |
| [`docs/04-api-clients.md`](docs/04-api-clients.md) | API client inventory, rules, lifecycle, rotation, exposure response |
| [`docs/05-access-reviews.md`](docs/05-access-reviews.md) | Cadence, procedure, what each finding means and what to do |
| [`docs/06-audit-and-monitoring.md`](docs/06-audit-and-monitoring.md) | Ten access-related events to detect and why |
| [`docs/07-decisions-adr.md`](docs/07-decisions-adr.md) | Eight architecture decision records |
| [`config/role-assignment-policy.json`](config/role-assignment-policy.json) | Personas, limits, review cadence, API scope allowlist |
| [`config/user-register.csv`](config/user-register.csv) | Intended state of every human account |
| [`config/api-client-register.csv`](config/api-client-register.csv) | Intended state of every API client |
| [`scripts/access_review.py`](scripts/access_review.py) | The review tool (standard library only) |
| [`sample-data/`](sample-data) | Console exports and deliberately flawed registers, with the expected findings |

## Run the review

```bash
# shipped registers, reconciled with a clean console export
python3 scripts/access_review.py --as-of 2026-10-12 --console sample-data/console-export-clean.csv

# deliberately flawed data: every finding code fires
python3 scripts/access_review.py --as-of 2026-10-12 \
  --users sample-data/user-register-with-issues.csv \
  --clients sample-data/api-client-register-with-issues.csv \
  --console sample-data/console-export-with-issues.csv
```

The first run reports 0 errors and 4 warnings (the API client scopes are not yet verified against a console). The second reports 15 errors and 11 warnings; the full output is in [`sample-data/review-report-example.md`](sample-data/review-report-example.md).

## Validation

`tests/test_access_review.py` checks three things:

1. The tool finds exactly the errors planted in the sample data, every finding code is exercised, and the command-line exit codes are right.
2. The shipped registers and policy are clean: no shared accounts, SSO for every named user, break-glass limits agree, one API client per integration, secrets held as vault references only.
3. This module agrees with module 01: every persona maps to a role in the module 01 matrix, the privileged flags match the capabilities there, containment is held only by L2, the owner and break-glass accounts, and headcounts match the module 01 persona table.

```bash
pip install -r ../requirements-dev.txt
pytest -q
```

## Verify before relying on this design

- [ ] SSO enforcement, and whether local sign-in remains possible for break-glass accounts when it is enforced
- [ ] Whether roles can be assigned from IdP attributes (ADR-002 assumes not)
- [ ] Exact console role names behind each persona, and the response role used for containment (placeholders in the policy)
- [ ] Exact API scope names and the minimal set each integration needs (placeholders in the policy; every client carries warning `A04` until verified)
- [ ] Which audit events NG-SIEM exposes for user, role and API client changes, and their names
- [ ] Format of the console user export used in access reviews
- [ ] Whether two API client secrets can be active at once for rotation without downtime
