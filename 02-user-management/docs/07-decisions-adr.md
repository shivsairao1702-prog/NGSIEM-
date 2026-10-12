# 07 - Architecture decision records

Status values: Accepted, Proposed, Superseded.

---

## ADR-001: SSO through Okta, with local accounts only for break-glass

**Status:** Accepted

**Context:** Northwind Labs uses Okta for workforce sign-in and Entra ID for Microsoft 365. The SOC needs one place to enforce MFA and offboarding.

**Decision:** Named users sign in to Falcon through SAML SSO with Okta. MFA is enforced at the IdP. Local credentials exist only for two break-glass accounts.

**Alternatives considered:** Local Falcon accounts with Falcon-side MFA (offboarding becomes a second manual task that gets missed), or Entra ID as the IdP (equally valid; Okta was chosen because the SOC already administers it and its logs are already onboarded in module 01).

**Trade-offs:** The IdP becomes a single point of failure and an attack surface. Mitigated by phishing-resistant MFA for privileged users, monitoring of IdP changes (`06-audit-and-monitoring.md`) and the break-glass accounts. **VERIFY** SSO enforcement and local sign-in behaviour for your tenant.

---

## ADR-002: Access follows IdP groups; roles are assigned manually from approved tickets

**Status:** Accepted, revisit if role sync is verified

**Context:** Mapping IdP groups to Falcon roles automatically would remove a manual step, but it is not verified that the tenant supports it, and automatic role assignment would put privilege decisions in IdP group membership alone.

**Decision:** `grp-ngsiem-<persona>` controls who can sign in. A platform engineer assigns the console role from an approved ticket. The register records both.

**Alternatives considered:** Automatic role assignment from IdP attributes (faster and removes drift, but moves privilege control entirely to the IdP).

**Trade-offs:** More manual work, and more chance of drift, which the access review's console comparison (`C03`) catches. Revisit once role sync is verified.

---

## ADR-003: Two break-glass accounts

**Status:** Accepted

**Context:** An IdP outage or compromise must not lock the SOC out. A larger pool of emergency accounts widens the attack surface.

**Decision:** Exactly two local Falcon Administrator accounts, credentials split between two custodians and sealed in the vault, tested every 90 days, any use paged as critical.

**Alternatives considered:** One account (a single point of failure and a single custodian), or an emergency role for all platform engineers (turns an emergency control into routine access).

**Trade-offs:** Two secrets to protect and test. The policy, register and tests all cap the number at two.

---

## ADR-004: Privilege is derived from module 01 capabilities

**Status:** Accepted

**Context:** A hand-maintained list of "privileged roles" drifts from the real permission matrix.

**Decision:** A persona is privileged if its role holds any of the capabilities listed in `privileged_capabilities` in the policy (user management, API client management, retention, parsers, connectors, fleet, containment). Privileged personas are reviewed every 30 days, others every 90. A test recomputes the flags from the module 01 matrix.

**Trade-offs:** L2 responders are classed as privileged because of containment. That is intended: it is the power that most needs frequent review.

---

## ADR-005: No shared accounts; non-human access only through API clients, one per integration

**Status:** Accepted

**Context:** Shared accounts and shared clients destroy accountability and widen the blast radius of a leak.

**Decision:** Every human has their own account. Every integration has its own API client with an allowlisted scope set, an owner persona and a 90-day rotation.

**Alternatives considered:** One automation client for all Fusion workflows (fewer rows, but a leak of the ticketing integration would expose containment).

**Trade-offs:** A longer register and more secrets to rotate, handled by the review tool.

---

## ADR-006: The register is intended state; the console is the source of truth

**Status:** Accepted

**Context:** A register that nobody reconciles with reality gives false assurance.

**Decision:** Each access review compares a console export with the register and the policy. A console account unknown to the register is an error (`C01`), as is a role the policy does not allow (`C03`).

**Trade-offs:** Needs a console export at every review. A manual export is acceptable until an automated one is verified.

---

## ADR-007: Reviews are automated with a dependency-free tool whose checks are locked by tests

**Status:** Accepted

**Context:** Manual spreadsheet reviews are skipped when the SOC is busy, and a checker that silently stops detecting something is worse than none.

**Decision:** `scripts/access_review.py` uses only the Python standard library. Seventeen finding codes cover users, the console and API clients. A planted-issue dataset exercises every code and tests require the tool to find exactly those errors, so removing or breaking a check fails CI.

**Trade-offs:** The policy and registers must be kept as structured files. That is a feature: they are reviewed by pull request.

---

## ADR-008: Only L2 responders, the platform owner and break-glass hold containment

**Status:** Accepted

**Context:** Module 01 (ADR-006, ADR-009) restricts host containment and puts it behind approval and guardrails.

**Decision:** The persona-to-role mapping in this module gives containment only to `soc_l2_ir`, `falcon_platform_owner` and `break_glass`, plus the `apic-fusion-containment` client. A test compares this with the module 01 matrix, so changing either side without the other fails.

**Trade-offs:** L1 analysts hand off to L2 to contain, which adds minutes. The approval step in the Fusion workflow keeps that handoff short.
