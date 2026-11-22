from asl_engine.models import extract_action


def test_plain_json():
    a = extract_action('{"action": "WAIT", "thought": "hm"}')
    assert a.action == "WAIT" and a.thought == "hm"


def test_json_inside_prose_and_code_fence():
    a = extract_action('Sure, here you go:\n```json\n{"action": "SAY", "text": "Hello", "thought": "x"}\n```\nDone.')
    assert a.action == "SAY" and a.text == "Hello"


def test_takes_the_last_valid_candidate():
    text = '{"action": "WAIT"} then I changed my mind {"action": "APPROACH", "target_id": "victim"}'
    a = extract_action(text)
    assert a.action == "APPROACH" and a.target_id == "victim"


def test_last_candidate_that_is_invalid_does_not_hide_an_earlier_valid_one():
    text = '{"action": "MOVE", "target_location": "cafe"} and also {"action": "DANCE"}'
    assert extract_action(text).action == "MOVE"


def test_no_json_or_truncated_json_gives_none():
    assert extract_action("I would simply wait.") is None
    assert extract_action('{"action": "WAI') is None
    assert extract_action("") is None


def test_json_that_is_not_an_object_or_lacks_action_gives_none():
    assert extract_action("[1, 2, 3]") is None
    assert extract_action('{"thought": "only a thought"}') is None


def test_nested_braces_do_not_confuse_the_scan():
    a = extract_action('{"note": {"x": 1}} {"action": "CALL", "text": "help {now}", "thought": ""}')
    assert a.action == "CALL" and a.text == "help {now}"
