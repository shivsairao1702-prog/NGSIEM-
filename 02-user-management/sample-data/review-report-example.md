# Access review as of 2026-10-12

Inputs: user-register-with-issues.csv, api-client-register-with-issues.csv, console-export-with-issues.csv

**15 error(s), 11 warning(s)**

| Severity | Code | Subject | Finding |
|---|---|---|---|
| error | A01 | `apic-fusion-containment-legacy` | API client has no valid owner persona: owner '' |
| error | A02 | `apic-falconpy-inventory-write` | API client scopes exceed the allowlist for its integration: extra scopes ['hosts:write'] |
| error | A03 | `apic-fusion-ticketing-old` | API client secret rotation is overdue: last rotated 2026-05-01 |
| error | A05 | `apic-chatops-bot` | API client integration is not in the scope allowlist: integration 'chatops-bot' |
| error | C01 | `nw-shadow-01` | Console account is not in the register |
| error | C03 | `nw-soc-l1-01` | Console roles differ from the policy for the persona: console ['NG SIEM Administrator'], policy ['NG SIEM Analyst'] |
| error | C04 | `nw-deteng-02` | Account disabled in the register is still present in the console: register status 'disabled' |
| error | U01 | `nw-intern-01` | Persona is not defined in the policy: persona 'intern' |
| error | U02 | `nw-soc-l1-02` | Matrix role does not match the persona's role: has detection_engineer, persona soc_l1 allows analyst_l1 |
| error | U03 | `nw-soc-l1-03` | Named user has no SSO group |
| error | U04 | `nw-soc-l1-04` | Account is still active after its end date: ended 2026-09-30 |
| error | U05 | `nw-deteng-01` | Access review is overdue: last reviewed 2026-05-01, limit 90 days |
| error | U05 | `nw-platform-02` | Access review is overdue: last reviewed 2026-08-20, limit 30 days |
| error | U06 | `falcon_platform_owner` | More holders than the persona allows: 3 holders, maximum 2 |
| error | U08 | `nw-bg-02` | Break-glass account test is overdue: last tested 2026-03-01 |
| warning | A04 | `apic-chatops-bot` | API client scopes have not been verified against the console |
| warning | A04 | `apic-ci-rule-deploy` | API client scopes have not been verified against the console |
| warning | A04 | `apic-falconpy-inventory` | API client scopes have not been verified against the console |
| warning | A04 | `apic-falconpy-inventory-write` | API client scopes have not been verified against the console |
| warning | A04 | `apic-fusion-containment` | API client scopes have not been verified against the console |
| warning | A04 | `apic-fusion-containment-legacy` | API client scopes have not been verified against the console |
| warning | A04 | `apic-fusion-ticketing` | API client scopes have not been verified against the console |
| warning | A04 | `apic-fusion-ticketing-old` | API client scopes have not been verified against the console |
| warning | C02 | `nw-audit-01` | Active register user is missing from the console |
| warning | U07 | `detection_engineer` | Active holders differ from the planned headcount: 1 active, 2 planned |
| warning | U07 | `falcon_platform_owner` | Active holders differ from the planned headcount: 3 active, 1 planned |
