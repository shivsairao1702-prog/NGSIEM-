# 08 - RBAC verification

## Status

`../config/rbac-matrix.csv` records **design intent**: what Northwind Labs wants each persona to be able to do. It has **not** been verified against the actual capabilities of CrowdStrike roles. Public documentation does not list per-role permissions (it is behind the console login), so the mapping has to be completed from a real tenant.

`../config/rbac-console-mapping.csv` is the worksheet for that. Every capability starts as `verified = no`. A capability is only marked `yes` once the exact console role or permission name, its location in the console, the date and the verifier are recorded.

## Verification procedure

1. In the console, open the user and role management area and list the built-in roles available in your tenant.
2. For each row in the mapping worksheet, find the console role or permission that grants the capability and record its exact name and location.
3. Test with a throwaway account assigned only the intended role: attempt the action and confirm it succeeds or is denied as the matrix says.
4. Record the result. Where the console disagrees with the matrix, **change the matrix**, not the evidence, and log the difference below.
5. Repeat after any CrowdStrike role change and at every quarterly access review.

`pytest` enforces the bookkeeping: every matrix capability must have a worksheet row, and a row marked `yes` must carry a permission name, a date and a verifier.

## Riskiest assumptions and fallbacks

| # | Assumption in the design | If it does not hold | Fallback |
|---|---|---|---|
| A1 | Analysts cannot edit correlation rules created by others | Any analyst can alter or disable shared rules | Treat rule content as code: rule changes only by pull request reviewed by a detection engineer, with the console used for deployment only. Alert on rule modification events. |
| A2 | A custom role can give detection engineers rule management without administrator rights | Custom roles are unavailable or too coarse | Assign the NG SIEM Analyst role to detection engineers and rely on the pull-request control in A1. Record this as an accepted residual risk. |
| A3 | Containment (RTR/network contain) can be withheld from L1 analysts and granted to L2 and the automation client | Containment is bundled into a role L1 already holds | Move L1 to a role without direct containment capability. If permissions cannot be separated, record an unmet least-privilege requirement and escalate the role design. Fusion approval governs workflow actions only; it cannot prevent direct containment through another permitted interface. See ADR-009. |
| A4 | Repository and view access can be scoped per role | Scoping is tenant-wide | Drop `view-audit` and `view-network` as access boundaries and use them only as search conveniences. Remove the claim that auditors cannot see other data. |
| A5 | NG SIEM Administrator covers connectors, parsers, repositories and retention | Some of these need Falcon Administrator | Update the persona table in `05-rbac.md` and reduce use of the broader role by splitting duties across two named people. |
| A6 | An API client can be limited to the scopes Fusion needs and nothing else | Needed scopes are broader than expected | Document the actual scope list, review it quarterly, and keep one client per integration. |

## Custom-role restrictions

Whether custom roles are available, and what they can restrict, depends on the tenant and the licence. **VERIFY.** Until verified, the design must not depend on a custom role: every control that uses one (A2) has a fallback above.

## Difference log

Record every case where the console differed from the matrix.

| Date | Capability | Matrix said | Console showed | Change made | By |
|---|---|---|---|---|---|
| | | | | | |
