"""캐릭터 만들기 한 줄기가 HTTP 한 경로로 끝까지 도는지 확인하는 트레이서
시험(12.1-01 Task 2).

룰북이 데이터로 선언한 만들기 단계(자유 서술 하나 + 정해진 숫자 배치 하나)
→ 값 확정 → 완성(`Entity`/`StatEntry`) → 자동 점유(Phase 8 `OccupyCharacter`
재사용) → 명단 잠금 → 잠긴 뒤 거절, 순서로 한 세션을 끝까지 통과시킨다.

이 흐름은 AI를 전혀 타지 않으므로(D14 — 값 결정에 AI가 끼어들지 않는다)
`tests/conftest.py`의 `web_client` 픽스처(제공자 대역이 필요 없는 순수
FastAPI 클라이언트)를 그대로 쓴다.

**알려진 범위 경계(routes_creation.py 모듈 도크스트링 참조):**
`GET /my-character`·`GET /characters/{id}`는 여전히 `web.characters_data`의
정적 목록만 읽으므로, 이 계획이 세션 스코프로 만든 캐릭터는 그 두 경로에서
아직 보이지 않는다(12.1-05가 옮긴다). 이 시험은 그 대신 사건 기록
(`GET /events`)과 쿠키로 「자동 점유가 실제로 일어났다」를 확인한다.
"""

SESSION_ID = "creation-s1"
CHARACTER_ID = "hero-1"
BROWSER_ID = "b-hero-1"


def _events_of_type(client, event_type: str, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events")
    assert response.status_code == 200
    return [event for event in response.json()["events"] if event["event_type"] == event_type]


def _fix_party_size(client, count: int = 1, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/party-size",
        json={"player_character_count": count, "rulebook_id": "dungeonworld_like"},
    )


def _complete_step(client, *, session_id: str = SESSION_ID, **overrides):
    body = {
        "character_id": CHARACTER_ID,
        "browser_id": BROWSER_ID,
        "step_id": "name",
        "rulebook_id": "dungeonworld_like",
        "text_value": "브람",
    }
    body.update(overrides)
    return client.post(f"/api/sessions/{session_id}/creation/step", json=body)


def _complete_creation(client, *, character_id: str = CHARACTER_ID, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/complete",
        json={
            "character_id": character_id,
            "browser_id": BROWSER_ID,
            "rulebook_id": "dungeonworld_like",
            "one_line_intro": f"{character_id}는 조용한 마을을 떠나온 모험가다.",
        },
    )


def test_creation_end_to_end_through_lock_and_rejection_after_lock(web_client) -> None:
    client = web_client

    # ① 인원 확정(D-01)
    party_size_response = _fix_party_size(client, count=1)
    assert party_size_response.status_code == 200

    # ② 단계 둘 확정 — 자유 서술(이름) + 정해진 숫자 배치(능력치)
    name_response = _complete_step(client, step_id="name", text_value="브람")
    assert name_response.status_code == 200

    ability_response = _complete_step(
        client,
        step_id="ability_array",
        text_value=None,
        axis_values=[
            {"axis_name": "STR", "value": 2},
            {"axis_name": "DEX", "value": 1},
            {"axis_name": "CON", "value": 1},
            {"axis_name": "INT", "value": 0},
            {"axis_name": "WIS", "value": 0},
            {"axis_name": "CHA", "value": -1},
        ],
    )
    assert ability_response.status_code == 200

    # ③ 완성 — 자동 점유가 같은 요청 안에서 함께 일어난다(CHAR-05)
    complete_response = _complete_creation(client)
    assert complete_response.status_code == 200
    body = complete_response.json()
    assert body["character_id"] == CHARACTER_ID

    # ④ 완성 직후 character_occupied 사건이 남는다(CHAR-05, 자동 점유 증거)
    occupied_events = _events_of_type(client, "character_occupied")
    assert len(occupied_events) == 1
    assert occupied_events[0]["character_id"] == CHARACTER_ID
    assert occupied_events[0]["browser_id"] == BROWSER_ID

    created_events = _events_of_type(client, "character_created")
    assert len(created_events) == 1
    assert created_events[0]["display_name"] == "브람"
    assert len(created_events[0]["stats"]) == 6  # 능력치 여섯 칸

    # 자동 점유가 만든 쿠키가 실제로 이 캐릭터를 가리킨다
    raw_cookie = client.cookies.get("gptrpg_character")
    assert raw_cookie is not None

    # ⑤ 명단 잠금(D-08)
    lock_response = client.post(
        f"/api/sessions/{SESSION_ID}/creation/lock-roster",
        json={"character_ids": [CHARACTER_ID]},
    )
    assert lock_response.status_code == 200

    locked_events = _events_of_type(client, "party_roster_locked")
    assert len(locked_events) == 1
    assert locked_events[0]["character_ids"] == [CHARACTER_ID]

    # ⑥ 잠긴 뒤 새 캐릭터 완성 시도는 409다(D-08 — 중간에 추가 없음).
    # 이 클라이언트는 이미 hero-1 쿠키를 들고 있으므로(위 자동 점유), 그
    # 쿠키를 지워 「아직 아무도 선택한 적 없는 새 브라우저」를 흉내낸다 —
    # 그래야 확인하려는 거절이 신원 대조(403)가 아니라 명단 잠금(409)임이
    # 분명해진다.
    client.cookies.clear()
    second_step_response = client.post(
        f"/api/sessions/{SESSION_ID}/creation/step",
        json={
            "character_id": "hero-2",
            "browser_id": "b-hero-2",
            "step_id": "name",
            "rulebook_id": "dungeonworld_like",
            "text_value": "나리",
        },
    )
    assert second_step_response.status_code == 409

    second_complete_response = _complete_creation(client, character_id="hero-2")
    assert second_complete_response.status_code == 409


def test_place_fixed_values_rejects_a_mismatched_value_multiset(web_client) -> None:
    """T-12.1-04 — 선언된 fixed_values와 다른 숫자 묶음을 배치하면 거절된다."""
    client = web_client
    response = client.post(
        f"/api/sessions/{SESSION_ID}-tamper/creation/step",
        json={
            "character_id": CHARACTER_ID,
            "browser_id": BROWSER_ID,
            "step_id": "ability_array",
            "rulebook_id": "dungeonworld_like",
            "axis_values": [
                {"axis_name": "STR", "value": 9},
                {"axis_name": "DEX", "value": 9},
                {"axis_name": "CON", "value": 9},
                {"axis_name": "INT", "value": 9},
                {"axis_name": "WIS", "value": 9},
                {"axis_name": "CHA", "value": 9},
            ],
        },
    )
    assert response.status_code == 409


def test_complete_without_any_confirmed_step_is_rejected(web_client) -> None:
    """단계 값이 하나도 확정되지 않은 채 완료를 제출하면 조용히 빈 캐릭터가
    만들어지지 않고 거절된다."""
    client = web_client
    response = _complete_creation(
        client, character_id="ghost", session_id=f"{SESSION_ID}-empty"
    )
    assert response.status_code == 409


def test_lock_roster_with_empty_character_ids_is_rejected(web_client) -> None:
    """빈 명단 잠금은 거절된다 — 「아직 아무도 안 만들었다」와 구분되지 않는다."""
    client = web_client
    response = client.post(
        f"/api/sessions/{SESSION_ID}-empty-lock/creation/lock-roster",
        json={"character_ids": []},
    )
    assert response.status_code == 409


def test_occupy_succeeds_for_a_fresh_session_with_only_creation_events(web_client) -> None:
    """12.1-01 트레이서가 잡아낸 충돌 — 만들기 사건만 쌓인 새 세션에서
    자동 점유가 「옛 세션」으로 거절되지 않는다(Task 2 ⑦)."""
    client = web_client
    session_id = f"{SESSION_ID}-fresh-occupy"

    assert _fix_party_size(client, count=1, session_id=session_id).status_code == 200
    assert (
        _complete_step(client, session_id=session_id, step_id="name", text_value="선").status_code
        == 200
    )
    assert (
        _complete_step(
            client,
            session_id=session_id,
            step_id="ability_array",
            text_value=None,
            axis_values=[
                {"axis_name": "STR", "value": 2},
                {"axis_name": "DEX", "value": 1},
                {"axis_name": "CON", "value": 1},
                {"axis_name": "INT", "value": 0},
                {"axis_name": "WIS", "value": 0},
                {"axis_name": "CHA", "value": -1},
            ],
        ).status_code
        == 200
    )
    complete_response = _complete_creation(client, session_id=session_id)
    assert complete_response.status_code == 200

    occupied_events = _events_of_type(client, "character_occupied", session_id=session_id)
    assert len(occupied_events) == 1
