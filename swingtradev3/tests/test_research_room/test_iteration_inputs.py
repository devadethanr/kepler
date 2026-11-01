from research_room.grounding import packet
from research_room.iteration_inputs import compact_evidence


def test_compact_input_keeps_conflicts_and_limits_citation_choices():
    cutoff = "2025-01-01T00:00:00Z"
    packets = [
        packet(
            "A",
            "synthetic:first",
            "A reports that the gate is open.",
            event_id="event-1",
            decision_cutoff=cutoff,
        ),
        packet(
            "A",
            "synthetic:counter",
            "A reports that the gate is closed.",
            event_id="event-1",
            decision_cutoff=cutoff,
        ),
        packet(
            "A",
            "synthetic:future",
            "A reports a future published result.",
            published_at="2025-01-02T00:00:00Z",
            decision_cutoff=cutoff,
        ),
        packet(
            "A",
            "synthetic:outage",
            "A has an unavailable source excerpt.",
            status="unavailable",
            decision_cutoff=cutoff,
        ),
        packet(
            "A",
            "synthetic:plan",
            "A plans a meeting on a later date.",
            published_at="2024-12-30T00:00:00Z",
            event_at="2025-01-02T00:00:00Z",
            decision_cutoff=cutoff,
        ),
    ]
    evidence = {p["id"]: p for p in packets}
    result = compact_evidence(evidence, "A")
    assert len(result["sources"]) == len(packets)
    assert [source["source"] for source in result["sources"]] == [p["source"] for p in packets]
    assert result["sources"][0]["metadata_policy"]["freshness"] == "unknown"
    assert result["sources"][4]["metadata_policy"]["event"] == "after_cutoff"
    assert result["requested_scope"]["meaning"] == "requested scope; source relevance unverified"
    assert result["allowed_quote_ids"][0] == ""
    for item, allowed in zip(packets, [True, True, False, False, True]):
        quote_id = item["quote_spans"][0]["id"]
        option = next(x for x in result["quote_options"] if x["quote_id"] == quote_id)
        assert option["admissible"] is allowed
        assert (quote_id in result["allowed_quote_ids"]) is allowed
        assert option["source_event_id"] == item["event_id"]
    assert "semantic relevance unassessed" in result["quote_options"][0]["reason"]


def test_wrong_requested_scope_retained_but_not_citable():
    item = packet("B", "synthetic:other", "B reports the gate is open.")
    result = compact_evidence({item["id"]: item}, "A")
    assert len(result["sources"]) == 1
    assert result["allowed_quote_ids"] == [""]
    assert not result["quote_options"][0]["admissible"]
