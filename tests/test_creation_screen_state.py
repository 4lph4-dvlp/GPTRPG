"""12.3-02 — GM의 나머지 세 마디를 사건으로 남기고(Task 1), 만들기 진행
상태를 폴링 응답에 싣고(Task 2), 룰북 만들기 항목 선언 전용 경로를 시험한다
(Task 3).

`tests/test_creation_screen_tracer.py`의 조립 방식(`web_client_with_fake_provider`
+ `conftest.FakeProvider`)을 그대로 따른다.
"""

import json

from conftest import FakeProvider

SESSION_ID = "creation-screen-state-s1"
CHARACTER_ID = "hero-1"
BROWSER_ID = "b-hero-1"


def _fix_party_size(client, *, count: int = 3, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/party-size",
        json={"player_character_count": count, "rulebook_id": "dungeonworld_like"},
    )


def _submit_step(
    client,
    *,
    character_id: str,
    browser_id: str,
    step_id: str,
    session_id: str = SESSION_ID,
    **payload,
):
    return client.post(
        f"/api/sessions/{session_id}/creation/step",
        json={
            "character_id": character_id,
            "browser_id": browser_id,
            "step_id": step_id,
            "rulebook_id": "dungeonworld_like",
            **payload,
        },
    )


def _submit_name_step(
    client,
    *,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    text_value: str = "브람",
    session_id: str = SESSION_ID,
):
    return _submit_step(
        client,
        character_id=character_id,
        browser_id=browser_id,
        step_id="name",
        session_id=session_id,
        text_value=text_value,
    )


def _complete_all_required_steps(
    client,
    *,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    session_id: str = SESSION_ID,
):
    """던전월드류 대본의 필수 항목 전부(archetype/backstory/ability_array/hp/name)를
    채운다 — `tests/test_creation_gm.py`와 같은 흐름."""
    for step_id, payload in (
        ("archetype", {"picked": ["몸으로 먼저 막아선다"]}),
        ("backstory", {"text_value": "우물 마을 순찰대에 뒤늦게 합류한 떠돌이 검객"}),
        (
            "ability_array",
            {
                "axis_values": [
                    {"axis_name": "STR", "value": 2},
                    {"axis_name": "DEX", "value": 1},
                    {"axis_name": "CON", "value": 1},
                    {"axis_name": "INT", "value": 0},
                    {"axis_name": "WIS", "value": 0},
                    {"axis_name": "CHA", "value": -1},
                ]
            },
        ),
        ("hp", {}),
    ):
        response = _submit_step(
            client,
            character_id=character_id,
            browser_id=browser_id,
            step_id=step_id,
            session_id=session_id,
            **payload,
        )
        assert response.status_code == 200, response.text
    assert (
        _submit_name_step(
            client, character_id=character_id, browser_id=browser_id, session_id=session_id
        ).status_code
        == 200
    )


def _complete_creation(
    client,
    *,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    session_id: str = SESSION_ID,
    one_line_intro: str = "브람은 조용한 마을을 떠나온 모험가다.",
):
    return client.post(
        f"/api/sessions/{session_id}/creation/complete",
        json={
            "character_id": character_id,
            "browser_id": browser_id,
            "rulebook_id": "dungeonworld_like",
            "one_line_intro": one_line_intro,
        },
    )


def _nominate(client, *, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/nominate",
        json={"rulebook_id": "dungeonworld_like"},
    )


def _follow_up(client, *, character_id: str = CHARACTER_ID, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/follow-up",
        json={"character_id": character_id, "rulebook_id": "dungeonworld_like"},
    )


def _wrap_up(client, *, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/wrap-up",
        json={"rulebook_id": "dungeonworld_like"},
    )


def _events_of_type(client, event_type: str, *, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert response.status_code == 200
    return [event for event in response.json()["events"] if event["event_type"] == event_type]


# ---------------------------------------------------------------------------
# Task 1 — nominate/follow-up/wrap-up이 announce와 같은 모양으로 사건에 남고
# 서버가 한 번만 낸다(D-02/D-12).
# ---------------------------------------------------------------------------


def test_nominate_records_a_single_creation_gm_spoke_event(web_client_with_fake_provider):
    provider = FakeProvider(complete_value="[]")  # 계약 위반 -> 후보 첫 번째로 폴백
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-nominate-once"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        response = _nominate(client, session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["character_id"] == CHARACTER_ID
        assert isinstance(body["seq"], int)

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert len(events) == 1
        assert events[0]["kind"] == "nominate"
        assert events[0]["target_character_id"] == CHARACTER_ID


def test_nominate_called_twice_in_the_same_state_does_not_call_the_provider_again(
    web_client_with_fake_provider,
):
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-nominate-dedupe"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        first = _nominate(client, session_id=session_id)
        assert first.status_code == 200
        assert len(provider.calls) == 1

        second = _nominate(client, session_id=session_id)
        assert second.status_code == 200
        assert len(provider.calls) == 1  # 다시 부르지 않았다

        assert first.json() == second.json()
        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert len(events) == 1


def test_nominate_records_a_new_event_after_candidate_list_changes(
    web_client_with_fake_provider,
):
    """후보 목록이 실제로 바뀐 뒤(한 사람이 완성된 뒤)에는 새 사건을
    남긴다 — 중복 방지가 진행을 막지 않는다."""
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-nominate-progress"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(
            client, character_id="hero-1", browser_id="b-hero-1", session_id=session_id
        ).status_code == 200

        first = _nominate(client, session_id=session_id)
        assert first.status_code == 200
        assert first.json()["character_id"] == "hero-1"

        _complete_all_required_steps(
            client, character_id="hero-1", browser_id="b-hero-1", session_id=session_id
        )
        assert _complete_creation(
            client, character_id="hero-1", browser_id="b-hero-1", session_id=session_id
        ).status_code == 200
        client.cookies.clear()  # hero-1의 쿠키를 벗어야 hero-2의 항목을 낼 수 있다
        assert _submit_name_step(
            client, character_id="hero-2", browser_id="b-hero-2", session_id=session_id
        ).status_code == 200

        second = _nominate(client, session_id=session_id)
        assert second.status_code == 200
        assert second.json()["character_id"] == "hero-2"
        assert second.json()["seq"] != first.json()["seq"]

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        nominate_events = [event for event in events if event["kind"] == "nominate"]
        assert len(nominate_events) == 2


def test_follow_up_records_a_single_creation_gm_spoke_event_when_needs_more(
    web_client_with_fake_provider,
):
    provider = FakeProvider(
        complete_value=json.dumps([{"needs_more": True, "question": "그때 무슨 소리를 들었나요?"}])
    )
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-once"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        response = _follow_up(client, session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["needs_more"] is True
        assert body["question"]
        assert isinstance(body["seq"], int)

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        follow_up_events = [event for event in events if event["kind"] == "follow_up"]
        assert len(follow_up_events) == 1
        assert follow_up_events[0]["target_character_id"] == CHARACTER_ID


def test_follow_up_called_twice_in_the_same_state_does_not_call_the_provider_again(
    web_client_with_fake_provider,
):
    provider = FakeProvider(
        complete_value=json.dumps([{"needs_more": True, "question": "그때 무슨 소리를 들었나요?"}])
    )
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-dedupe"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        first = _follow_up(client, session_id=session_id)
        assert first.status_code == 200
        assert len(provider.calls) == 1

        second = _follow_up(client, session_id=session_id)
        assert second.status_code == 200
        assert len(provider.calls) == 1

        assert first.json() == second.json()
        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert len([e for e in events if e["kind"] == "follow_up"]) == 1


def test_follow_up_with_no_more_questions_records_no_event(web_client_with_fake_provider):
    """GM이 되묻지 않기로 하면(`needs_more=False`) 대화 줄기에 남길 말이
    없으므로 사건을 안 남긴다(D-02 ④)."""
    provider = FakeProvider(complete_value=json.dumps([{"needs_more": False, "question": None}]))
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-none"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        response = _follow_up(client, session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["needs_more"] is False
        assert body["question"] is None
        assert body["seq"] is None

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert [e for e in events if e["kind"] == "follow_up"] == []


def test_follow_up_rejects_mismatched_character_id_with_403_and_records_no_event(
    web_client_with_fake_provider,
):
    provider = FakeProvider(
        complete_value=json.dumps([{"needs_more": True, "question": "..."}])
    )
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-403"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        _complete_all_required_steps(
            client, character_id="hero-1", browser_id="b-hero-1", session_id=session_id
        )
        assert _complete_creation(
            client, character_id="hero-1", browser_id="b-hero-1", session_id=session_id
        ).status_code == 200
        assert client.cookies.get("gptrpg_character") is not None

        response = _follow_up(client, character_id="hero-2", session_id=session_id)
        assert response.status_code == 403

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert [e for e in events if e["kind"] == "follow_up"] == []


def test_wrap_up_records_a_single_creation_gm_spoke_event(web_client_with_fake_provider):
    provider = FakeProvider(complete_value="[]")  # 계약 위반 -> 기본 정리 문구로 폴백
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-wrapup-once"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        _complete_all_required_steps(client, session_id=session_id)
        assert _complete_creation(client, session_id=session_id).status_code == 200

        response = _wrap_up(client, session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["say"]
        assert isinstance(body["seq"], int)
        assert {intro["character_id"] for intro in body["intros"]} == {CHARACTER_ID}

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        wrap_up_events = [event for event in events if event["kind"] == "wrap_up"]
        assert len(wrap_up_events) == 1


def test_wrap_up_called_twice_in_the_same_state_does_not_call_the_provider_again(
    web_client_with_fake_provider,
):
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-wrapup-dedupe"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        _complete_all_required_steps(client, session_id=session_id)
        assert _complete_creation(client, session_id=session_id).status_code == 200

        first = _wrap_up(client, session_id=session_id)
        assert first.status_code == 200
        assert len(provider.calls) == 1

        second = _wrap_up(client, session_id=session_id)
        assert second.status_code == 200
        assert len(provider.calls) == 1

        assert first.json() == second.json()
        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert len([e for e in events if e["kind"] == "wrap_up"]) == 1
