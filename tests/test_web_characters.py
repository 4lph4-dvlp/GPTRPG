"""캐릭터 목록·시트·선택·조회 네 경로 시험 (04-04).

`web_client`는 `tests/conftest.py`가 lifespan을 열어 주는 픽스처다 —
`EventStore`가 필요하지 않은 시험이지만(캐릭터 데이터는 저장소를 안 만짐)
같은 앱 인스턴스를 재사용해 라우터 등록 순서까지 실제와 같은 경로로
검증한다.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from gptrpg.event_log.schema import EVENT_SCHEMA_VERSION, ActionDeclared, utc_now_iso
from gptrpg.event_log.store import EventStore
from gptrpg.web.characters_data import (
    CHARACTER_ARCHETYPES,
    NEW_CHARACTER_HP_BASE,
    NEW_CHARACTER_HP_PER_CON,
    NEW_CHARACTER_STAT_ARRAY,
    NEW_CHARACTER_STAT_NAMES,
    PLAYER_CHARACTERS,
)
from gptrpg.web.cookie_auth import verify_cookie
from gptrpg.web.routes_characters import COOKIE_NAME

_HP_DEPLETED_REF = "dungeonworld_like.hp_depleted"


def test_known_character_sheet_matches_characters_data(web_client: TestClient) -> None:
    """알려진 캐릭터의 시트가 `characters_data`의 값과 칸마다 같다."""
    entity = PLAYER_CHARACTERS["bram"]

    response = web_client.get("/api/sessions/s1/characters/bram")

    assert response.status_code == 200
    body = response.json()
    assert body["entity_id"] == entity.entity_id
    assert body["display_name"] == entity.display_name
    assert body["rulebook_id"] == entity.rulebook_id
    assert len(body["stats"]) == len(entity.stats)
    for stat_view, stat in zip(body["stats"], entity.stats, strict=True):
        assert stat_view["name"] == stat.name
        assert stat_view["current"] == stat.current
        assert stat_view["max"] == stat.max
        assert stat_view["depleted_effect_ref"] == stat.depleted_effect_ref


def test_unknown_character_sheet_returns_404(web_client: TestClient) -> None:
    """모르는 캐릭터 식별자는 404다."""
    response = web_client.get("/api/sessions/s1/characters/no-such-character")

    assert response.status_code == 404


def test_different_stat_counts_produce_same_shaped_response(web_client: TestClient) -> None:
    """상태값 개수가 다른 두 캐릭터 모두 같은 모양(칸 이름 집합)의 응답을 낸다."""
    assert len(PLAYER_CHARACTERS["bram"].stats) != len(PLAYER_CHARACTERS["nari"].stats), (
        "이 시험은 두 캐릭터의 상태값 개수가 실제로 달라야 의미가 있다"
    )

    bram_response = web_client.get("/api/sessions/s1/characters/bram")
    nari_response = web_client.get("/api/sessions/s1/characters/nari")

    assert bram_response.status_code == 200
    assert nari_response.status_code == 200
    top_level_keys = set(bram_response.json().keys())
    assert top_level_keys == set(nari_response.json().keys())
    for stats_list in (bram_response.json()["stats"], nari_response.json()["stats"]):
        for stat_view in stats_list:
            assert set(stat_view.keys()) == {"name", "current", "max", "depleted_effect_ref"}


def test_character_sheet_route_rejects_all_write_methods(web_client: TestClient) -> None:
    """시트 주소에 PUT/PATCH/DELETE/POST를 보내면 전부 405다 (RIG-05 읽기 전용)."""
    for method in ("put", "patch", "delete", "post"):
        response = web_client.request(method, "/api/sessions/s1/characters/bram")
        assert response.status_code == 405, f"{method.upper()}이 405가 아니었다: {response.status_code}"


def test_select_character_sets_httponly_lax_cookie(web_client: TestClient) -> None:
    """`select-character`가 쿠키를 걸고, 그 쿠키에 HttpOnly와 SameSite=lax가 붙어 있다."""
    response = web_client.post(
        "/api/sessions/s1/select-character",
        json={"character_id": "bram"},
    )

    assert response.status_code == 200
    assert response.json() == {"selected": True, "character_id": "bram"}
    set_cookie_header = response.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie_header
    assert "httponly" in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()


def test_my_character_returns_selected_true_after_selecting(web_client: TestClient) -> None:
    """쿠키를 건 뒤 `my-character`가 `selected: true`를 돌려준다."""
    web_client.post("/api/sessions/s1/select-character", json={"character_id": "nari"})

    response = web_client.get("/api/sessions/s1/my-character")

    assert response.status_code == 200
    assert response.json() == {"selected": True, "character_id": "nari"}


def test_my_character_returns_selected_false_for_different_session(web_client: TestClient) -> None:
    """다른 세션 식별자로 `my-character`를 부르면 `selected: false`다."""
    web_client.post("/api/sessions/s1/select-character", json={"character_id": "nari"})

    response = web_client.get("/api/sessions/s2/my-character")

    assert response.status_code == 200
    assert response.json() == {"selected": False, "character_id": None}


def test_select_unknown_character_returns_400_and_sets_no_cookie(web_client: TestClient) -> None:
    """모르는 캐릭터로 `select-character`를 부르면 400이고 쿠키가 걸리지 않는다."""
    response = web_client.post(
        "/api/sessions/s1/select-character",
        json={"character_id": "no-such-character"},
    )

    assert response.status_code == 400
    assert "set-cookie" not in response.headers


def test_path_traversal_session_id_rejected_with_400(web_client: TestClient) -> None:
    """상위 경로를 가리키는 세션 식별자는 400이다."""
    response = web_client.get("/api/sessions/..escape/characters")

    assert response.status_code == 400


def test_character_list_contains_all_hand_authored_characters(web_client: TestClient) -> None:
    """목록 경로가 손으로 쓴 캐릭터 전부와 그 한 줄 소개를 돌려준다."""
    response = web_client.get("/api/sessions/s1/characters")

    assert response.status_code == 200
    body = response.json()
    assert {item["character_id"] for item in body} == set(PLAYER_CHARACTERS.keys())
    for item in body:
        assert item["archetype"] == CHARACTER_ARCHETYPES[item["character_id"]]


def test_bram_and_nari_stats_are_pinned_by_d49() -> None:
    """브람·나리의 수치가 05-02 계획 실행 전후로 한 칸도 달라지지 않는다.

    이 시험이 깨지면 D-49(경험자 2명이 쓸 캐릭터는 그대로 유지)가 깨진 것이다
    — 값도 순서도 05-01 종료 시점 그대로여야 한다.
    """

    def stats_tuple(character_id: str) -> tuple[tuple[str, int, int | None, str | None], ...]:
        return tuple(
            (stat.name, stat.current, stat.max, stat.depleted_effect_ref)
            for stat in PLAYER_CHARACTERS[character_id].stats
        )

    assert stats_tuple("bram") == (
        ("체력", 20, 20, _HP_DEPLETED_REF),
        ("STR", 2, None, None),
        ("DEX", 0, None, None),
        ("CON", 1, None, None),
        ("INT", -1, None, None),
        ("WIS", 0, None, None),
        ("CHA", 0, None, None),
        ("방어구", 2, None, None),
    )
    assert stats_tuple("nari") == (
        ("체력", 16, 16, _HP_DEPLETED_REF),
        ("STR", 0, None, None),
        ("DEX", 2, None, None),
        ("CON", 0, None, None),
        ("INT", 1, None, None),
        ("WIS", 1, None, None),
        ("CHA", -1, None, None),
    )


def test_seon_and_hodu_placeholders_satisfy_new_character_spec() -> None:
    """선·호두 자리표시자가 신규 캐릭터 규격(능력치 배열·체력 공식)을 만족한다.

    세션 당일 손으로 갈아 끼운 값을 검사할 관문과 같은 단언이다. 브람·나리는
    이 규격의 대상이 아니다(D-49).
    """
    expected_sorted_stats = sorted(NEW_CHARACTER_STAT_ARRAY)

    for character_id in ("seon", "hodu"):
        stats_by_name = {stat.name: stat for stat in PLAYER_CHARACTERS[character_id].stats}

        actual_sorted_stats = sorted(stats_by_name[name].current for name in NEW_CHARACTER_STAT_NAMES)
        assert actual_sorted_stats == expected_sorted_stats, character_id

        hp = stats_by_name["체력"]
        con = stats_by_name["CON"].current
        expected_hp = NEW_CHARACTER_HP_BASE + con * NEW_CHARACTER_HP_PER_CON
        assert hp.current == expected_hp, character_id
        assert hp.current == hp.max, character_id
        assert hp.depleted_effect_ref, character_id


# ---------------------------------------------------------------------------
# 08-01 Task 4 — QUAL-04·QUAL-05 관문 시험
# ---------------------------------------------------------------------------


def test_select_character_id_over_max_length_returns_422_and_sets_no_cookie(
    web_client: TestClient,
) -> None:
    """QUAL-04: `character_id`에 상한이 없으면 쿠키 크기 상한(브라우저마다
    보통 4KB)을 넘겨 조용한 저장 실패가 날 수 있다(Pitfall 3). 65자(상한
    `MAX_ID_LEN=64`를 1 넘긴 값)는 422이고 쿠키가 걸리지 않는다."""
    response = web_client.post(
        "/api/sessions/s1/select-character",
        json={"character_id": "a" * 65},
    )

    assert response.status_code == 422
    assert "set-cookie" not in response.headers


def test_identity_mismatch_response_has_no_secret_leak(web_client: TestClient) -> None:
    """QUAL-05: 신원 불일치(403) 응답 본문에 ① 발급된 쿠키 값 전체 ② 비밀
    열쇠 바이트의 16진 표현 ③ 서명 조각 ④ `browser_id` 값 넷 중 어느 것도
    부분 문자열로 실려 나가지 않는다."""
    select_response = web_client.post(
        "/api/sessions/s1/select-character", json={"character_id": "bram"}
    )
    assert select_response.status_code == 200
    cookie_value = web_client.cookies.get(COOKIE_NAME)
    assert cookie_value is not None

    secret = web_client.app.state.cookie_secret
    payload = verify_cookie(cookie_value, secret=secret)
    assert payload is not None
    browser_id = payload["browser_id"]
    signature_fragment = cookie_value.rsplit(".", 1)[-1]
    secret_hex = secret.hex()

    # bram 쿠키를 그대로 든 채, 본문의 character_id만 다른 캐릭터로 어긋내
    # 신원 불일치(TRUST-02)를 일으킨다 — declare()의 신원 대조는 제공자
    # 설정에 닿기 전에 먼저 걸리므로 `web_client`(대역 제공자 없음)로 충분하다.
    response = web_client.post(
        "/api/sessions/s1/actions/declare",
        json={
            "player_id": "p1",
            "character_id": "nari",
            "raw_text": "아무 문장",
            "rulebook_id": "dungeonworld_like",
        },
    )
    assert response.status_code == 403

    body_text = response.text
    assert cookie_value not in body_text
    assert secret_hex not in body_text
    assert signature_fragment not in body_text
    assert browser_id not in body_text


# ---------------------------------------------------------------------------
# 08-02 Task 2 — 캐릭터 점유가 select-character보다 먼저 제출된다.
# 「먼저 잡은 사람이 임자다」(D-05), 놓기는 없다(D-07), D-14가 옛/새 세션을
# 가른다.
# ---------------------------------------------------------------------------


def _character_occupied_event_count(tmp_db_path: Path, session_id: str = "s1") -> int:
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        events = store.read_events(session_id)
    finally:
        store.close()
    return sum(1 for event in events if event.event_type == "character_occupied")


def test_occupancy_first_select_appends_one_character_occupied_event(
    web_client: TestClient, tmp_db_path: Path
) -> None:
    response = web_client.post(
        "/api/sessions/s1/select-character", json={"character_id": "bram"}
    )

    assert response.status_code == 200
    assert _character_occupied_event_count(tmp_db_path) == 1


def test_occupancy_second_browser_without_cookie_gets_409_no_cookie_no_new_event(
    web_app: FastAPI, tmp_db_path: Path
) -> None:
    """빈 세션에서 다른 브라우저가 같은 캐릭터를 고르면 409이고, 쿠키가
    걸리지 않고 사건도 늘지 않는다.

    두 `TestClient`는 **차례로**(중첩하지 않고) 연다 — 같은 `SessionActor`의
    `asyncio.Queue`를 서로 다른 포털 스레드/이벤트 루프에서 동시에
    건드리면 08-01이 이미 겪은 교착(멎음)이 재발한다. 점유는 사건
    기록으로 남으므로(D-06) `with` 블록을 나갔다 다시 들어가도, 즉 서버가
    재시작해도 「다른 브라우저」 재현이 그대로 성립한다 — 같은
    `tmp_db_path`와 `cookie_secret` 파일을 공유하기 때문이다.
    """
    with TestClient(web_app) as client_a:
        first = client_a.post(
            "/api/sessions/s1/select-character", json={"character_id": "bram"}
        )
        assert first.status_code == 200

    with TestClient(web_app) as client_b:
        second = client_b.post(
            "/api/sessions/s1/select-character", json={"character_id": "bram"}
        )

        assert second.status_code == 409
        assert "set-cookie" not in second.headers
    assert _character_occupied_event_count(tmp_db_path) == 1


def test_occupancy_second_browser_can_select_a_different_character(
    web_app: FastAPI,
) -> None:
    """진 쪽은 다른 캐릭터를 고를 수 있다(D-05)."""
    with TestClient(web_app) as client_a:
        first = client_a.post(
            "/api/sessions/s1/select-character", json={"character_id": "bram"}
        )
        assert first.status_code == 200

    with TestClient(web_app) as client_b:
        second = client_b.post(
            "/api/sessions/s1/select-character", json={"character_id": "nari"}
        )
        assert second.status_code == 200


def test_occupancy_own_reselect_returns_200_and_does_not_duplicate_event(
    web_client: TestClient, tmp_db_path: Path
) -> None:
    """본인 재접속은 그대로 통과하고 사건은 늘지 않는다(D-05)."""
    first = web_client.post(
        "/api/sessions/s1/select-character", json={"character_id": "bram"}
    )
    assert first.status_code == 200

    second = web_client.post(
        "/api/sessions/s1/select-character", json={"character_id": "bram"}
    )
    assert second.status_code == 200
    assert _character_occupied_event_count(tmp_db_path) == 1


def test_occupancy_reselecting_a_different_character_returns_409(
    web_client: TestClient,
) -> None:
    """한 브라우저는 한 캐릭터만(D-07) — 이미 bram을 쥔 쿠키로 nari를 고르면 409."""
    first = web_client.post(
        "/api/sessions/s1/select-character", json={"character_id": "bram"}
    )
    assert first.status_code == 200

    second = web_client.post(
        "/api/sessions/s1/select-character", json={"character_id": "nari"}
    )
    assert second.status_code == 409


def test_occupancy_409_response_has_no_holder_identity_leak(web_app: FastAPI) -> None:
    """QUAL-05: 409 응답 본문 어디에도 점유자의 browser_id가 실려 나가지 않는다."""
    with TestClient(web_app) as client_a:
        first = client_a.post(
            "/api/sessions/s1/select-character", json={"character_id": "bram"}
        )
        assert first.status_code == 200
        cookie_value = client_a.cookies.get(COOKIE_NAME)
        assert cookie_value is not None
        secret = client_a.app.state.cookie_secret
        payload = verify_cookie(cookie_value, secret=secret)
        assert payload is not None
        holder_browser_id = payload["browser_id"]

    with TestClient(web_app) as client_b:
        second = client_b.post(
            "/api/sessions/s1/select-character", json={"character_id": "bram"}
        )

    assert second.status_code == 409
    assert holder_browser_id not in second.text


def test_occupancy_old_session_rejects_select_but_polling_still_succeeds(
    tmp_db_path: Path, web_app: FastAPI
) -> None:
    """D-14 옛 세션: 사건은 있는데(action_declared) 점유 사건이 없으면
    select-character는 409지만 폴링(GET /events)은 여전히 200이다 — 다시보기는
    된다."""
    store = EventStore(tmp_db_path)
    store.initialize()
    store.append(
        ActionDeclared(
            session_id="s1",
            seq=0,
            schema_version=EVENT_SCHEMA_VERSION,
            caused_by_seq=None,
            recorded_at=utc_now_iso(),
            event_type="action_declared",
            player_id="p1",
            raw_text="문을 두드린다",
        )
    )
    store.close()

    with TestClient(web_app) as client:
        select_response = client.post(
            "/api/sessions/s1/select-character", json={"character_id": "bram"}
        )
        assert select_response.status_code == 409

        poll_response = client.get("/api/sessions/s1/events")
        assert poll_response.status_code == 200


def test_occupancy_new_session_with_zero_events_select_succeeds(web_client: TestClient) -> None:
    """D-14 새 세션: 사건이 하나도 없는 세션에서는 언제나 정상적으로 잡힌다."""
    response = web_client.post(
        "/api/sessions/s1/select-character", json={"character_id": "bram"}
    )
    assert response.status_code == 200


def test_occupancy_same_character_selectable_independently_in_a_different_session(
    web_client: TestClient,
) -> None:
    """점유는 세션 범위다 — s1에서 bram을 잡아도 s2에서 같은 브라우저가 bram을
    고르는 것은 충돌이 아니다(`GameState`는 세션마다 따로 접힌다)."""
    first = web_client.post(
        "/api/sessions/s1/select-character", json={"character_id": "bram"}
    )
    assert first.status_code == 200

    second = web_client.post(
        "/api/sessions/s2/select-character", json={"character_id": "bram"}
    )
    assert second.status_code == 200
