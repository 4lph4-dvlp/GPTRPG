"""캐릭터 목록·시트·선택·조회 네 경로 시험 (04-04).

`web_client`는 `tests/conftest.py`가 lifespan을 열어 주는 픽스처다 —
`EventStore`가 필요하지 않은 시험이지만(캐릭터 데이터는 저장소를 안 만짐)
같은 앱 인스턴스를 재사용해 라우터 등록 순서까지 실제와 같은 경로로
검증한다.
"""

import asyncio
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from gptrpg.event_log.schema import (
    EVENT_SCHEMA_VERSION,
    ActionDeclared,
    ResourceChanged,
    utc_now_iso,
)
from gptrpg.event_log.store import EventStore
from gptrpg.rulebooks import RULEBOOKS
from gptrpg.rules_core.entities import Entity, StatEntry
from gptrpg.rules_core.rulebook import GradeBand, ResourceAxisDecl, Rulebook, TWO_D6
from gptrpg.web.cookie_auth import verify_cookie
from gptrpg.web.routes_characters import COOKIE_NAME

from conftest import seed_character_created as _seed_character_created
from tests.fixtures.characters import (
    CHARACTER_ARCHETYPES,
    NEW_CHARACTER_HP_BASE,
    NEW_CHARACTER_HP_PER_CON,
    NEW_CHARACTER_STAT_ARRAY,
    NEW_CHARACTER_STAT_NAMES,
    PLAYER_CHARACTERS,
)

_HP_DEPLETED_REF = "dungeonworld_like.hp_depleted"


def test_known_character_sheet_matches_characters_data(web_client: TestClient) -> None:
    """알려진 캐릭터의 시트가 시험 재료(`tests/fixtures/characters.py`)의 값과
    칸마다 같다(이 캐릭터를 이 세션에서 먼저 「만든」 뒤에)."""
    entity = PLAYER_CHARACTERS["bram"]
    _seed_character_created(web_client.app.state.db_path, "s1", "bram")

    response = web_client.get("/api/sessions/s1/characters/bram")

    assert response.status_code == 200
    body = response.json()
    # 12.1-05부터 세션에서 만들어진 캐릭터의 entity_id는 짧은 식별자
    # ("bram")다 — 시험 재료의 긴 형태("player.bram")가 아니다. 만들기
    # 완료가 처음부터 짧은 형태로 Entity를 만들기 때문이다(D-01).
    assert body["entity_id"] == "bram"
    assert body["display_name"] == entity.display_name
    assert body["rulebook_id"] == entity.rulebook_id
    assert len(body["stats"]) == len(entity.stats)
    for stat_view, stat in zip(body["stats"], entity.stats, strict=True):
        assert stat_view["name"] == stat.name
        assert stat_view["form"] == stat.form
        assert stat_view["current"] == stat.current
        assert stat_view["max"] == stat.max
        assert stat_view["depleted_effect_ref"] == stat.depleted_effect_ref


def test_none_axis_excluded_from_sheet_response(web_client: TestClient) -> None:
    """`form == "none"`으로 선언된 축은 시트 응답의 `stats`에 없고, 그 축
    이름이 응답 본문 문자열 어디에도 등장하지 않는다(RULE-12 성공 기준 2) —
    화면이 숨기는 것이 아니라 서버가 안 보낸다는 것을 문자열 단언으로
    고정한다. 이름은 이 시험 안에서만 쓰는 값으로 짓고 특정 룰북 어휘를
    쓰지 않는다."""
    test_rulebook_id = "test-only-none-axis-rulebook"
    hidden_axis_name = "시험전용안쓰는축"
    visible_axis_name = "시험전용쓰는축"
    test_rulebook = Rulebook(
        rulebook_id=test_rulebook_id,
        display_name="시험 전용",
        resolution_method=TWO_D6,
        grade_bands=(GradeBand(name="success", counts_as_failure=False, succeeded=True, costs=False),),
        resource_axes=(
            ResourceAxisDecl(name=hidden_axis_name, form="none", none_kind="absent"),
            ResourceAxisDecl(name=visible_axis_name, form="numeric"),
        ),
        check_trigger_mode="no_dice",
    )
    test_character_id = "test-only-none-axis-character"
    test_entity = Entity(
        entity_id="test.none_axis_character",
        display_name="시험용",
        rulebook_id=test_rulebook_id,
        stats=(
            StatEntry(name=hidden_axis_name, form="none", none_kind="absent"),
            StatEntry(name=visible_axis_name, form="numeric", current=3),
        ),
    )
    RULEBOOKS[test_rulebook_id] = test_rulebook
    try:
        _seed_character_created(
            web_client.app.state.db_path, "s1", test_character_id, entity=test_entity
        )
        response = web_client.get(f"/api/sessions/s1/characters/{test_character_id}")
    finally:
        del RULEBOOKS[test_rulebook_id]

    assert response.status_code == 200
    body = response.json()
    stat_names = {stat["name"] for stat in body["stats"]}
    assert hidden_axis_name not in stat_names
    assert visible_axis_name in stat_names
    assert hidden_axis_name not in response.text


def test_dungeonworld_discretionary_axis_is_absent_from_sheet_response(
    web_client: TestClient,
) -> None:
    """던전월드류가 실제로 선언한 `form="none"`(`discretionary`) 축("소지품")이
    브람의 시트 응답 본문 문자열 어디에도 등장하지 않는다(RULE-12, D-67,
    11-07) — 시험 픽스처가 아니라 저장소에 출하되는 실제 룰북 데이터로
    RULE-12를 실증한다."""
    _seed_character_created(web_client.app.state.db_path, "s1", "bram")
    response = web_client.get("/api/sessions/s1/characters/bram")

    assert response.status_code == 200
    assert "소지품" not in response.text


def test_dungeonworld_sheet_stat_count_unchanged_by_none_axis(web_client: TestClient) -> None:
    """룰북이 「소지품」 축을 새로 선언해도, 그 축을 갖지 않은 브람의 시트
    `stats` 길이는 `Entity.stats` 선언 길이와 완전히 같다 — 룰북이 선언한
    `none` 축이 개체에 없는 값을 새로 실어 보내지 않는다(D-04)."""
    _seed_character_created(web_client.app.state.db_path, "s1", "bram")
    response = web_client.get("/api/sessions/s1/characters/bram")

    assert response.status_code == 200
    assert len(response.json()["stats"]) == len(PLAYER_CHARACTERS["bram"].stats)


def test_rulebook_with_zero_axes_returns_empty_stats(web_client: TestClient) -> None:
    """`resource_axes=()`인 룰북을 쓰는 개체의 시트 응답은 `stats: []`이고
    HTTP 200이다."""
    test_rulebook_id = "test-only-zero-axes-rulebook"
    test_rulebook = Rulebook(
        rulebook_id=test_rulebook_id,
        display_name="시험 전용",
        resolution_method=TWO_D6,
        grade_bands=(GradeBand(name="success", counts_as_failure=False, succeeded=True, costs=False),),
        resource_axes=(),
        check_trigger_mode="no_dice",
    )
    test_character_id = "test-only-zero-axes-character"
    test_entity = Entity(
        entity_id="test.zero_axes_character",
        display_name="시험용",
        rulebook_id=test_rulebook_id,
        stats=(),
    )
    RULEBOOKS[test_rulebook_id] = test_rulebook
    try:
        _seed_character_created(
            web_client.app.state.db_path, "s1", test_character_id, entity=test_entity
        )
        response = web_client.get(f"/api/sessions/s1/characters/{test_character_id}")
    finally:
        del RULEBOOKS[test_rulebook_id]

    assert response.status_code == 200
    assert response.json()["stats"] == []


def test_sheet_stats_preserve_declaration_order(web_client: TestClient) -> None:
    """브람 시트 응답의 `stats` 이름 순서가 `Entity.stats` 선언 순서와
    완전히 같다(RULE-11 ordering) — 응답 조립 단계가 어디서도 다시
    정렬하지 않는다는 증거다."""
    _seed_character_created(web_client.app.state.db_path, "s1", "bram")
    response = web_client.get("/api/sessions/s1/characters/bram")

    assert response.status_code == 200
    response_names = [stat["name"] for stat in response.json()["stats"]]
    declared_names = [stat.name for stat in PLAYER_CHARACTERS["bram"].stats]
    assert response_names == declared_names


def test_unknown_character_sheet_returns_404(web_client: TestClient) -> None:
    """모르는 캐릭터 식별자는 404다."""
    response = web_client.get("/api/sessions/s1/characters/no-such-character")

    assert response.status_code == 404


def test_different_stat_counts_produce_same_shaped_response(web_client: TestClient) -> None:
    """상태값 개수가 다른 두 캐릭터 모두 같은 모양(칸 이름 집합)의 응답을 낸다."""
    assert len(PLAYER_CHARACTERS["bram"].stats) != len(PLAYER_CHARACTERS["nari"].stats), (
        "이 시험은 두 캐릭터의 상태값 개수가 실제로 달라야 의미가 있다"
    )
    _seed_character_created(web_client.app.state.db_path, "s1", "bram")
    _seed_character_created(web_client.app.state.db_path, "s1", "nari")

    bram_response = web_client.get("/api/sessions/s1/characters/bram")
    nari_response = web_client.get("/api/sessions/s1/characters/nari")

    assert bram_response.status_code == 200
    assert nari_response.status_code == 200
    top_level_keys = set(bram_response.json().keys())
    assert top_level_keys == set(nari_response.json().keys())
    for stats_list in (bram_response.json()["stats"], nari_response.json()["stats"]):
        for stat_view in stats_list:
            assert set(stat_view.keys()) == {
                "name",
                "form",
                "current",
                "max",
                "depleted_effect_ref",
                "slot_values",
                "tags",
                "none_kind",
            }


def test_character_sheet_route_rejects_all_write_methods(web_client: TestClient) -> None:
    """시트 주소에 PUT/PATCH/DELETE/POST를 보내면 전부 405다 (RIG-05 읽기 전용)."""
    for method in ("put", "patch", "delete", "post"):
        response = web_client.request(method, "/api/sessions/s1/characters/bram")
        assert response.status_code == 405, f"{method.upper()}이 405가 아니었다: {response.status_code}"


def test_select_character_sets_httponly_lax_cookie(web_client: TestClient) -> None:
    """`select-character`가 쿠키를 걸고, 그 쿠키에 HttpOnly와 SameSite=lax가 붙어 있다."""
    _seed_character_created(web_client.app.state.db_path, "s1", "bram")
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
    _seed_character_created(web_client.app.state.db_path, "s1", "nari")
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


def test_character_list_is_empty_when_nobody_has_created_a_character(
    web_client: TestClient,
) -> None:
    """12.1-05: 만들기가 하나도 안 일어난 세션의 캐릭터 목록은 빈 목록이다
    (CHAR-02 empty) — 완성된 캐릭터를 미리 보여주는 정적 목록은 이제
    제품 코드 어디에도 없다."""
    response = web_client.get("/api/sessions/s1/characters")

    assert response.status_code == 200
    assert response.json() == []


def test_character_list_contains_only_characters_created_in_this_session(
    web_client: TestClient,
) -> None:
    """12.1-05: 목록 경로는 「이 세션에서 만들어진 캐릭터」만 돌려주고,
    그 순서는 완성된 순서다(D-01/D-12) — 정적 상수 넷을 전부 돌려주지
    않는다. `archetype`은 `character_created` 사건의 `one_line_intro`에서
    온다(CHAR-03)."""
    db_path = web_client.app.state.db_path
    _seed_character_created(db_path, "s1", "bram", one_line_intro=CHARACTER_ARCHETYPES["bram"])
    _seed_character_created(db_path, "s1", "nari", one_line_intro=CHARACTER_ARCHETYPES["nari"])

    response = web_client.get("/api/sessions/s1/characters")

    assert response.status_code == 200
    body = response.json()
    assert [item["character_id"] for item in body] == ["bram", "nari"]
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
    _seed_character_created(web_client.app.state.db_path, "s1", "bram")
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
    _seed_character_created(tmp_db_path, "s1", "bram")
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
    _seed_character_created(tmp_db_path, "s1", "bram")
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
    web_app: FastAPI, tmp_db_path: Path
) -> None:
    """진 쪽은 다른 캐릭터를 고를 수 있다(D-05)."""
    _seed_character_created(tmp_db_path, "s1", "bram")
    _seed_character_created(tmp_db_path, "s1", "nari")
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
    _seed_character_created(tmp_db_path, "s1", "bram")
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
    _seed_character_created(web_client.app.state.db_path, "s1", "bram")
    _seed_character_created(web_client.app.state.db_path, "s1", "nari")
    first = web_client.post(
        "/api/sessions/s1/select-character", json={"character_id": "bram"}
    )
    assert first.status_code == 200

    second = web_client.post(
        "/api/sessions/s1/select-character", json={"character_id": "nari"}
    )
    assert second.status_code == 409


def test_occupancy_409_response_has_no_holder_identity_leak(
    web_app: FastAPI, tmp_db_path: Path
) -> None:
    """QUAL-05: 409 응답 본문 어디에도 점유자의 browser_id가 실려 나가지 않는다."""
    _seed_character_created(tmp_db_path, "s1", "bram")
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
    """D-14 옛 세션: 사건은 있는데(action_declared) 캐릭터 만들기 사건이
    하나도 없으면 select-character는 거절되지만 폴링(GET /events)은 여전히
    200이다 — 다시보기는 된다.

    **12.1-05부터 응답 코드는 400이다(409가 아니다).** 이전에는 "bram"이
    정적 상수라 항상 「알려진 캐릭터」였고, 옛 세션 판별(`_prepare_occupy`,
    D-14)이 점유 시도 단계에서 409로 막았다. 이제는 select-character의
    첫 관문이 「이 세션에서 실제로 만들어진 캐릭터인가」이고(CHAR-02),
    이 세션은 애초에 그런 캐릭터가 하나도 없으므로(옛 세션이 정확히 그런
    상태다) 그 관문에서 400으로 먼저 걸린다 — 점유 시도까지 가지도 않는다.
    「다시보기는 되지만 새로 캐릭터를 잡을 수 없다」는 결론 자체는 그대로다.
    `_prepare_occupy`의 옛 세션 판별 자체는 `tests/test_session_actor.py`가
    여전히 직접 검사한다.
    """
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
        assert select_response.status_code == 400

        poll_response = client.get("/api/sessions/s1/events")
        assert poll_response.status_code == 200


def test_occupancy_new_session_with_zero_events_select_succeeds(web_client: TestClient) -> None:
    """D-14 새 세션: 사건이 하나도 없는 세션에서는 언제나 정상적으로 잡힌다."""
    _seed_character_created(web_client.app.state.db_path, "s1", "bram")
    response = web_client.post(
        "/api/sessions/s1/select-character", json={"character_id": "bram"}
    )
    assert response.status_code == 200


def test_occupancy_same_character_selectable_independently_in_a_different_session(
    web_client: TestClient,
) -> None:
    """점유는 세션 범위다 — s1에서 bram을 잡아도 s2에서 같은 브라우저가 bram을
    고르는 것은 충돌이 아니다(`GameState`는 세션마다 따로 접힌다)."""
    db_path = web_client.app.state.db_path
    _seed_character_created(db_path, "s1", "bram")
    _seed_character_created(db_path, "s2", "bram")
    first = web_client.post(
        "/api/sessions/s1/select-character", json={"character_id": "bram"}
    )
    assert first.status_code == 200

    second = web_client.post(
        "/api/sessions/s2/select-character", json={"character_id": "bram"}
    )
    assert second.status_code == 200


# ---------------------------------------------------------------------------
# 08-02 Task 3 (TEST-02) — HTTP 계층: 두 개의 독립된 AsyncClient가 같은 앱에
# 같은 캐릭터로 동시에 select-character를 보낸다.
#
# `ASGITransport`는 lifespan을 스스로 돌리지 않는다 — `web_app.router.
# lifespan_context(web_app)` 블록 안에서 두 클라이언트를 열어 새 의존성 없이
# `app.state.store`/`registry`/`cookie_secret`을 채운다.
# ---------------------------------------------------------------------------


async def test_concurrent_select_character_same_character_status_codes_are_200_and_409(
    web_app: FastAPI, tmp_db_path: Path
) -> None:
    _seed_character_created(tmp_db_path, "s1", "bram")
    async with web_app.router.lifespan_context(web_app):
        transport = ASGITransport(app=web_app)
        async with (
            AsyncClient(transport=transport, base_url="http://test") as client_a,
            AsyncClient(transport=transport, base_url="http://test") as client_b,
        ):
            response_a, response_b = await asyncio.gather(
                client_a.post(
                    "/api/sessions/s1/select-character", json={"character_id": "bram"}
                ),
                client_b.post(
                    "/api/sessions/s1/select-character", json={"character_id": "bram"}
                ),
            )

    assert {response_a.status_code, response_b.status_code} == {200, 409}


# ---------------------------------------------------------------------------
# 12-01 — 캐릭터 시트가 시작값이 아니라 접은 지금 값을 돌려준다(RULE-06, D-65).
# ---------------------------------------------------------------------------


def test_resource_changed_event_is_reflected_in_character_sheet(
    web_app: FastAPI, tmp_db_path: Path
) -> None:
    """`resource_changed` 사건을 하나 넣은 세션에서 시트의 그 축 `current`가
    시작값(만들기 완료 사건이 기록한 값)과 다르다 — 사건이 있는 세션에서만
    접은 값이 달라지고, 없는 세션(위
    `test_known_character_sheet_matches_characters_data`)에서는 여전히
    시작값과 같다는 것과 대칭이다."""
    entity = PLAYER_CHARACTERS["bram"]
    starting_hp = next(stat.current for stat in entity.stats if stat.name == "체력")

    _seed_character_created(tmp_db_path, "s1", "bram")
    store = EventStore(tmp_db_path)
    store.initialize()
    store.append(
        ResourceChanged(
            session_id="s1",
            seq=store.next_seq("s1"),
            schema_version=EVENT_SCHEMA_VERSION,
            caused_by_seq=None,
            recorded_at=utc_now_iso(),
            event_type="resource_changed",
            character_id="bram",
            changes=[
                {
                    "axis": "체력",
                    "operation": "delta",
                    "amount": -6,
                    "rolls": [],
                    "before": starting_hp,
                    "after": starting_hp - 6,
                }
            ],
            category_id=None,
            source="outcome_list",
        )
    )
    store.close()

    with TestClient(web_app) as client:
        response = client.get("/api/sessions/s1/characters/bram")

    assert response.status_code == 200
    body = response.json()
    hp_stat = next(stat for stat in body["stats"] if stat["name"] == "체력")
    assert hp_stat["current"] == starting_hp - 6
    assert hp_stat["current"] != starting_hp
