# 03 - Data onboarding

Part of the [NG-SIEM lab](../README.md). How a log source gets into NG-SIEM correctly: choosing the method, parsing, validating, and proving it is done. Methods and repositories follow module 01 ([`01-architecture`](../01-architecture)).

## Goal

Make onboarding repeatable and checkable. A source is not onboarded when events arrive; it is onboarded when the fields are populated, the time is right, parse failures are visible and the evidence is kept.

## Status

| Source | Method | Status |
|---|---|---|
| Cribl Datagen syslog (synthetic, test only) | Cribl Stream Quick Connect to a Cribl data connector | Current committed CQL confirmed tested in a working environment by the project owner on 2026-10-12; synthetic model tests also pass |
| Linux Audit | Falcon Log Collector | Next |
| Windows Security | Falcon Log Collector | Next |
| Okta | Data connector | Next |
| AWS CloudTrail | Data connector (S3/SQS) | Next |

## Contents

| Path | What it covers |
|---|---|
| [`docs/01-onboarding-methods.md`](docs/01-onboarding-methods.md) | Choosing a method, parser rules, where test data may go, lifecycle, definition of done |
| [`docs/02-cribl-quick-connect-runbook.md`](docs/02-cribl-quick-connect-runbook.md) | Cribl Datagen through Quick Connect into NG-SIEM, with problems met and how to keep evidence safely |
| [`docs/03-parser-walkthrough.md`](docs/03-parser-walkthrough.md) | The syslog parser: flow, decisions, fixes since 1.0.0, limitations, what is not proven |
| [`docs/04-validation-and-troubleshooting.md`](docs/04-validation-and-troubleshooting.md) | Validation queries and a symptom table |
| [`config/parsers/cribl-datagen-syslog.cql`](config/parsers/cribl-datagen-syslog.cql) | The parser |
| [`config/parsers/cribl-datagen-syslog.meta.json`](config/parsers/cribl-datagen-syslog.meta.json) | Tag fields, test-only flag, items to verify in a tenant |
| [`sample-data/datagen-syslog-cases.json`](sample-data/datagen-syslog-cases.json) | 16 synthetic inputs with the fields each must produce |
| [`scripts/parser_ref.py`](scripts/parser_ref.py) | Python model of the parser that reads the real CQL file |

## Try it

```bash
python3 scripts/parser_ref.py '<13>Sep  9 03:04:05 db02 cron[77]: job ran'
```

## Validation

`tests/test_parser.py` runs every case through the model and checks that fields are present or absent as stated. It also pins the validated regex, the section order, the fields dropped in cleanup, and agreement with module 01 (tag fields must be in the module 01 tag list, `event.dataset` must be `module.dataset`, high-cardinality fields must not be tags). Removing a fix, such as the envelope prefix or the padded-day format, fails a test.

```bash
pip install -r ../requirements-dev.txt
pytest -q
```

## Verify before relying on this

- [x] Project owner confirms the current committed CQL was tested in a working environment (2026-10-12). CI runs the Python model, not CQL.
- [ ] Record sanitized inputs, outputs and validation coverage for reproducibility.
- [ ] Items in `verify_in_tenant` in the parser's metadata file
- [ ] Cribl and console menu names for the versions you run
- [ ] Whether persistent queueing is needed for real sources
