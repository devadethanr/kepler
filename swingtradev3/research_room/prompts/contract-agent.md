Single-claim assessment mode. Call the room_message FUNCTION exactly once now.
No prose response, explanation, correction, retrieval or further discussion.

Fill its seven string arguments:
recipient: "room"
position: "question" (assessment mode, regardless of support label)
text: copy the supplied claim_text byte for byte, preserving punctuation and Unicode;
      add no prefix, quotation marks around the claim, or explanation.
claim_kind: classify that supplied sentence as observation, inference or question.
support_assessment: for an observation choose supported, contradicted or insufficient
      from the evidence; for inference/question choose unassessed.
quote_id: one relevant admissible supplied span, including context for uncertainty,
      inference or a question; "" only if none is relevant and admissible.
event_id: the selected source's known event ID, or "" if it is unknown or no quote.

Assess the original assertion, not a rewritten denial or a statement about your own
confidence. An assertion with unknown support is still an observation/insufficient.
Use only input-defined values, cutoff and freshness policy. Call the function and stop.
