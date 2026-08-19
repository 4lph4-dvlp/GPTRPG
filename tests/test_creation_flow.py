"""자기소개 자리를 끝까지 닫는 시험 — 자기 차례 되돌리기(D-07) · 끼어들기
(D-09) · GM 정리와 한 줄 소개(CHAR-03/D-10) · 동의 관문과 부분 재진행
(D-11) · 전원 동의 순간의 명단 잠금 (Phase 12.1-04).

`tests/test_creation_tracer.py`(12.1-01)의 `TestClient` 조립 방식과
`tests/test_creation_gm.py`(12.1-03)의 가짜 제공자 조립 방식을 그대로
따른다. 던전월드류 대본 다섯 단계(archetype/backstory/ability_array/hp/
name)를 채우는 도우미는 `tests/test_creation_gm.py`의
`_complete_all_required_steps`와 같은 순서다.
"""

import json

from gptrpg.rules_core.reducer import fold

SESSION_ID = "creation-flow-s1"
CHARACTER_ID = "hero-1"
BROWSER_ID = "b-hero-1"
SECOND_CHARACTER_ID = "hero-2"
SECOND_BROWSER_ID = "b-hero-2"


def _fix_party_size(client, *, count: int = 3, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/party-size",
        json={"player_character_count": count, "rulebook_id": "dungeonworld_like"},
    )


def _complete_step(
    client,
    *,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    session_id: str = SESSION_ID,
    step_id: str = "name",
    **overrides,
):
    body = {
        "character_id": character_id,
        "browser_id": browser_id,
        "step_id": step_id,
        "rulebook_id": "dungeonworld_like",
        "text_value": "브람" if step_id == "name" else None,
    }
    body.update(overrides)
    return client.post(f"/api/sessions/{session_id}/creation/step", json=body)


def _complete_all_required_steps(
    client,
    *,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    session_id: str = SESSION_ID,
    name: str = "브람",
):
    """던전월드류 대본 1~5단계(archetype/backstory/ability_array/hp/name)를
    전부 채운다 — `/creation/complete`가 요구하는 필수 항목 최소선이다."""
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
        response = client.post(
            f"/api/sessions/{session_id}/creation/step",
            json={
                "character_id": character_id,
                "browser_id": browser_id,
                "step_id": step_id,
                "rulebook_id": "dungeonworld_like",
                **payload,
            },
        )
        assert response.status_code == 200, response.text
    assert (
        _complete_step(
            client,
            character_id=character_id,
            browser_id=browser_id,
            session_id=session_id,
            step_id="name",
            text_value=name,
        ).status_code
        == 200
    )


def _complete_creation(
    client,
    *,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    session_id: str = SESSION_ID,
    one_line_intro: str | None = None,
):
    return client.post(
        f"/api/sessions/{session_id}/creation/complete",
        json={
            "character_id": character_id,
            "browser_id": browser_id,
            "rulebook_id": "dungeonworld_like",
            "one_line_intro": one_line_intro or f"{character_id}는 조용한 마을을 떠나온 모험가다.",
        },
    )


def _interject(
    client,
    *,
    session_id: str = SESSION_ID,
    speaker_character_id: str,
    browser_id: str,
    during_character_id: str,
    mentioned_character_ids: tuple[str, ...] = (),
    text: str = "안녕하세요, 같이 가시죠",
):
    return client.post(
        f"/api/sessions/{session_id}/creation/interject",
        json={
            "speaker_character_id": speaker_character_id,
            "browser_id": browser_id,
            "during_character_id": during_character_id,
            "mentioned_character_ids": list(mentioned_character_ids),
            "text": text,
        },
    )


def _events_of_type(client, event_type: str, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events")
    assert response.status_code == 200
    return [event for event in response.json()["events"] if event["event_type"] == event_type]


# ---------------------------------------------------------------------------
# Task 1 — 자기 차례 되돌리기(D-07)와 끼어들기(D-09)
# ---------------------------------------------------------------------------


def test_rewinding_the_same_step_within_the_turn_supersedes_the_earlier_value(web_client):
    """D-07 — 자기 차례 안에서는 같은 항목을 몇 번이든 다시 확정할 수
    있고, 접은 결과에서는 나중 값이 이기며 앞선 사건은 지워지지 않는다."""
    client = web_client
    session_id = SESSION_ID + "-rewind"
    assert _fix_party_size(client, session_id=session_id).status_code == 200

    first = _complete_step(client, session_id=session_id, step_id="name", text_value="브람")
    assert first.status_code == 200
    second = _complete_step(
        client, session_id=session_id, step_id="name", text_value="브람 2세"
    )
    assert second.status_code == 200

    step_events = _events_of_type(client, "creation_step_completed", session_id=session_id)
    assert len(step_events) == 2
    assert step_events[0]["superseded_seq"] is None
    assert step_events[1]["superseded_seq"] == step_events[0]["seq"]


def test_completing_a_step_after_the_turn_ended_is_rejected(web_client):
    """D-07 경계 — 차례가 끝나면(character_created가 기록되면) 그 사람
    몫은 확정된다. 정리 뒤 동의 관문(D-11)에서 말해야 한다."""
    client = web_client
    session_id = SESSION_ID + "-turn-ended"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    _complete_all_required_steps(client, session_id=session_id)
    assert _complete_creation(client, session_id=session_id).status_code == 200

    response = _complete_step(
        client, session_id=session_id, step_id="name", text_value="브람 3세"
    )
    assert response.status_code == 409


def test_interjection_is_recorded_with_speaker_and_mentioned(web_client):
    """D-09 — 끼어든 말이 화자·언급 대상과 함께 사건으로 남는다."""
    client = web_client
    session_id = SESSION_ID + "-interject-basic"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    assert _complete_step(client, session_id=session_id, step_id="name").status_code == 200

    response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        during_character_id=CHARACTER_ID,
        mentioned_character_ids=(CHARACTER_ID,),
        text="저도 그 마을 출신이에요",
    )
    assert response.status_code == 200

    events = _events_of_type(client, "creation_interjection", session_id=session_id)
    assert len(events) == 1
    assert events[0]["speaker_character_id"] == SECOND_CHARACTER_ID
    assert events[0]["during_character_id"] == CHARACTER_ID
    assert events[0]["mentioned_character_ids"] == [CHARACTER_ID]


def test_interjection_during_own_turn_is_rejected(web_client):
    """D-09 — 자기 차례에는 끼어드는 것이 아니라 말하는 것이다."""
    client = web_client
    session_id = SESSION_ID + "-interject-own-turn"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    assert _complete_step(client, session_id=session_id, step_id="name").status_code == 200

    response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=CHARACTER_ID,
        browser_id=BROWSER_ID,
        during_character_id=CHARACTER_ID,
    )
    assert response.status_code == 409


def test_interjection_mentioning_an_unknown_character_is_rejected(web_client):
    """D-09 — 이 세션에 없는 사람을 가리키는 기록을 남기지 않는다."""
    client = web_client
    session_id = SESSION_ID + "-interject-unknown"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    assert _complete_step(client, session_id=session_id, step_id="name").status_code == 200

    response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        during_character_id=CHARACTER_ID,
        mentioned_character_ids=("ghost",),
    )
    assert response.status_code == 409


def test_interjection_never_changes_creation_step_completed_or_character_created_counts(
    web_client,
):
    """D-09 결정 — 끼어든 말이 어느 캐릭터의 `creation_step_values`도
    `created_characters`도 바꾸지 않는다. `creation_step_completed`/
    `character_created`가 이 두 파생 칸을 채우는 유일한 사건 종류이므로
    (rules_core.reducer), 끼어들기 전후로 그 사건들의 개수가 그대로라는
    것이 상태 불변의 직접 증거다. (`GET /characters`는 아직 정적 목록만
    읽으므로(12.1-01 알려진 한계) 이 세션 스코프 캐릭터를 비추지 못한다
    — 12.1-05가 옮기기 전까지는 사건 개수 검사가 더 정확하다.)
    """
    client = web_client
    session_id = SESSION_ID + "-interject-no-side-effect"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    _complete_all_required_steps(client, session_id=session_id)

    step_events_before = len(
        _events_of_type(client, "creation_step_completed", session_id=session_id)
    )
    created_events_before = len(
        _events_of_type(client, "character_created", session_id=session_id)
    )

    response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        during_character_id=CHARACTER_ID,
        mentioned_character_ids=(CHARACTER_ID,),
        text="이 마을 잘 아시나요?",
    )
    assert response.status_code == 200

    step_events_after = len(
        _events_of_type(client, "creation_step_completed", session_id=session_id)
    )
    created_events_after = len(
        _events_of_type(client, "character_created", session_id=session_id)
    )
    assert step_events_after == step_events_before
    assert created_events_after == created_events_before


def test_interjection_with_someone_elses_speaker_character_id_is_rejected(web_client):
    """신원 대조 — 이미 쿠키를 든 브라우저가 다른 캐릭터인 척 끼어들 수
    없다."""
    client = web_client
    session_id = SESSION_ID + "-interject-403"
    assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200
    _complete_all_required_steps(client, session_id=session_id)
    assert _complete_creation(client, session_id=session_id).status_code == 200
    assert client.cookies.get("gptrpg_character") is not None

    response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        during_character_id=CHARACTER_ID,
    )
    assert response.status_code == 403


def test_creation_step_with_someone_elses_character_id_is_rejected(web_client):
    """T-12.1-01 재확인 — `POST /creation/step`이 남의 character_id로 오면
    403이다."""
    client = web_client
    session_id = SESSION_ID + "-step-403"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    _complete_all_required_steps(client, session_id=session_id)
    assert _complete_creation(client, session_id=session_id).status_code == 200

    response = _complete_step(
        client,
        session_id=session_id,
        character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        step_id="name",
        text_value="나리",
    )
    assert response.status_code == 403


def test_interject_and_complete_after_roster_locked_are_both_rejected(web_client):
    """명단이 잠긴 뒤 되돌리기·끼어들기 둘 다 `RosterAlreadyLocked`다."""
    client = web_client
    session_id = SESSION_ID + "-interject-locked"
    assert _fix_party_size(client, count=3, session_id=session_id).status_code == 200
    _complete_all_required_steps(client, session_id=session_id)
    assert _complete_creation(client, session_id=session_id).status_code == 200
    lock_response = client.post(
        f"/api/sessions/{session_id}/creation/lock-roster",
        json={"character_ids": [CHARACTER_ID]},
    )
    assert lock_response.status_code == 200
    assert _events_of_type(client, "party_roster_locked", session_id=session_id)

    client.cookies.clear()
    interject_response = _interject(
        client,
        session_id=session_id,
        speaker_character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        during_character_id=CHARACTER_ID,
    )
    assert interject_response.status_code == 409

    step_response = _complete_step(
        client,
        session_id=session_id,
        character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        step_id="name",
        text_value="나리",
    )
    assert step_response.status_code == 409
