"""`POST /sessions/{session_id}/opening`의 HTTP 종단 시험(SCENE-01, Phase 13)
— 명단이 잠긴 세션에서 오프닝이 판정 없이 `scene_opened` 사건 하나로
남는지, 겹친 호출이 사건 하나로 수렴하는지, 명단이 안 잠긴 세션과 신원
없는 요청이 거부되는지 확인한다.

`tests/conftest.py`의 `lock_creation_roster`(정원만큼 캐릭터를 완성시키고
전원 동의로 명단을 잠그는 조립)와 `web_client_with_fake_provider`를 그대로
쓴다 — `tests/test_creation_screen_tracer.py`의 조립 방식과 같다.

**기존 HTTP 시험 관례를 지킨다** — 브라우저 여럿을 흉내 내는 시험도 각자
순차 `with` 블록으로 연다(중첩하면 액터의 `asyncio.Queue`가 다른 이벤트
루프를 쥐고 교착한다, 08-02 기록).
"""

from conftest import FakeProvider, lock_creation_roster, seed_character_created, select_character

from gptrpg.rulebooks.lamplight_vigil import LAMPLIGHT_VIGIL

SESSION_ID = "scene-opening-s1"


def _opening_events(client, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert response.status_code == 200
    return [event for event in response.json()["events"] if event["event_type"] == "scene_opened"]


def _open(client, character_id: str, session_id: str = SESSION_ID, **overrides):
    body = {"character_id": character_id, "scenario_id": "lamplight_vigil"}
    body.update(overrides)
    return client.post(f"/api/sessions/{session_id}/opening", json=body)


def test_scripted_opening_records_a_single_scene_opened_event_with_the_authors_text(
    web_client_with_fake_provider,
):
    """뼈대 시험 — 세션을 열고, 캐릭터를 만들고, 명단을 잠그고,
    `POST /sessions/{id}/opening`을 `scenario_id="lamplight_vigil"`로 부르고,
    폴링 응답의 `events`에 `scene_opened`가 정확히 하나 있고 그 `text`가
    저자가 쓴 다섯 칸을 그대로 담고 있는지 확인한다."""
    provider = FakeProvider(complete_value="시험용 GM 응답")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        cookies = lock_creation_roster(client, SESSION_ID)
        client.cookies.clear()
        client.cookies.set("gptrpg_character", cookies["hero-1"])

        response = _open(client, "hero-1")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["opened"] is True
        assert body["source"] == "scripted"
        assert isinstance(body["seq"], int)

        events = _opening_events(client)
        assert len(events) == 1
        event = events[0]
        assert event["scenario_id"] == "lamplight_vigil"
        assert event["source"] == "scripted"
        assert event["seq"] == body["seq"]
        assert LAMPLIGHT_VIGIL.opening.hooks[0] in event["text"]
        assert LAMPLIGHT_VIGIL.opening.invitation in event["text"]


def test_calling_opening_twice_in_the_same_session_stays_at_one_event(
    web_client_with_fake_provider,
):
    """같은 세션에서 오프닝을 두 번 부르면 두 번째가 200 + `opened=False`
    이고 `scene_opened` 사건이 여전히 하나임을 확인한다(D-01/D-02/D-03)."""
    provider = FakeProvider(complete_value="시험용 GM 응답")
    session_id = SESSION_ID + "-twice"
    with web_client_with_fake_provider(action_classifier=provider) as client:
        cookies = lock_creation_roster(client, session_id)
        client.cookies.clear()
        client.cookies.set("gptrpg_character", cookies["hero-1"])

        first = _open(client, "hero-1", session_id=session_id)
        assert first.status_code == 200, first.text
        assert first.json()["opened"] is True
        first_seq = first.json()["seq"]

        second = _open(client, "hero-1", session_id=session_id)
        assert second.status_code == 200, second.text
        assert second.json()["opened"] is False
        assert second.json()["seq"] == first_seq

        events = _opening_events(client, session_id=session_id)
        assert len(events) == 1


def test_opening_before_roster_is_locked_is_rejected_and_records_nothing(
    web_client_with_fake_provider,
):
    """명단이 안 잠긴 세션에서 부르면 거부되고 사건이 안 생김을 확인한다
    (D-01 — 「첫 사람이 완성한 순간」이 아니다)."""
    provider = FakeProvider(complete_value="시험용 GM 응답")
    session_id = SESSION_ID + "-unlocked"
    with web_client_with_fake_provider(action_classifier=provider) as client:
        seed_character_created(client.app.state.db_path, session_id, "bram")
        select_character(client, session_id, "bram")

        response = _open(client, "bram", session_id=session_id)
        assert response.status_code == 400, response.text

        assert _opening_events(client, session_id=session_id) == []


def test_opening_without_identity_is_rejected(web_client_with_fake_provider):
    """신원 없이 부르면 403(TRUST-02/D-04, `proceed()`와 같은 검사)."""
    provider = FakeProvider(complete_value="시험용 GM 응답")
    session_id = SESSION_ID + "-no-identity"
    with web_client_with_fake_provider(action_classifier=provider) as client:
        response = _open(client, "ghost", session_id=session_id)
        assert response.status_code == 403


def test_opening_with_unknown_scenario_id_is_rejected(web_client_with_fake_provider):
    """등록되지 않은 `scenario_id`는 400이고 사건이 안 생긴다
    (`get_scenario`의 닫힌 목록 대조, T-13-02)."""
    provider = FakeProvider(complete_value="시험용 GM 응답")
    session_id = SESSION_ID + "-unknown-scenario"
    with web_client_with_fake_provider(action_classifier=provider) as client:
        cookies = lock_creation_roster(client, session_id)
        client.cookies.clear()
        client.cookies.set("gptrpg_character", cookies["hero-1"])

        response = _open(
            client, "hero-1", session_id=session_id, scenario_id="no-such-scenario"
        )
        assert response.status_code == 400, response.text
        assert _opening_events(client, session_id=session_id) == []
