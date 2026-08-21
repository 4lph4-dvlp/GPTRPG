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

import json
import time

from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.reducer import GameState
from gptrpg.session_actor.projection import rebuild_state_from_events
from gptrpg.web import creation_state

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


def _poll_state(client, *, session_id: str = SESSION_ID) -> dict:
    """`tests/test_creation_screen_state.py`의 같은 이름 도우미와 같은
    모양 — 폴링 응답의 `state` 칸만 돌려준다."""
    response = client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert response.status_code == 200
    return response.json()["state"]


def _act_as(client, cookie_value: str) -> None:
    """진짜 그 사람의 서명 쿠키로 (다시) 갈아 끼운다 — `tests/test_creation_flow.py`의
    같은 이름 도우미와 같은 이유(CR-01 뒤에는 `cookies.clear()`만으로는
    다른 사람 행세를 할 수 없다)."""
    client.cookies.clear()
    client.cookies.set("gptrpg_character", cookie_value)


def _claim_host(client, browser_id: str, *, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/host", json={"browser_id": browser_id}
    )


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


def test_one_persons_reopen_clears_every_other_characters_consent_in_the_polled_state(
    web_client,
):
    """D-03/D-11 교차 전파의 서버 쪽 절반(Phase 12.3-08, 3차 검증이 QA
    도구의 구조적 제약으로 확인하지 못한 항목) — 한 사람의 재오픈이
    `creation_consent_recorded(agree=False)`의 `creation_consents={}`
    (`reducer.py:546~563`)로 세션 전체의 동의를 통째로 비우고, 그 값이
    폴링 응답 하나로 두 사람 화면 모두에 나간다.

    **이 시험이 증명하는 것:** 재오픈 하나가 다른 캐릭터의 동의 표시
    까지 서버 상태에서 되돌리고, 그 값이 폴링으로 모두에게 나가는
    **배선**. **증명하지 못하는 것:** 먼저 동의한 사람의 **화면**에
    그것이 실제로 그려지는가 — 그것은 실제로 서로 다른 브라우저 둘이
    필요해 사람 확인 목록에 남는다(12.3-VERIFICATION.md
    `behavior_unverified_items`, 단일 크로미움 프로필은 쿠키·브라우저
    저장소를 탭 전체에 전역 공유해 두 사람이 동시에 각자 유효한 인증
    상태를 갖는 상황 자체를 만들 수 없다). **이 시험을 그 사람 확인
    항목의 대체물로 부르지 않는다.**
    """
    client = web_client
    session_id = SESSION_ID + "-cross-consent-reopen"
    assert _fix_party_size(client, session_id=session_id).status_code == 200

    # 세 번째 참가자가 아직 한창 만드는 중이면(CR-02, `_all_created_
    # characters_consented`) 완성된 둘이 동의해도 명단이 자동으로 안
    # 잠긴다 — 재오픈을 걸 수 있는 창을 만든다. 이 참가자 자체는 이
    # 시험이 확인하는 교차 전파와 무관하다.
    third_character_id = "hero-3"
    third_browser_id = "b-hero-3"
    assert (
        _complete_step(
            client,
            character_id=third_character_id,
            browser_id=third_browser_id,
            session_id=session_id,
            step_id="archetype",
            picked=["몸으로 먼저 막아선다"],
        ).status_code
        == 200
    )

    _complete_all_required_steps(
        client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id
    )
    assert (
        _complete_creation(
            client, character_id=CHARACTER_ID, browser_id=BROWSER_ID, session_id=session_id
        ).status_code
        == 200
    )
    first_cookie = client.cookies.get("gptrpg_character")
    client.cookies.clear()  # 두 번째 캐릭터의 항목 제출이 첫 번째 사람의 쿠키와 안 부딪히게 한다.

    _complete_all_required_steps(
        client,
        character_id=SECOND_CHARACTER_ID,
        browser_id=SECOND_BROWSER_ID,
        session_id=session_id,
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
    second_cookie = client.cookies.get("gptrpg_character")

    _act_as(client, first_cookie)
    assert (
        _consent(
            client,
            session_id=session_id,
            character_id=CHARACTER_ID,
            browser_id=BROWSER_ID,
            agree=True,
        ).status_code
        == 200
    )
    _act_as(client, second_cookie)
    assert (
        _consent(
            client,
            session_id=session_id,
            character_id=SECOND_CHARACTER_ID,
            browser_id=SECOND_BROWSER_ID,
            agree=True,
        ).status_code
        == 200
    )

    state = _poll_state(client, session_id=session_id)
    consented = {c["character_id"]: c["consented"] for c in state["creation_characters"]}
    assert consented[CHARACTER_ID] is True
    assert consented[SECOND_CHARACTER_ID] is True

    # 첫 번째 사람이 자기 항목 하나를 재오픈한다.
    _act_as(client, first_cookie)
    reopen = _consent(
        client,
        session_id=session_id,
        character_id=CHARACTER_ID,
        browser_id=BROWSER_ID,
        agree=False,
        step_id="backstory",
    )
    assert reopen.status_code == 200
    assert reopen.json()["reopened_step_id"] == "backstory"

    # 핵심 단언 — 재오픈 뒤의 폴링 응답에서 두 번째 사람의 동의도
    # False로 되돌아간다.
    state = _poll_state(client, session_id=session_id)
    consented = {c["character_id"]: c["consented"] for c in state["creation_characters"]}
    assert consented[CHARACTER_ID] is False
    assert consented[SECOND_CHARACTER_ID] is False

    disagree_events = [
        e
        for e in _events_of_type(client, "creation_consent_recorded", session_id=session_id)
        if e["agree"] is False
    ]
    assert len(disagree_events) == 1
    assert disagree_events[0]["reopened_step_id"] == "backstory"

    # 서버를 재시작해도 이 초기화가 남는다.
    rebuilt = _rebuild_state(client, session_id)
    assert rebuilt.creation_consents == {}


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


# ---------------------------------------------------------------------------
# Task 2 — 방장을 만든다: 가장 먼저 들어온 사람, 조용해지면 승계 (D-11).
# ---------------------------------------------------------------------------


def test_first_host_claim_records_event_and_returns_you_are_host_true(web_client):
    client = web_client
    session_id = SESSION_ID + "-host-first"

    response = _claim_host(client, "browser-a", session_id=session_id)
    assert response.status_code == 200
    body = response.json()
    assert body["you_are_host"] is True
    assert body["host_claimed"] is True
    assert body["changed"] is True

    events = _events_of_type(client, "creation_host_claimed", session_id=session_id)
    assert len(events) == 1
    assert events[0]["reason"] == "first"
    # `GET /events`가 돌려주는 events 목록은 browser_id를 가린다(T-12.3-05,
    # CR-03) — 저장소 원본에는 남아 있지만 폴링 응답에는 안 실린다.
    assert events[0]["browser_id"] == ""
    assert events[0]["previous_browser_id"] is None


def test_same_browser_claiming_again_records_no_new_event(web_client):
    client = web_client
    session_id = SESSION_ID + "-host-same"

    assert _claim_host(client, "browser-a", session_id=session_id).status_code == 200
    second = _claim_host(client, "browser-a", session_id=session_id)
    assert second.status_code == 200
    assert second.json()["you_are_host"] is True
    assert second.json()["changed"] is False

    events = _events_of_type(client, "creation_host_claimed", session_id=session_id)
    assert len(events) == 1


def test_a_different_browser_claiming_immediately_is_not_host_and_records_no_event(web_client):
    client = web_client
    session_id = SESSION_ID + "-host-second-immediate"

    assert _claim_host(client, "browser-a", session_id=session_id).status_code == 200
    second = _claim_host(client, "browser-b", session_id=session_id)
    assert second.status_code == 200
    assert second.json()["you_are_host"] is False
    assert second.json()["host_claimed"] is True
    assert second.json()["changed"] is False

    events = _events_of_type(client, "creation_host_claimed", session_id=session_id)
    assert len(events) == 1  # 여전히 browser-a의 첫 선점 하나뿐


def test_idle_host_is_succeeded_by_another_browser_and_cannot_reclaim(web_client):
    """방장이 유휴로 판정되면 다른 브라우저가 이어받고, 옛 방장은 다시
    불러도 방장을 도로 뺏지 못한다."""
    client = web_client
    session_id = SESSION_ID + "-host-succession"

    assert _claim_host(client, "browser-a", session_id=session_id).status_code == 200

    # 시험에서 재실 표를 직접 조작해 browser-a를 유휴로 만든다.
    creation_state._browser_last_seen[(session_id, "browser-a")] = (
        time.monotonic() - creation_state.HOST_IDLE_S - 5
    )

    succession = _claim_host(client, "browser-b", session_id=session_id)
    assert succession.status_code == 200
    assert succession.json()["you_are_host"] is True
    assert succession.json()["changed"] is True

    events = _events_of_type(client, "creation_host_claimed", session_id=session_id)
    assert len(events) == 2
    assert events[1]["reason"] == "succession"
    # 승계 사건도 첫 선점과 같은 이유로 browser_id/previous_browser_id가
    # 가려진다(T-12.3-05, CR-03) — 옛 방장의 식별자도 남의 것이다.
    assert events[1]["browser_id"] == ""
    assert events[1]["previous_browser_id"] is None

    # 옛 방장(browser-a)이 다시 불러도 방장을 도로 뺏지 못한다.
    reclaim = _claim_host(client, "browser-a", session_id=session_id)
    assert reclaim.status_code == 200
    assert reclaim.json()["you_are_host"] is False
    assert reclaim.json()["changed"] is False
    assert len(_events_of_type(client, "creation_host_claimed", session_id=session_id)) == 2


def test_non_host_browser_cannot_fix_party_size_and_records_no_event(web_client):
    client = web_client
    session_id = SESSION_ID + "-host-gate-403"

    assert _claim_host(client, "browser-a", session_id=session_id).status_code == 200

    response = _fix_party_size(client, session_id=session_id, browser_id="browser-b")
    assert response.status_code == 403
    assert not _events_of_type(client, "party_size_fixed", session_id=session_id)


def test_host_browser_can_fix_party_size(web_client):
    client = web_client
    session_id = SESSION_ID + "-host-gate-ok"

    assert _claim_host(client, "browser-a", session_id=session_id).status_code == 200
    response = _fix_party_size(client, session_id=session_id, browser_id="browser-a")
    assert response.status_code == 200


def test_party_size_without_any_host_still_succeeds(web_client):
    """방장이 없는 세션의 인원 확정은 여전히 통과한다 — 화면이 없는
    호출부(시험·스크립트)를 막지 않는다."""
    client = web_client
    session_id = SESSION_ID + "-host-none-ok"

    response = _fix_party_size(client, session_id=session_id)
    assert response.status_code == 200


def test_host_response_never_leaks_a_browser_id(web_client):
    """`CreationHostResponse`의 어느 칸에도 `browser_id` 값이 없다
    (T-12.3-05) — 응답 JSON을 통째로 훑어 실제 값이 어디에도 안 새는지
    확인한다."""
    client = web_client
    session_id = SESSION_ID + "-host-no-leak"

    response = _claim_host(client, "the-secret-browser-id", session_id=session_id)
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"you_are_host", "host_claimed", "changed"}
    assert "the-secret-browser-id" not in response.text


def test_events_array_never_leaks_a_browser_id_from_creation_host_claimed(web_client):
    """12.3-REVIEW.md CR-03 — `GET /events`의 `events` 배열 전체를 훑어
    `creation_host_claimed`의 `browser_id`/`previous_browser_id`가 안
    새는지 확인한다. `test_host_response_never_leaks_a_browser_id`는 POST
    응답만, `test_claiming_host_makes_creation_host_claimed_true_with_no_identifier`
    는 `state` 칸만 겨눴다 — 이 시험이 CR-03이 실제로 겨눈 자리(events
    목록)다."""
    client = web_client
    session_id = SESSION_ID + "-events-leak"

    assert _claim_host(client, "the-secret-host-id", session_id=session_id).status_code == 200
    # 승계까지 일으켜 previous_browser_id도 채운다.
    creation_state._browser_last_seen[(session_id, "the-secret-host-id")] = (
        time.monotonic() - creation_state.HOST_IDLE_S - 5
    )
    assert _claim_host(
        client, "the-second-secret-id", session_id=session_id
    ).status_code == 200

    response = client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert response.status_code == 200
    assert "the-secret-host-id" not in response.text
    assert "the-second-secret-id" not in response.text

    events = _events_of_type(client, "creation_host_claimed", session_id=session_id)
    assert len(events) == 2
    for event in events:
        assert event["browser_id"] == ""
        assert event["previous_browser_id"] is None


def test_a_browser_cannot_read_the_host_id_from_polling_and_replay_it_to_fix_party_size(
    web_client,
):
    """12.3-REVIEW.md CR-03 — 실제 공격 경로가 닫혔는지 끝까지 확인한다.
    `browser-b`는 방장이 아니다. 이전에는 `GET /events`의 `events` 배열에서
    방장의 `browser_id`를 평문으로 읽어 `/creation/party-size`에 그대로
    실으면 방장 전용 조작(인원 확정)을 통과했다 — 이 시험은 그 값이 이제
    응답 어디에도 없으므로 재현조차 불가능함을 보인다: 폴링 응답에서
    읽을 수 있는 값은 빈 문자열뿐이고, 그 값으로 시도하면 403이다."""
    client = web_client
    session_id = SESSION_ID + "-impersonation"

    assert _claim_host(client, "browser-a", session_id=session_id).status_code == 200

    leaked = client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert leaked.status_code == 200
    host_claimed = [
        event for event in leaked.json()["events"] if event["event_type"] == "creation_host_claimed"
    ]
    assert len(host_claimed) == 1
    stolen_browser_id = host_claimed[0]["browser_id"]
    assert stolen_browser_id == ""  # 훔칠 값 자체가 없다

    replay = _fix_party_size(client, session_id=session_id, browser_id=stolen_browser_id)
    assert replay.status_code == 403
    assert not _events_of_type(client, "party_size_fixed", session_id=session_id)


# ---------------------------------------------------------------------------
# Task 3 — 동의·방장 경로가 폴링과 짝지어진다.
# ---------------------------------------------------------------------------


def test_claiming_host_makes_creation_host_claimed_true_with_no_identifier(web_client):
    """방장을 잡으면 `state.creation_host_claimed`가 참이 되고, 그
    응답에는 여전히 방장의 식별자가 없다(T-12.3-05)."""
    client = web_client
    session_id = SESSION_ID + "-poll-host-claimed"

    before = client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert before.status_code == 200
    assert before.json()["state"]["creation_host_claimed"] is False

    assert _claim_host(client, "browser-poll", session_id=session_id).status_code == 200

    after = client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert after.status_code == 200
    body = after.json()
    state = body["state"]
    assert state["creation_host_claimed"] is True
    # state 칸에는 여부만 있다 — 식별자는 어느 state 키에도 없다(T-12.3-05).
    assert "browser-poll" not in json.dumps(state)
    # **events 목록도 마찬가지다(12.3-REVIEW.md CR-03 수정).** 이전에는
    # 이 검사 범위를 state 칸으로만 좁혔다(12.3-03-SUMMARY.md의 스코프
    # 축소 — "사건 기록에는 신원 감사를 위해 browser_id가 정당하게
    # 남는다"는 전제였다) — 하지만 이 응답의 events 목록은 모든 폴링
    # 브라우저에게 공개되고, `/creation/party-size`의 방장 관문
    # (`routes_creation.py::fix_party_size`)이 `body.browser_id`를 그대로
    # 문자열 비교하므로, events 목록에 남은 browser_id는 곧 방장 전용
    # 조작을 통과시키는 열쇠였다. 그 전제가 틀렸다 — events 목록도 절대
    # 새면 안 된다.
    assert "browser-poll" not in json.dumps(body["events"])


def test_a_restart_of_the_liveness_table_does_not_let_a_stranger_ambush_the_host(web_client):
    """T-12.3-13 — 재실 표는 프로세스 메모리라 서버가 재시작하면 빈다.
    `GameState`(사건에서 다시 접은 값)의 방장은 그대로인데 재실 표만
    비었을 때, 다른 브라우저가 곧바로 부르면 애먼 승계가 아니라
    「지금 본 것으로만 기록」하고 넘어가야 한다."""
    client = web_client
    session_id = SESSION_ID + "-host-liveness-restart"

    assert _claim_host(client, "browser-a", session_id=session_id).status_code == 200

    # 프로세스 재시작 재현 — 재실 표만 통째로 지운다(GameState는 사건에서
    # 다시 접히므로 방장은 그대로 "browser-a"다).
    creation_state._browser_last_seen.pop((session_id, "browser-a"), None)

    ambush = _claim_host(client, "browser-b", session_id=session_id)
    assert ambush.status_code == 200
    assert ambush.json()["you_are_host"] is False
    assert ambush.json()["changed"] is False
    assert len(_events_of_type(client, "creation_host_claimed", session_id=session_id)) == 1

    # 이번 호출이 browser-a를 "지금 본 것"으로 기록했으므로, 곧바로 또
    # 부른다고 승계되지 않는다 — HOST_IDLE_S가 다시 지나야 한다.
    second_ambush = _claim_host(client, "browser-b", session_id=session_id)
    assert second_ambush.status_code == 200
    assert second_ambush.json()["you_are_host"] is False
    assert len(_events_of_type(client, "creation_host_claimed", session_id=session_id)) == 1
