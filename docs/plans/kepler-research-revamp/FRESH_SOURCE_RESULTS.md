# Fresh source run results

**Status: run collection complete.** Run `fresh-source-20261101T195640Z` has eight completed rooms. This report records bounded bookkeeping and sanitized public evidence only; it does not assess financial accuracy or claim that the rooms passed. Integration and service checks are tracked in `FRESH_SOURCE_FINDINGS.md`.

## Frozen plan

- Unique frozen reference questions: 3; planned paired comparison: 6 rooms (3 ordinary-tool, 3 saved-source). The two development rooms are separate.
- Declared ceiling: 120 model admissions, 120 tool admissions; 24 development and 96 frozen/integrated model admissions. Each model generation after a tool call is counted separately. Provider HTTP requests are counted separately.
- Frozen case SHA-256: `b5b8a502bf2ac854a1516e0fb866ef1117f51fd0d7819fa5c1cf778ea629011e`.
- Frozen source export SHA-256: `061c0522e0cea46f79f5d26b0583c5ddb435b9d2545e1e293c0cb868af2e3113`.
- Active instructions SHA-256: `58bd97fdb300db89908729c0fad7297a60f831d3d2687b628e5c5844046969e3`.
- Frozen case set, source refs, and allocation are exported under `evidence/fresh-source-v1/`. Hashes and source references are identifiers, not validation of source correctness.

## Final accounting and source-ingestion snapshot

Final run-native accounting: 93 model admissions and 88 tool admissions; reserved tokens 3,047,424; reported actual input tokens 643,713 and output tokens 9,962; 2 calls have unknown provider usage. Development source used 12 model and 12 tool admissions and ended in abstention after the `UTC None` tool failure; that integration bug was fixed offline before paired generation; development cancel used 2 model and 0 tool admissions. Frozen rooms used 79 model and 76 tool admissions (calculated by summing the six frozen-room counters). All six paired rooms and both development rooms have ended; failed and abstention statuses are preserved in `evidence/fresh-source-v1/accounting.json`.

The initial feed ingestion logged four source operations: SEBI RSS (30 entries, 1 HTTP request), PIB RSS (20 entries, 1), RBI RSS (10 entries, 1), and one PIB HTML release (request count not reported; bound 4). A repeat logged SEBI `304 Not Modified` (1 HTTP request) and RBI RSS (10 entries, 1). The repeat RBI ingest caused ten metadata revisions after the frozen cutoff as its terms label was corrected; earlier frozen version references are retained and must not be silently replaced. Feed coverage is limited to the observed current window; no historical pagination completeness is established. Across feed-ingestion records there are five known feed HTTP requests: three initial feed requests plus the repeat SEBI 304 and RBI request. The PIB HTML attempt has an unknown request count, bounded at four. These HTTP counts come from ingestion result records and are not model/tool admissions.

A first orchestrator process was killed before its database outcome could be established. Its usage is unknown; up to 10 requests were reserved as a bound and are not asserted as actual calls. The separate probe report records at least 21 known commands/responses, with a possible incomplete count. Do not sum that probe figure into model/tool admissions or state an exact HTTP total from it. The frozen cutoff snapshot contains 61 current source items. The later repeat added ten RBI terms-label revisions, leaving 71 immutable versions across those 61 current items. Preserve the original 61 frozen references. Do not call the repeat RBI ingest idempotent: a third repeat was not tested.

Durable events contain three model budget denials and zero tool budget denials across the eight rooms. The separate synthetic protocol-zero test made one rejected model-admission request; the typed `call_limit` marker survived with zero model or tool admissions and did not rewrite failed room records. Per-room elapsed times from the first `room.started` through `room.finished` are in `evidence/fresh-source-v1/room-latency.json`. Participant-role model counts remain unknown because durable `budget.admitted` events do not identify a participant role.

The three `browser_read` tool jobs are logged separately from tool admissions. Their room events show two tool-level capability denials requiring browser skill discovery/load and one empty result; they do not contain HTTP request counts or statuses. The public-fetch loop permits at most four requested URLs total. The two pre-skill denials made zero public fetches; the remaining empty-result job reached a completed capture, but its exact HTTP count was not recorded. The public-fetch accounting is in `evidence/fresh-source-v1/browser-fetch-accounting.json`. The separate source probes report at least 21 known commands/responses but may be incomplete; the killed orchestrator outcome and usage remain unknown, with up to ten requests reserved as a bound. Across the full run, 93 model admissions do not establish 93 provider HTTP requests; two usage records are unknown, and forwarding for the two cancelled admissions is unconfirmed.

## Run-native evidence locations

Private source artifacts remain at `/home/devadethanr/.local/state/kepler-rooms/fresh-source-20261101T195640Z`. Raw room/private records are not copied into this repository. Sanitized exports contain the frozen references and only whitelisted public room messages/source metadata, with source quote payloads withheld; visible participant messages and source metadata are exported. No account data, HTML bodies, credentials, or private model reasoning are exported.

## Paired-room outcomes and limits

The completed public-message audit reports saved-source title coverage for 3/3 unique questions and ordinary-tool title coverage for 0/3. The ordinary rooms emitted 11 public messages, with three referring to historical non-primary material; saved-source rooms emitted 23 public messages, with 20 admitted-reference message instances covering the same three frozen titles, including repeated references. These are retrieval and public-message counts, not independent fact counts or accuracy scores. Several rooms ended failed or abstained; the exact status and failure reasons are preserved without rewriting in the accounting export.

## Limitations

The denominator is three unique real questions, not six independent cases. Ordinary tools read current graph/files/browser views and are not verified point-in-time captures, so this is not a strict causal historical replay. Sources do not establish complete coverage, and a valid empty feed would not establish that no announcement exists. Company-disclosure coverage remains incomplete absent an exchange/company source with established issuer identity. This run is a bounded evidence-service exercise and cannot establish financial accuracy.
