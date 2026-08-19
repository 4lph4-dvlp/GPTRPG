"""도장 찍은 쪽지 하나가 선택 -> 선언 -> 확인 -> 판정까지 끝까지 도는지
확인하는 트레이서 시험 (08-01 Task 2).

`web_client_with_fake_provider` 픽스처를 쓴다(네트워크를 전혀 타지 않는다).
서명 쿠키는 직접 만들지 않고 실제 `select-character` 경로를 통해서만 얻는다
— 시험 전용 서명기를 쓰면 서명이 실제로 맞는지를 시험이 못 잡는다.

서버 재시작 재현은 같은 `EventStore` 경로 위에 `SessionRegistry`를 새로
만들어 `get_or_create`로 액터를 다시 얻는 방식으로 한다(`actor.py`가 그
자리에서 사건을 다시 접는다).
"""

import json

import pytest
from httpx import ASGITransport, AsyncClient

from conftest import FakeProvider
from conftest import seed_character_created as _seed_character_created
from gptrpg.session_actor.actor import CommandRejected, ConfirmAction, SessionRegistry
from gptrpg.web.cookie_auth import COOKIE_SECRET_FILENAME, verify_cookie

SESSION_ID = "s1"


def _declare_body(**overrides) -> dict:
    body = {
        "player_id": "p1",
        "character_id": "bram",
        "raw_text": "경비병을 설득해 통로를 열어 보려 한다",
        "rulebook_id": "dungeonworld_like",
    }
    body.update(overrides)
    return body


def _confirm_body(declare_seq: int, **overrides) -> dict:
    # `target`/`modifiers`는 `ConfirmRequest`에서 사라졌다(D-02, 12-01
    # Task 3) — `extra="forbid"`가 이 두 칸을 거절한다.
    body = {
        "player_id": "p1",
        "move": "parley",
        "stat": "CHA",
        "suggestion_move": "parley",
        "suggestion_stat": "CHA",
        "confirmed": True,
        "declare_seq": declare_seq,
        "rulebook_id": "dungeonworld_like",
        "character_id": "bram",
    }
    body.update(overrides)
    return body


def _select_character(client, character_id: str, session_id: str = SESSION_ID):
    """12.1-05부터 select-character가 통과하려면 그 캐릭터가 이 세션에서
    먼저 「만들어져」 있어야 한다(CHAR-02) — `seed_character_created`로
    시험 재료(`tests/fixtures/characters.py`)의 값을 먼저 심는다."""
    _seed_character_created(client.app.state.db_path, session_id, character_id)
    response = client.post(
        f"/api/sessions/{session_id}/select-character",
        json={"character_id": character_id},
    )
    assert response.status_code == 200
    return response


def _events_of_type(client, event_type: str, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events")
    assert response.status_code == 200
    return [event for event in response.json()["events"] if event["event_type"] == event_type]


def _classifier() -> FakeProvider:
    return FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))


# ---------------------------------------------------------------------------
# TRUST-01: 서명 쿠키는 위조 불가능하고, 변조되면 조용히 「고른 적 없음」이 된다
# ---------------------------------------------------------------------------


def test_select_character_cookie_is_not_plain_json(web_client_with_fake_provider) -> None:
    with web_client_with_fake_provider(action_classifier=_classifier()) as client:
        _select_character(client, "bram")
        raw = client.cookies.get("gptrpg_character")

    assert raw is not None
    assert "." in raw  # base64url(payload).hex(signature) — 점 하나로 나뉜 두 조각
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw)


def test_valid_cookie_returns_selected_true(web_client_with_fake_provider) -> None:
    with web_client_with_fake_provider(action_classifier=_classifier()) as client:
        _select_character(client, "bram")
        response = client.get(f"/api/sessions/{SESSION_ID}/my-character")

    assert response.status_code == 200
    assert response.json() == {"selected": True, "character_id": "bram"}


def test_tampered_cookie_char_returns_selected_false_not_an_exception(
    web_client_with_fake_provider,
) -> None:
    with web_client_with_fake_provider(action_classifier=_classifier()) as client:
        _select_character(client, "bram")
        raw = client.cookies.get("gptrpg_character")
        tampered = raw[:-1] + ("0" if raw[-1] != "0" else "1")
        client.cookies.set("gptrpg_character", tampered)
        response = client.get(f"/api/sessions/{SESSION_ID}/my-character")

    assert response.status_code == 200
    assert response.json() == {"selected": False, "character_id": None}


# ---------------------------------------------------------------------------
# TRUST-02/D-04: 라우트 계층이 요청의 캐릭터를 쿠키의 캐릭터와 대조한다
# ---------------------------------------------------------------------------


def test_declare_without_cookie_returns_403_and_no_event(web_client_with_fake_provider) -> None:
    with web_client_with_fake_provider(action_classifier=_classifier()) as client:
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare", json=_declare_body()
        )
        declared = _events_of_type(client, "action_declared")

    assert response.status_code == 403
    assert declared == []


def test_declare_with_mismatched_character_returns_403_and_no_event(
    web_client_with_fake_provider,
) -> None:
    with web_client_with_fake_provider(action_classifier=_classifier()) as client:
        _select_character(client, "bram")
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(character_id="nari"),
        )
        declared = _events_of_type(client, "action_declared")

    assert response.status_code == 403
    assert declared == []


def test_declare_with_matching_character_records_character_id(
    web_client_with_fake_provider,
) -> None:
    with web_client_with_fake_provider(action_classifier=_classifier()) as client:
        _select_character(client, "bram")
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(character_id="bram"),
        )
        declared = _events_of_type(client, "action_declared")

    assert response.status_code == 200
    assert len(declared) == 1
    assert declared[0]["character_id"] == "bram"


def test_confirm_with_mismatched_character_returns_403_at_route_layer(
    web_client_with_fake_provider,
) -> None:
    """라우트 계층이 먼저 막는다 — 쿠키의 캐릭터와 본문의 캐릭터가 어긋나면
    액터까지 가지도 않는다.

    08-02가 점유(D-05/D-07)를 실제로 강제하면서, 같은 브라우저가 bram을 쥔
    채로 nari를 다시 고르는 것은 이제 정당한 점유 충돌(409)이다 — 그래서
    nari는 **다른** 브라우저(별도 `TestClient`, 같은 `tmp_db_path` 위에서
    차례로 연다)가 잡는다. 그 다른 브라우저의 쿠키(nari)로 bram의 선언을
    확인하려 하면, 본문의 character_id(bram)와 쿠키(nari)가 어긋난다는
    이 시험의 원래 의도는 그대로 유지된다.
    """
    with web_client_with_fake_provider(action_classifier=_classifier()) as client:
        _select_character(client, "bram")
        declare_response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(character_id="bram"),
        )
        assert declare_response.status_code == 200
        declare_seq = declare_response.json()["declare_seq"]

    with web_client_with_fake_provider(action_classifier=_classifier()) as other_client:
        _select_character(other_client, "nari")
        response = other_client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(declare_seq, character_id="bram"),
        )
        confirmed = _events_of_type(other_client, "action_confirmed")

    assert response.status_code == 403
    assert confirmed == []


# ---------------------------------------------------------------------------
# TRUST-03: SessionActor가 최종 방어선이다 — 라우트를 우회해도 소유권이 지켜진다
# ---------------------------------------------------------------------------


async def _select_character_async(client, character_id: str, db_path, session_id: str = SESSION_ID):
    """12.1-05부터 select-character가 통과하려면 그 캐릭터가 이 세션에서
    먼저 「만들어져」 있어야 한다(CHAR-02). `httpx.AsyncClient`는
    `client.app`을 노출하지 않으므로(`TestClient`와 다르다) 호출부가
    `app.state.db_path`를 직접 넘긴다."""
    _seed_character_created(db_path, session_id, character_id)
    response = await client.post(
        f"/api/sessions/{session_id}/select-character",
        json={"character_id": character_id},
    )
    assert response.status_code == 200
    return response


async def test_actor_level_ownership_check_rejects_bypassing_route(
    web_client_with_fake_provider,
) -> None:
    """`TestClient`(동기)는 앱을 별도 포털 스레드/이벤트 루프에서 돌린다 —
    이 시험처럼 `actor.submit(...)`을 직접 `await`해야 하는 경우 `TestClient`와
    섞으면 다른 이벤트 루프에 매인 `asyncio.Queue`를 건드리게 되어 멎는다.
    `httpx.AsyncClient` + `ASGITransport`로 이 시험의 이벤트 루프 위에서
    lifespan까지 직접 돌려 한 루프 안에 머문다(RESEARCH.md의 신규 패턴)."""
    app = web_client_with_fake_provider(action_classifier=_classifier()).app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await _select_character_async(client, "bram", app.state.db_path)
            declare_response = await client.post(
                f"/api/sessions/{SESSION_ID}/actions/declare",
                json=_declare_body(character_id="bram"),
            )
            assert declare_response.status_code == 200
            declare_seq = declare_response.json()["declare_seq"]

            actor = app.state.registry.get_or_create(SESSION_ID)
            with pytest.raises(CommandRejected):
                await actor.submit(
                    ConfirmAction(
                        player_id="p-nari",
                        move="parley",
                        stat="CHA",
                        system_suggestion={"move": "parley", "stat": "CHA"},
                        player_confirmed=True,
                        caused_by_seq=declare_seq,
                        character_id="nari",
                    )
                )


async def test_actor_level_ownership_check_survives_actor_restart(
    web_client_with_fake_provider,
) -> None:
    """서버 재시작 재현 — Pitfall 1이 지적한 바로 그 상황(TRUST-03의 핵심)."""
    app = web_client_with_fake_provider(action_classifier=_classifier()).app
    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await _select_character_async(client, "bram", app.state.db_path)
            declare_response = await client.post(
                f"/api/sessions/{SESSION_ID}/actions/declare",
                json=_declare_body(character_id="bram"),
            )
            assert declare_response.status_code == 200
            declare_seq = declare_response.json()["declare_seq"]

            store = app.state.store
            fresh_registry = SessionRegistry(store)
            fresh_actor = fresh_registry.get_or_create(SESSION_ID)
            try:
                with pytest.raises(CommandRejected):
                    await fresh_actor.submit(
                        ConfirmAction(
                            player_id="p-nari",
                            move="parley",
                            stat="CHA",
                            system_suggestion={"move": "parley", "stat": "CHA"},
                            player_confirmed=True,
                            caused_by_seq=declare_seq,
                            character_id="nari",
                        )
                    )
            finally:
                await fresh_actor.stop()


# ---------------------------------------------------------------------------
# TRUST-04: check_resolved 사건에 「어느 브라우저가 · 어느 캐릭터로」가 남는다
# ---------------------------------------------------------------------------


def test_check_resolved_records_person_id_and_character_id(web_client_with_fake_provider) -> None:
    gm = FakeProvider(stream_text="문이 요란하게 부서진다.")
    with web_client_with_fake_provider(action_classifier=_classifier(), master_gm=gm) as client:
        _select_character(client, "bram")
        raw_cookie = client.cookies.get("gptrpg_character")
        payload = verify_cookie(raw_cookie, secret=client.app.state.cookie_secret)

        declare_response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(character_id="bram"),
        )
        declare_seq = declare_response.json()["declare_seq"]
        confirm_response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(declare_seq, character_id="bram"),
        )
        assert confirm_response.status_code == 200
        resolved = _events_of_type(client, "check_resolved")

    assert len(resolved) == 1
    assert resolved[0]["character_id"] == "bram"
    assert resolved[0]["person_id"] == payload["browser_id"]
    assert resolved[0]["person_id"]  # 비어 있지 않다


# ---------------------------------------------------------------------------
# D-02: 비밀 열쇠가 없으면 서버가 스스로 만들어 재사용한다. 환경변수가 있으면
# 그것이 우선한다.
# ---------------------------------------------------------------------------


def test_cookie_secret_persists_across_app_restarts_without_env_var(
    web_client_with_fake_provider, monkeypatch
) -> None:
    monkeypatch.delenv("GPTRPG_COOKIE_SECRET", raising=False)

    with web_client_with_fake_provider(action_classifier=_classifier()) as first_client:
        _select_character(first_client, "bram")
        raw_cookie = first_client.cookies.get("gptrpg_character")

    with web_client_with_fake_provider(action_classifier=_classifier()) as second_client:
        second_client.cookies.set("gptrpg_character", raw_cookie)
        response = second_client.get(f"/api/sessions/{SESSION_ID}/my-character")

    assert response.status_code == 200
    assert response.json() == {"selected": True, "character_id": "bram"}


def test_env_var_cookie_secret_overrides_file(
    web_client_with_fake_provider, monkeypatch, tmp_db_path
) -> None:
    monkeypatch.setenv("GPTRPG_COOKIE_SECRET", "env-secret-value-for-test")
    secret_file = tmp_db_path.parent / COOKIE_SECRET_FILENAME

    with web_client_with_fake_provider(action_classifier=_classifier()) as client:
        assert client.app.state.cookie_secret == b"env-secret-value-for-test"

    assert not secret_file.exists()
