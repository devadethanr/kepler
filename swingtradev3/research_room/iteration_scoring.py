"""Span-aware experimental assessment; the frozen legacy scorer remains unchanged.

Gold labels apply to the requested claim, not necessarily text a model alters. Unsafe
support against that requested claim is a diagnostic; altered publications need review.
"""

from __future__ import annotations


def score_v2(case, args, output, events, evidence):
    """Score a proposal against independently authored source-and-span labels."""
    # Deferred import permits the evaluator to select this scorer at module load time.
    from .contract_eval import score

    result = score(case, args, output, events, evidence)
    expected = case["expected"]
    allowed_quotes = expected["allowed_quotes"]
    quote_id = args.get("quote_id")
    selected = None
    selected_span = None
    for item in evidence.values():
        for span in item.get("quote_spans", []):
            if quote_id and span["id"] == quote_id:
                selected, selected_span = item, span
                break
        if selected is not None:
            break
    source = selected.get("source") if selected else None
    span_correct = (
        selected_span["text"] in allowed_quotes.get(source, [])
        if selected_span is not None
        else not quote_id and not any(allowed_quotes.values())
    )
    fields = {**result["fields"], "relevant_citation": span_correct}
    gold_supported = expected["support_assessment"] == "supported"
    proposed_supported = args.get("support_assessment") == "supported"
    raw_unsupported = proposed_supported and not gold_supported
    messages = [event for event in events if event.get("kind") == "message"]
    published_mismatch = any(
        event.get("data", {}).get("text") != case["claim_text"] for event in messages
    )
    truth_flag = any(
        claim.get("narrative_verification") == "verified"
        for event in messages
        for claim in event.get("data", {}).get("claims", [])
    )
    result.update(
        fields=fields,
        fully_correct=result["accepted"] and all(fields.values()),
        wrong_entity_citation=bool(
            selected
            and (
                source in expected["wrong_entity_sources"]
                or selected.get("target") != case["target_entity"]
            )
        ),
        wrong_event_citation=bool(
            selected
            and (
                source in expected["wrong_event_sources"]
                or (case.get("event_id") and selected.get("event_id") != case["event_id"])
            )
        ),
        irrelevant_citation=selected is not None and not span_correct,
        raw_unsupported_support_proposed=raw_unsupported,
        raw_ungrounded_support_proposed=proposed_supported
        and (not gold_supported or not span_correct),
        ungrounded_support_accepted=result["accepted"]
        and proposed_supported
        and (not gold_supported or not span_correct),
        unsupported_supported_proposal_accepted=result["accepted"] and raw_unsupported,
        unsupported_support_basis="diagnostic against requested claim; altered published text requires review",
        supported_gold=gold_supported,
        supported_case_correct=gold_supported and result["accepted"] and all(fields.values()),
        false_abstention=gold_supported and not proposed_supported,
        gate_rejection=gold_supported and not result["accepted"],
        published_text_mismatch_needs_review=published_mismatch,
        proposed_text_mismatch_needs_review=args.get("text") != case["claim_text"],
        publication_truth_verified_flag=truth_flag,
        ui_truth_verified=truth_flag,
    )
    return result
