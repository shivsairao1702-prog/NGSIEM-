# 01 - Overview and scope

## Purpose

This document defines the environment the NG-SIEM architecture is designed for, the use cases it must serve, and what is deliberately out of scope.

## The fictional organisation: Northwind Labs

All values in this project are fictional planning figures. Nothing here comes from a real tenant.

| Attribute | Value |
|---|---|
| Employees | 500 |
| Managed endpoints (Falcon sensor) | 300 |
| Identity provider | Okta (SSO) and Microsoft Entra ID |
| Productivity | Microsoft 365 |
| Cloud | AWS (single organisation, management events) |
| Network security | FortiGate firewalls, Zscaler Internet Access |
| Directory | Windows Active Directory (domain controllers) |
| Servers | Linux servers (auth/syslog) |
| SOC model | Small in-house SOC, business-hours analysts plus an on-call engineer |

## What NG-SIEM is, in one paragraph

NG-SIEM is part of the Falcon platform, not a separate product. First-party data from Falcon modules (sensor/EDR, Identity Protection, Cloud Security, Exposure Management) is already in the platform and is never forwarded. Third-party data (firewalls, identity providers, cloud, SaaS, proxies) must be ingested, parsed and stored. The storage and search engine underneath is Falcon LogScale, which is index-free: events are stored compressed in time-ordered segments and searches read only the segments inside the requested time range.

## Use cases the design must serve

1. **Identity threat detection**: impossible travel, MFA fatigue, risky sign-ins across Okta and Entra ID.
2. **Cloud control-plane monitoring**: suspicious AWS API activity from CloudTrail.
3. **Network and web visibility**: correlating firewall and proxy activity with endpoint telemetry.
4. **Windows and Linux authentication monitoring**: brute force, lateral movement indicators.
5. **Automated response**: alert on third-party data, then contain the host through the Falcon sensor using Fusion SOAR.
6. **Investigation**: one search surface across first-party and third-party data.

## In scope

- Logical architecture and data flow
- Sizing and licensing headroom
- Repository, retention and view design
- Role-based access control design
- Naming and tagging conventions
- Recorded design decisions (ADRs)

## Out of scope (covered by other projects in this lab)

| Topic | Where it is covered |
|---|---|
| Step-by-step source onboarding and custom parsers | module 03 (data onboarding) |
| Collector deployment, health monitoring, silent-source alerting | module 04 (collector fleet health) |
| Detection content (CQL rules, correlation rules) | module 06 (detections as code) |
| Fusion SOAR workflow build-out | module 09 (Fusion SOAR workflows) |
| Falcon sensor deployment and host policies | Not covered in this lab yet |

## Assumptions and verification status

Items marked **VERIFY** must be checked against current CrowdStrike documentation and your own licence before relying on them. Licensing, retention limits and role names vary by contract and change over time. See the verification checklist in the root `README.md`.
