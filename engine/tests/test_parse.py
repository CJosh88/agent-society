from asl_engine.models import extract_picks

FOUR = '{"picks": [{"ticket": "T01", "priority": "HIGH"}, {"ticket": "T02", "priority": "low"}], "thought": "hm"}'


def test_plain_json_and_case_is_normalised():
    a = extract_picks('{"picks": [{"ticket": "t07", "priority": "low"}], "thought": "hm"}')
    assert a.picks[0].ticket == "T07" and a.picks[0].priority == "LOW" and a.thought == "hm"


def test_json_inside_prose_and_code_fence():
    a = extract_picks(f"Sure, here you go:\n```json\n{FOUR}\n```\nDone.")
    assert [p.ticket for p in a.picks] == ["T01", "T02"]


def test_takes_the_last_valid_candidate():
    text = '{"picks": [{"ticket": "T01", "priority": "HIGH"}]} then I changed my mind ' + FOUR
    assert len(extract_picks(text).picks) == 2


def test_last_candidate_that_is_invalid_does_not_hide_an_earlier_valid_one():
    text = FOUR + ' and also {"picks": [{"ticket": "T03", "priority": "MEDIUM"}]}'
    assert [p.ticket for p in extract_picks(text).picks] == ["T01", "T02"]


def test_no_json_or_truncated_json_gives_none():
    assert extract_picks("I would simply pick T01.") is None
    assert extract_picks('{"picks": [{"ticket": "T0') is None
    assert extract_picks("") is None
    assert extract_picks('{"action": "WAIT"}') is None
