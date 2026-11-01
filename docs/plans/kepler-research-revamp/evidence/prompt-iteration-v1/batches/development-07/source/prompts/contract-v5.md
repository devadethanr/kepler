For this supplied atomic-claim assessment, call the room_message function once.
The function call has exactly seven string arguments. Copy claim_text unchanged
into text, including negation and punctuation: it is the claim being assessed, not
an answer or correction. Set recipient to "room" and position to "question".

Set claim_kind to "question", "inference", or "observation" under the evidence
policy. Set support_assessment to "unassessed" for a question or inference; for an
observation use "supported", "contradicted", or "insufficient". Set quote_id to
one relevant admissible supplied span ID, including context for uncertainty. Set
event_id to that source's established event ID, or "" if unknown. If no relevant
admissible span exists, set both quote_id and event_id to "".

Use the supplied policy and cutoff. Call the function with these arguments and stop;
do not substitute plain text or JSON for the function call.
