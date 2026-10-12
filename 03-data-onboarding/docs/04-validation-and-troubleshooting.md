# 04 - Validation and troubleshooting

Replace `<CONNECTION_ID>` with the data connection ID in your private copy. Run in Advanced Event Search over the past 15 minutes. **VERIFY** function behaviour in your tenant: these use standard CQL but have not been run against one in this repository.

## 1. Do events arrive and are the key fields populated

```text
#dataConnectionID = "<CONNECTION_ID>"
| table([@timestamp, @ingesttimestamp, host.hostname, process.name, process.pid, message])
```

Pass: rows appear, those columns are populated, and no row has `@error:true`.

## 2. How complete is each field

```text
#dataConnectionID = "<CONNECTION_ID>"
| case { host.hostname = * | has_host := 1; * | has_host := 0; }
| case { process.name = * | has_proc := 1; * | has_proc := 0; }
| groupBy([], function=[count(as=events), sum(has_host, as=with_host), sum(has_proc, as=with_proc)])
| host_pct := with_host / events * 100
| proc_pct := with_proc / events * 100
```

Pass: each percentage meets the figure recorded in the source's runbook. For the Datagen feed expect 100 for both; a real source records its own expectation.

## 3. Parse failures

```text
#dataConnectionID = "<CONNECTION_ID>"
| error.message = *
| groupBy([error.message], function=count())
```

and

```text
#dataConnectionID = "<CONNECTION_ID>"
| @error = true
| table([@timestamp, @error_msg, @rawstring])
```

Pass: zero, or below the threshold the runbook sets. A rise after a sender upgrade means the log format changed.

## 4. Timestamp skew

```text
#dataConnectionID = "<CONNECTION_ID>"
| skew_s := (@ingesttimestamp - @timestamp) / 1000
| skew_s > 3600 or skew_s < -300
| table([@timestamp, @ingesttimestamp, skew_s, Vendor.timestamp])
```

Pass: no rows for live data. Rows near a year apart point to the year-assumption limitation; rows a fixed number of hours apart point to a wrong time zone.

## 5. Tags

```text
#dataConnectionID = "<CONNECTION_ID>"
| groupBy([#Vendor, #event.module, #event.dataset, #observer.type], function=count())
```

Pass: only the values module 01 allows. An unexpected value means a parser or tag-field setting is wrong.

## Symptom table

| Symptom | Likely cause | First check |
|---|---|---|
| No events at all | Connector credentials, wrong API URL, sender not deployed, destination blocked | Sender-side error and last-sent time; connector status |
| Events arrive, `host.hostname` empty | Envelope not unwrapped, or the regex does not match the sender's format | `@rawstring` of one event: starts with `{`? Query 3 |
| Events missing on days 1 to 9 | Timestamp format uses plain `d` | The parser's format string |
| Times off by a whole number of hours | Sender logs local time, parser assumes UTC | Query 4, then the sender's zone setting |
| Times a year out | Year assumed for a time with no year | Query 4; limitation in `03-parser-walkthrough.md` |
| `@error:true` on some events | `parseTimestamp` rejected the value | Query 3, second form |
| High volume of one tag value | A high-cardinality field used as a tag | Parser tag-field settings |
| Duplicate events | Sender retried after a timeout | Compare `event.original` and `@ingesttimestamp` of the pair |
| Data stops after working | Credential expiry, source change, pipeline stopped | Module 04 silence alert; connector and sender status |
