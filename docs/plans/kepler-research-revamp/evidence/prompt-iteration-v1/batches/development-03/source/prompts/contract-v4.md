Use the room_message FUNCTION now. Do not output a plain-text answer or plain JSON.
Your function call must contain exactly the seven string arguments in its schema.

Set recipient to room and position to question. Copy claim_text verbatim into text;
do not explain, correct, negate or append anything to the supplied assertion.
Classify its kind. An open question is question; a prediction/causal hypothesis is
inference; a factual assertion is observation. For question/inference the support
label is unassessed. For observation apply the evidence policy to the whole claim.

Choose one relevant admissible supplied q: span, including context for uncertainty.
Actual entity/event mismatch, irrelevant text, unavailable status or future
publication means do not cite that span, even if packet labels match the request.
With no relevant admissible span, quote_id and event_id are BOTH empty strings.
With a quote, event_id is the cited source's established ID or empty if unknown.
Use the provided evidence_policy and cutoff; assume no fixed dates or values.
Call the function once and stop. No explanation, analysis, retrieval or retry.
