# 05 - Access reviews

## Cadence

| Population | Cadence | Reason |
|---|---|---|
| Standard personas | Every 90 days | Catches role creep and leavers within a quarter |
| Privileged personas and break-glass | Every 30 days | Small group, high impact |
| API clients | At every review, plus rotation every 90 days | Non-human access has no manager to notice it |
| Break-glass test | Every 90 days | A break-glass account that has not been tested is not a control |

## Procedure

1. **Export** the console's user list with their roles into a CSV with two columns: `user_id` and `console_roles` (semicolon separated). The exact export format is a **VERIFY** item; a manual copy into the CSV is acceptable.
2. **Run** the review:

   ```bash
   python3 scripts/access_review.py --console console-export.csv --as-of 2026-10-12
   ```

3. **Triage** every finding with the table below. Errors must be fixed or formally accepted; warnings are reviewed.
4. **Re-run** until no errors remain. Use `--strict` in CI if warnings should also fail.
5. **Sign off.** The reviewer records the report, the date and the decisions. Update `last_access_review` for each user reviewed in the register, in a pull request.
6. **Keep the evidence.** Report, console export (sanitised in public repositories) and the register commit.

The tool exits 1 on any error, so it can gate a scheduled job.

## Findings and what to do

| Code | Severity | Meaning | Action |
|---|---|---|---|
| U01 | error | Persona not in the policy | Fix the register or add the persona through a reviewed policy change |
| U02 | error | Role does not match the persona | Correct the role, or change persona through the mover process |
| U03 | error | Named user without an SSO group | Move the user to SSO. Local accounts are for break-glass only |
| U04 | error | Active after end date | Disable now, then find out why the leaver process missed it |
| U05 | error | Review overdue | Review the user, update `last_access_review` |
| U06 | error | More holders than the persona allows | Remove holders, or raise the maximum with CISO approval and an ADR |
| U07 | warning | Holders differ from planned headcount | Confirm the change is intended and update the plan |
| U08 | error | Break-glass test overdue | Test, then rotate the password |
| C01 | error | Console account unknown to the register | Treat as a possible unauthorised account: investigate before disabling |
| C02 | warning | Register user missing from the console | Update the register, or find out why access was removed |
| C03 | error | Console roles differ from policy | Remove the extra role, or correct the policy through review |
| C04 | error | Disabled in the register, present in the console | Disable in the console and review what the account did since leaving |
| A01 | error | API client has no valid owner | Assign an owner or revoke the client |
| A02 | error | Scopes beyond the allowlist | Remove the extra scopes |
| A03 | error | Rotation overdue | Rotate now |
| A04 | warning | Scopes not verified | Compare with the console, then set `scopes_verified` to `yes` |
| A05 | error | Integration not in the allowlist | Add it through a reviewed change, or revoke the client |

Every code above is exercised by a deliberately flawed dataset in `../sample-data/`, and a test fails if a check stops detecting its case. `../sample-data/review-report-example.md` is the real output of that dataset.

## Separation of duties checks

Run these alongside the tool at each review; the tool covers the first two.

| Check | Where |
|---|---|
| Nobody holds a role that does not match their persona | Tool, `U02` |
| Holder counts are within limits | Tool, `U06` |
| The person who approved a privileged grant is not the person who implemented it | Ticket history |
| Nobody on the detection engineering team holds ingestion or retention rights | Module 01 matrix, test |
| Falcon Administrator is held only by the platform owner and break-glass accounts | Tool, `U02`, and module 01 test |
| API clients that can contain hosts or change rules are owned by the right persona | Register review |

## What the tool cannot see

- Whether the register itself is honest. Only the console export reveals unregistered or mis-roled accounts, which is why the console comparison is part of every review.
- Activity. A correctly roled account can still be misused; that is the job of the monitoring in `06-audit-and-monitoring.md`.
- Permissions inside a role. The console role name is compared, not its contents; role contents are verified under module 01 (`08-rbac-verification.md`).
