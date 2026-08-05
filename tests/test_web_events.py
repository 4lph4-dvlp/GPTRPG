"""`GET /api/sessions/{session_id}/events` 폴링 엔드포인트 시험 (04-01).

<behavior>의 여섯 항목을 하나씩 검증한다. 사건을 미리 넣어야 하는 시험은
`tmp_db_path`에 `EventStore`로 직접 append해서 준비한다
(`tests/test_reducer_failure_count.py`가 payload 사전을 직접 만드는 방식과
같은 결). `TestClient`는 부르는 쪽이 동기라 `pytest-asyncio`가 필요 없다.
"""

from pathlib import Path

from fastapi.testclient import TestClient

from gptrpg.event_log.schema import (
    ActionDeclared,
    CheckResolved,
    EVENT_SCHEMA_VERSION,
    ModifierRecord,
    utc_now_iso,
)
from gptrpg.event_log.store import EventStore
from gptrpg.session_actor.actor import AUTO_ADVANCE_FAILURE_THRESHOLD


def _declared(session_id: str, seq: int, text: str) -> ActionDeclared:
    return ActionDeclared(
        event_type="action_declared",
        player_id="p1",
        raw_text=text,
        session_id=session_id,
        seq=seq,
        schema_version=EVENT_SCHEMA_VERSION,
        recorded_at=utc_now_iso(),
    )


def _seed_events(db_path: Path, session_id: str, count: int) -> None:
    store = EventStore(db_path)
    store.initialize()
    for seq in range(count):
        store.append(_declared(session_id, seq, f"행동 {seq}"))
    store.close()


def test_from_seq_boundary_is_inclusive(tmp_db_path: Path, web_client: TestClient) -> None:
    """`from_seq=3`은 seq 3 이상인 사건만, seq 3을 포함해서 돌려준다."""
    _seed_events(tmp_db_path, "s1", count=6)

    response = web_client.get("/api/sessions/s1/events", params={"from_seq": 3})

    assert response.status_code == 200
    body = response.json()
    seqs = [event["seq"] for event in body["events"]]
    assert seqs == [3, 4, 5], "seq==from_seq인 사건(3)이 결과에 들어 있어야 한다 — 경계는 포함"


def test_from_seq_zero_returns_full_history(tmp_db_path: Path, web_client: TestClient) -> None:
    """`from_seq=0`은 세션 전체 역사를 돌려준다 — 재접속에 쓰는 값이 이것 하나뿐이다."""
    _seed_events(tmp_db_path, "s1", count=5)

    response = web_client.get("/api/sessions/s1/events", params={"from_seq": 0})

    assert response.status_code == 200
    body = response.json()
    seqs = [event["seq"] for event in body["events"]]
    assert seqs == [0, 1, 2, 3, 4]


def test_negative_from_seq_rejected_with_422(web_client: TestClient) -> None:
    """`from_seq`가 음수면 422로 거절한다."""
    response = web_client.get("/api/sessions/s1/events", params={"from_seq": -1})

    assert response.status_code == 422


def test_path_traversal_session_id_rejected_with_400(web_client: TestClient) -> None:
    """`session_id`가 `[A-Za-z0-9_-]{1,64}`를 벗어나면(상위 경로를 가리키는 값) 400으로 거절한다.

    순수 `..` 세그먼트는 RFC 3986 dot-segment 정규화 규칙에 따라 HTTP 클라이언트가
    보내기 전에 지워 버리므로(따라서 서버에 아예 도달하지 못해 404가 난다), 완전한
    세그먼트가 정확히 `.`/`..`가 아닌 값(점이 다른 글자와 섞인 값)으로 확인한다 —
    그래도 여전히 `SAFE_SESSION_ID` 정규식이 거부해야 하는 값이다.
    """
    response = web_client.get("/api/sessions/..escape/events")

    assert response.status_code == 400


def test_state_matches_rebuild_state(tmp_db_path: Path, web_client: TestClient) -> None:
    """응답의 `state` 칸은 `rebuild_state`가 돌려주는 `GameState`와 칸마다 같은 값이다."""
    from gptrpg.session_actor.projection import rebuild_state

    _seed_events(tmp_db_path, "s1", count=4)

    response = web_client.get("/api/sessions/s1/events", params={"from_seq": 0})
    assert response.status_code == 200
    state = response.json()["state"]

    store = EventStore(tmp_db_path)
    store.initialize()
    expected = rebuild_state(store, "s1")
    store.close()

    assert state["session_id"] == expected.session_id
    assert state["last_seq"] == expected.last_seq
    assert state["turn_count"] == expected.turn_count
    assert state["check_count"] == expected.check_count
    assert state["failure_count"] == expected.failure_count
    assert state["clock_segment"] == expected.clock_segment
    assert state["clock_advances"] == expected.clock_advances
    assert state["narration_count"] == expected.narration_count
    assert state["ai_calls"] == expected.ai_calls
    assert state["total_tokens"] == expected.total_tokens
    assert state["last_grade"] == expected.last_grade


def test_empty_session_returns_200_with_empty_list_and_initial_state(
    web_client: TestClient,
) -> None:
    """사건이 하나도 없는 세션도 200과 빈 목록 + 초기 `state`를 돌려준다 (404가 아니다)."""
    response = web_client.get("/api/sessions/never-seen/events", params={"from_seq": 0})

    assert response.status_code == 200
    body = response.json()
    assert body["events"] == []
    assert body["state"]["session_id"] == "never-seen"
    assert body["state"]["last_seq"] == -1
    assert body["state"]["turn_count"] == 0


def _failed_check(session_id: str, seq: int) -> CheckResolved:
    return CheckResolved(
        event_type="check_resolved",
        move="문을 부순다",
        rolls=[1, 1],
        modifiers=[ModifierRecord(type="flat", value=0, source="없음")],
        target=10,
        grade="miss",
        counts_as_failure=True,
        session_id=session_id,
        seq=seq,
        schema_version=EVENT_SCHEMA_VERSION,
        recorded_at=utc_now_iso(),
    )


def test_poll_response_state_has_fails_since_clock_matching_failure_count(
    tmp_db_path: Path, web_client: TestClient
) -> None:
    """실패 두 번이 기록된 세션의 폴링 응답에서 state.fails_since_clock == 2이고
    state.failure_count == 2다 — 시계가 아직 안 돌았으니 두 값이 같다."""
    store = EventStore(tmp_db_path)
    store.initialize()
    for seq in range(2):
        store.append(_failed_check("s1", seq))
    store.close()

    response = web_client.get("/api/sessions/s1/events", params={"from_seq": 0})

    assert response.status_code == 200
    state = response.json()["state"]
    assert state["fails_since_clock"] == 2
    assert state["failure_count"] == 2


def test_poll_response_auto_advance_threshold_matches_actor_constant(
    web_client: TestClient,
) -> None:
    """state.auto_advance_threshold == 3이고, 이 값이
    session_actor.actor.AUTO_ADVANCE_FAILURE_THRESHOLD를 import해 비교했을 때
    같다 (문턱값이 두 자리에 따로 적히지 않는다)."""
    response = web_client.get("/api/sessions/never-seen/events", params={"from_seq": 0})

    assert response.status_code == 200
    state = response.json()["state"]
    assert state["auto_advance_threshold"] == AUTO_ADVANCE_FAILURE_THRESHOLD
    assert state["auto_advance_threshold"] == 3
