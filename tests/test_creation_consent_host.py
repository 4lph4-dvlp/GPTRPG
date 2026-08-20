"""동의·「아니요」의 재시작 내구성과 방장 잡기·승계를 시험한다(12.3-03).

`tests/test_creation_flow.py`가 이미 동의 관문의 API 동작(잠금 판정·403·
CR-02·부분 재진행)을 시험한다 — 이 파일은 그 위에 12.3-03이 새로 여는
것만 더한다: 사건 기록에서 다시 접은 상태가 재시작에도 살아남는지
(Task 1)와 방장 잡기·승계(Task 2), 그 둘을 화면 API·폴링과 짝짓는 것
(Task 3)이다.

**재시작 재현:** 액터 객체를 새로 만들면 메모리가 비고 사건만 남으므로,
같은 `db_path`로 새 `EventStore` 연결을 열어 `rebuild_state_from_events`를
다시 부르는 것이 "서버를 껐다 켰다"와 같은 조건이다(`_rebuild_state`
참조, `tests/conftest.py::seed_character_created`와 같은 이유로 시험
스레드 전용 새 연결을 연다).
"""

from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.reducer import GameState
from gptrpg.session_actor.projection import rebuild_state_from_events

SESSION_ID = "creation-consent-host-s1"
CHARACTER_ID = "hero-1"
BROWSER_ID = "b-hero-1"
SECOND_CHARACTER_ID = "hero-2"
SECOND_BROWSER_ID = "b-hero-2"


def _fix_party_size(client, *, count: int = 3, session_id: str = SESSION_ID, browser_id: str = ""):
    body = {"player_character_count": count, "rulebook_id": "dungeonworld_like"}
    if browser_id:
        body["browser_id"] = browser_id
    return client.post(f"/api/sessions/{session_id}/creation/party-size", json=body)


def _complete_step(
    client,
    *,
    character_id: str,
    browser_id: str,
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
    character_id: str,
    browser_id: str,
    session_id: str = SESSION_ID,
    name: str = "브람",
):
    """던전월드류 대본 1~5단계(archetype/backstory/ability_array/hp/name)를
    전부 채운다 — `tests/test_creation_flow.py`와 같은 순서."""
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
        response = _complete_step(
            client,
            character_id=character_id,
            browser_id=browser_id,
            session_id=session_id,
            step_id=step_id,
            **payload,
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
    character_id: str,
    browser_id: str,
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


def _consent(
    client,
    *,
    session_id: str = SESSION_ID,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    agree: bool,
    step_id: str | None = None,
):
    body = {"character_id": character_id, "browser_id": browser_id, "agree": agree}
    if step_id is not None:
        body["step_id"] = step_id
    return client.post(f"/api/sessions/{session_id}/creation/consent", json=body)


def _events_of_type(client, event_type: str, *, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert response.status_code == 200
    return [event for event in response.json()["events"] if event["event_type"] == event_type]


def _act_as(client, cookie_value: str) -> None:
    """진짜 그 사람의 서명 쿠키로 (다시) 갈아 끼운다 — `tests/test_creation_flow.py`의
    같은 이름 도우미와 같은 이유(CR-01 뒤에는 `cookies.clear()`만으로는
    다른 사람 행세를 할 수 없다)."""
    client.cookies.clear()
    client.cookies.set("gptrpg_character", cookie_value)


def _rebuild_state(client, session_id: str = SESSION_ID) -> GameState:
    """저장소에 쌓인 사건만으로 상태를 다시 접는다 — "서버를 껐다 켰다"의
    시험 대역이다."""
    store = EventStore(client.app.state.db_path)
    store.initialize()
    try:
        return rebuild_state_from_events(session_id, store.read_events(session_id))
    finally:
        store.close()


# ---------------------------------------------------------------------------
# Task 1 — 동의와 「아니요」가 사건 기록에서만 나오고, 재시작에도 살아남는다
# (D-03). `tests/test_creation_flow.py`가 API 동작(잠금 판정·CR-01/CR-02)을
# 이미 시험하므로, 여기서는 "사건이 실제로 남는가"와 "재시작 재현
# (rebuild_state_from_events)에서도 그대로인가"만 더한다.
# ---------------------------------------------------------------------------


def test_consent_and_lock_survive_a_simulated_restart(web_client):
    client = web_client
    session_id = SESSION_ID + "-restart-lock"
    assert _fix_party_size(client, session_id=session_id).status_code == 200

    _complete_all_required_steps(
        client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id
    )
    assert (
        _complete_creation(
            client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id
        ).status_code
        == 200
    )
    hero1_cookie = client.cookies.get("gptrpg_character")
    client.cookies.clear()

    _complete_all_required_steps(
        client,
        character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        session_id=session_id,
        name="나리",
    )
    assert (
        _complete_creation(
            client,
            character_id=SECOND_CHARACTER_ID,
            browser_id=SECOND_BROWSER_ID,
            session_id=session_id,
        ).status_code
        == 200
    )
    hero2_cookie = client.cookies.get("gptrpg_character")

    # 한 명(hero-1)만 동의한다 — creation_consent_recorded 사건이 하나
    # 생기고 agree가 true다.
    _act_as(client, hero1_cookie)
    first = _consent(
        client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
        agree=True,
    )
    assert first.status_code == 200
    assert first.json()["locked"] is False

    consent_events = _events_of_type(client, "creation_consent_recorded", session_id=session_id)
    assert len(consent_events) == 1
    assert consent_events[0]["character_id"] == CHARACTER_ID
    assert consent_events[0]["agree"] is True

    # 재시작 재현 — 이 시점에서 상태를 다시 접으면 hero-1의 동의가
    # 그대로 남아 있다.
    rebuilt = _rebuild_state(client, session_id)
    assert rebuilt.creation_consents == {CHARACTER_ID: True}
    assert rebuilt.party_roster is None

    # 나머지 한 명(hero-2)도 동의하면 같은 요청 안에서 party_roster_locked
    # 사건이 생기고 응답의 locked가 참이다.
    _act_as(client, hero2_cookie)
    second = _consent(
        client, session_id=session_id, character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID, agree=True,
    )
    assert second.status_code == 200
    assert second.json()["locked"] is True

    locked_events = _events_of_type(client, "party_roster_locked", session_id=session_id)
    assert len(locked_events) == 1
    assert set(locked_events[0]["character_ids"]) == {CHARACTER_ID, SECOND_CHARACTER_ID}

    rebuilt_after_lock = _rebuild_state(client, session_id)
    assert rebuilt_after_lock.party_roster is not None
    assert set(rebuilt_after_lock.party_roster) == {CHARACTER_ID, SECOND_CHARACTER_ID}


def test_disagreeing_reopens_the_step_in_reconstructed_state_and_closes_on_refill(web_client):
    client = web_client
    session_id = SESSION_ID + "-restart-reopen"
    assert _fix_party_size(client, session_id=session_id).status_code == 200

    _complete_all_required_steps(
        client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id
    )
    assert (
        _complete_creation(
            client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id
        ).status_code
        == 200
    )
    hero1_cookie = client.cookies.get("gptrpg_character")

    # 「아니요」 + step_id — creation_consent_recorded 사건이 agree=false·
    # reopened_step_id와 함께 남는다.
    disagree = _consent(
        client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
        agree=False, step_id="backstory",
    )
    assert disagree.status_code == 200
    assert disagree.json()["reopened_step_id"] == "backstory"

    consent_events = _events_of_type(client, "creation_consent_recorded", session_id=session_id)
    assert len(consent_events) == 1
    assert consent_events[0]["agree"] is False
    assert consent_events[0]["reopened_step_id"] == "backstory"

    # 재시작 재현 — 다시 접은 상태에서 creation_consents가 비어 있고
    # reopened_creation_steps에 그 키가 있다.
    rebuilt = _rebuild_state(client, session_id)
    assert rebuilt.creation_consents == {}
    assert (CHARACTER_ID, "backstory") in rebuilt.reopened_creation_steps

    # 다시 열리지 않은 항목(name)을 완성된 캐릭터가 고치려 하면 여전히
    # 409다 — D-07 경계가 안 무너졌다.
    still_locked = _complete_step(
        client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id,
        step_id="name", text_value="브람 4세",
    )
    assert still_locked.status_code == 409

    # 다시 열린 항목(backstory)을 다시 채우면 다시 접은 상태의
    # reopened_creation_steps에서 그 키가 사라진다 — 한 번 다시 채우면
    # 다시 닫힌다.
    refill = _complete_step(
        client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id,
        step_id="backstory", text_value="사실 밤그림자를 쫓는 추적자였다",
    )
    assert refill.status_code == 200

    rebuilt_after_refill = _rebuild_state(client, session_id)
    assert (CHARACTER_ID, "backstory") not in rebuilt_after_refill.reopened_creation_steps

    # 재확정 뒤 캐릭터를 다시 완성할 수 있다(재제출).
    recreate = _complete_creation(
        client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id,
        one_line_intro="브람은 사실 추적자였다.",
    )
    assert recreate.status_code == 200
    _act_as(client, hero1_cookie)  # 신원 확인만 하고 이 이후로는 안 쓴다.


def test_consent_without_any_cookie_is_rejected_and_creates_no_events(web_client):
    """CR-01이 지켜졌는지(신원 없는 요청은 403) — 이 계획이 `_prepare`
    경로로 옮기면서 이 관문을 실수로 느슨하게 만들지 않았는지 확인한다."""
    client = web_client
    session_id = SESSION_ID + "-no-cookie-403"
    assert _fix_party_size(client, session_id=session_id).status_code == 200
    _complete_all_required_steps(
        client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id
    )
    assert (
        _complete_creation(
            client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id
        ).status_code
        == 200
    )
    assert client.cookies.get("gptrpg_character") is not None

    client.cookies.clear()
    response = _consent(
        client, session_id=session_id, character_id=CHARACTER_ID, browser_id=BROWSER_ID,
        agree=True,
    )
    assert response.status_code == 403
    assert not _events_of_type(client, "creation_consent_recorded", session_id=session_id)
