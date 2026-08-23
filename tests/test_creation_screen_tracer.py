"""안내(`announce`)가 사건으로 남고 중복 호출을 서버가 막는지 확인하는
트레이서 시험(12.3-01 Task 2, D-02/D-12).

`tests/test_creation_gm.py`의 `web_client_with_fake_provider` 조립 방식을
그대로 따른다 — `creation_gm` 역할을 따로 등록하지 않으면
`action_classifier` 대역이 그 역할도 대신 받는다(같은 파일 337~345행 선례).
"""

from conftest import FakeProvider

SESSION_ID = "creation-screen-tracer-s1"


from tests.conftest import lock_creation_roster


def _fix_party_size(client, *, count: int = 3, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/party-size",
        json={"player_character_count": count, "rulebook_id": "dungeonworld_like"},
    )


def _announce(client, *, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/announce",
        json={"rulebook_id": "dungeonworld_like"},
    )


def _events_of_type(client, event_type: str, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert response.status_code == 200
    return [event for event in response.json()["events"] if event["event_type"] == event_type]


def test_announce_records_a_single_creation_gm_spoke_event(web_client_with_fake_provider):
    provider = FakeProvider(complete_value="캐릭터 이름과 지난 이야기, 능력치가 필요합니다.")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        assert _fix_party_size(client).status_code == 200

        response = _announce(client)
        assert response.status_code == 200
        body = response.json()
        assert body["message"]
        assert isinstance(body["seq"], int)

        events = _events_of_type(client, "creation_gm_spoke")
        assert len(events) == 1
        assert events[0]["kind"] == "announce"
        assert events[0]["say"]


def test_announce_called_twice_does_not_call_the_provider_again(web_client_with_fake_provider):
    """D-12의 핵심 시험 — 같은 시점에 두 번째로 불려도 사건이 늘지 않고,
    대역 제공자의 호출 횟수도 1에서 늘지 않는다(제공자가 실제로 다시
    불렸는지를 `FakeProvider.calls`로 직접 확인한다)."""
    provider = FakeProvider(complete_value="캐릭터 이름과 지난 이야기, 능력치가 필요합니다.")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        assert _fix_party_size(client).status_code == 200

        first = _announce(client)
        assert first.status_code == 200
        assert len(provider.calls) == 1

        second = _announce(client)
        assert second.status_code == 200
        assert len(provider.calls) == 1  # 다시 부르지 않았다

        assert first.json()["message"] == second.json()["message"]
        assert first.json()["seq"] == second.json()["seq"]

        events = _events_of_type(client, "creation_gm_spoke")
        assert len(events) == 1


def test_events_with_schema_11_creation_events_replay_without_error(web_client_with_fake_provider):
    """인원 확정 → announce → `GET /events`를 `from_seq=0`으로 다시 읽는다.
    `poll_events`가 매 호출마다 `rebuild_state_from_events`로 전체를 다시
    접으므로(`routes_events.py`), 이 호출이 200으로 끝나는 것 자체가 판 11
    사건이 섞인 기록을 예외 없이 접을 수 있다는 증거다."""
    provider = FakeProvider(complete_value="캐릭터 이름과 지난 이야기가 필요합니다.")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        assert _fix_party_size(client).status_code == 200
        assert _announce(client).status_code == 200

        response = client.get(f"/api/sessions/{SESSION_ID}/events", params={"from_seq": 0})
        assert response.status_code == 200
        event_types = {event["event_type"] for event in response.json()["events"]}
        assert "party_size_fixed" in event_types
        assert "creation_gm_spoke" in event_types


def test_announce_returns_409_after_roster_is_locked(web_client_with_fake_provider):
    """명단이 잠긴 세션에서 `announce`는 409이고, 서버가 이미 쓰는 한국어
    문장을 그대로 낸다(D-15의 서버 쪽 근거)."""
    provider = FakeProvider(complete_value="[]")
    session_id = SESSION_ID + "-locked"
    with web_client_with_fake_provider(action_classifier=provider) as client:
        # G-12.3-11 뒤로는 정한 인원이 전부 완성하고 동의해야 잠긴다 —
        # 그 조립은 conftest에 한 번만 적혀 있다.
        lock_creation_roster(client, session_id)

        response = _announce(client, session_id=session_id)
        assert response.status_code == 409
        assert response.json()["detail"] == "파티 명단이 이미 잠겼다"
