# 07 - Architecture decision records

Each record states the context, the decision, the alternatives and the trade-offs. Status values: Accepted, Proposed, Superseded.

---

## ADR-001: Do not forward first-party Falcon data

**Status:** Accepted

**Context:** NG-SIEM is part of the Falcon platform. Sensor, Identity, Cloud and Exposure Management data is already structured and searchable.

**Decision:** Never build connectors or parsers for first-party data. Ingest only third-party sources.

**Consequences:** No duplicate ingest cost and no parser upkeep for Falcon data. Third-party sizing excludes it entirely.

---

## ADR-002: Choose the ingest method by source type

**Status:** Accepted

**Context:** The platform offers data connectors (API pull), HEC (push), Falcon Log Collector with Fleet management, and CrowdStream.

**Decision:**

| Source type | Method |
|---|---|
| SaaS, cloud and identity with a native API | Data connector |
| Systems that push over HTTPS | HEC |
| Syslog, Windows events and files on the network | Falcon Log Collector |
| High-volume sources that need filtering before ingest | CrowdStream |

**Alternatives considered:** Using Falcon Log Collector for everything (more infrastructure to run), and HEC for everything (requires every source to support it).

**Trade-offs:** Four methods means more to learn, but each source gets the method with the least operating effort.

---

## ADR-003: Filter FortiGate traffic logs before ingest

**Status:** Accepted

**Context:** FortiGate traffic is the largest single source at about 4.75 GB/day raw, and much of it is allowed internal-to-internal noise.

**Decision:** Filter it before ingest with CrowdStream, with a planned 50% reduction.

**Alternatives considered:** Ingest everything (simple but pushes the design over the free tier), or drop the source (loses network visibility).

**Trade-offs:** Filtered events cannot be searched later. Keep the filter rules in version control and review them quarterly. **VERIFY** CrowdStream availability under your licence.

---

## ADR-004: Split repositories by retention and access only

**Status:** Accepted

**Context:** Retention is set per repository. The first draft placed 90-day and 180-day sources in one network repository, which is not possible.

**Decision:** Six repositories (see `04-retention-and-repositories.md`). Split only for retention or access. Use tags for everything else.

**Alternatives considered:** One repository for all third-party data (cannot give sources different retention), or one repository per source (too many to administer and harder to search together).

**Trade-offs:** Cross-source searches need a view. Mitigated with `view-soc-all`.

---

## ADR-005: Use the platform's tag schema unchanged

**Status:** Accepted

**Context:** Out-of-the-box parsers, detections and dashboards assume the ECS-based CPS tags.

**Decision:** Use `#Vendor`, `#event.module`, `#event.dataset`, `#observer.type`, `#event.kind`, `#event.outcome`, `#ecs.version` and `#Cps.version` exactly as defined. Never use a high-cardinality field as a tag.

**Trade-offs:** Less freedom in custom parsers, but all vendor content keeps working and datasource counts stay low.

---

## ADR-006: Built-in roles first, containment granted separately

**Status:** Accepted

**Context:** A small SOC needs simple, auditable access.

**Decision:** Assign built-in NG-SIEM roles by persona, keep Falcon Administrator to one named owner, and grant host-containment permission only to L2 responders and to the Fusion API client.

**Alternatives considered:** Giving all analysts containment rights (faster response but higher risk of accidental isolation).

**Trade-offs:** L1 analysts must hand off to L2 to isolate a host. Mitigate with a Fusion workflow that requests approval and then contains.

---

## ADR-007: Treat the free third-party ingest tier as a planning boundary

**Status:** Proposed

**Context:** Modelled ingest after filtering is 8.03 GB/day. With a 25% growth buffer it is 10.03 GB/day, which is 0.03 GB/day above the free tier recorded in the study notes.

**Decision:** Stay inside the free tier by tightening filters on the two largest sources (FortiGate traffic and Zscaler) before growth arrives. If the boundary is still crossed after tuning, obtain a licensed volume.

**Alternatives considered:** Buying licensed volume now (cost before the need is proven), or dropping a source (loses visibility).

**Trade-offs:** Requires measuring real ingest in the first month and revisiting this record. **VERIFY** the free tier figure against current licensing before relying on this decision.

---

## ADR-008: Automate response through Fusion SOAR with scoped API clients

**Status:** Accepted

**Context:** Alerts on third-party data (for example an identity alert) should be able to contain a host through the Falcon sensor without extra integration.

**Decision:** Use Fusion SOAR workflows for containment and notification. Automation runs through dedicated API clients with minimal scopes. Third-party SOAR actions and correlation rule templates may require a paid NG-SIEM licence, so confirm entitlement.

**Trade-offs:** Workflows must be tested and version controlled (see `fusion-soar-workflows` and `ci-cd-for-security`).
