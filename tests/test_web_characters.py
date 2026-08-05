"""캐릭터 목록·시트·선택·조회 네 경로 시험 (04-04).

`web_client`는 `tests/conftest.py`가 lifespan을 열어 주는 픽스처다 —
`EventStore`가 필요하지 않은 시험이지만(캐릭터 데이터는 저장소를 안 만짐)
같은 앱 인스턴스를 재사용해 라우터 등록 순서까지 실제와 같은 경로로
검증한다.
"""

from fastapi.testclient import TestClient

from gptrpg.web.characters_data import (
    CHARACTER_ARCHETYPES,
    NEW_CHARACTER_HP_BASE,
    NEW_CHARACTER_HP_PER_CON,
    NEW_CHARACTER_STAT_ARRAY,
    NEW_CHARACTER_STAT_NAMES,
    PLAYER_CHARACTERS,
)
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
