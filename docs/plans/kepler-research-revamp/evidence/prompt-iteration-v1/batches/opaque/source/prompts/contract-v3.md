Assess the supplied claim_text, then call room_message once. No retrieval or retry.
Follow the evidence policy. Do not explain or correct the claim in the text field.

Output rules, independently for each field:
recipient = "room"
position = "question"
text = claim_text copied exactly, including its negation and punctuation
claim_kind = "question" for an open question, "inference" for a prediction/causal
hypothesis, otherwise "observation"
support_assessment = "unassessed" whenever claim_kind is question or inference;
otherwise supported, contradicted or insufficient under the evidence policy
quote_id = a relevant admissible supplied span's q: ID; use context/counterevidence
even for an unassessed or insufficient claim when applicable
event_id = the cited source's established event ID, or "" when not established

Do not cite different actual entities/events or irrelevant spans merely because
their metadata scope label matches. Never cite a publication after decision_cutoff.
If no admissible relevant span exists, BOTH quote_id and event_id must be "".
Unknown/stale context may illustrate uncertainty; future plans do not establish
past occurrence. A plan alone is insufficient, not explicit contradiction.
Use the evidence_policy supplied with this case; assume no fixed dates or values.
Return only the seven string tool arguments. A support label qualifies the exact
input assertion; replacing it with your corrected answer invalidates the record.
