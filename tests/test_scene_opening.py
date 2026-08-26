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

**13-03 Task 3 — 메모형(`sketch`) 오프닝 시험.** `well_below`(등록소의
유일한 `sketch` 시나리오)를 대상으로 상황판단→서술 경로가 실제로 도는지,
검사에 걸리면 정확히 한 번 다시 만드는지, 제공자가 아예 실패하거나
설정 자체가 없으면 어떻게 떨어지는지 확인한다. `WELL_BELOW.opening.hook_terms`
(`"우물"`/`"염소"`/`"발자국"`)를 대조 손잡이로 그대로 쓴다 — 시험 전용
낱말을 새로 짓지 않는다.
"""

import asyncio
import json
import time

from conftest import FakeProvider, lock_creation_roster, seed_character_created, select_character
from httpx import ASGITransport, AsyncClient

from gptrpg.agents.envelope import AgentResult
from gptrpg.imagery import imagery_config_from_env
from gptrpg.rulebooks.lamplight_vigil import LAMPLIGHT_VIGIL
from gptrpg.rulebooks.threat_clocks import WELL_BELOW, WELL_BELOW_ID
from gptrpg.rules_core.scenario import render_scripted_opening
from gptrpg.web.app import create_app

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


# ---------------------------------------------------------------------------
# 메모형(sketch) 오프닝 — 상황판단 → 서술, 검사·재생성·폴백(13-03 Task 3)
# ---------------------------------------------------------------------------


def _situation_judge_provider(*, scene_summary: str = "우물가에 서늘한 정적이 감돈다.") -> FakeProvider:
    """`judge_opening_situation`이 파싱할 수 있는 닫힌 JSON 응답을 돌려주는
    가짜 상황판단 제공자."""
    return FakeProvider(
        complete_value=json.dumps([{"scene_summary": scene_summary, "facts": []}])
    )


class _StreamFailingProvider:
    """`master_gm` 역할 전용 이중체 — `stream()`이 (제너레이터를 만들기도
    전에) 매번 즉시 예외를 던진다. `complete()`는 이 시험에서 안 쓰인다."""

    name = "opening-stream-failing-stub"

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise RuntimeError("master_gm provider unavailable")

    def last_result(self) -> AgentResult:
        return AgentResult(ok=False, value=None, elapsed_ms=0, prompt_tokens=0, completion_tokens=0)

    def note_result(self, result: AgentResult) -> None:
        pass


def test_sketch_opening_succeeds_records_ai_generated_text_with_sketch_source(
    web_client_with_fake_provider,
):
    """상황판단·서술 둘 다 성공하고 생성된 글이 저자의 실마리 낱말과 초대를
    실제로 담으면 `source == "sketch"`이고 그 생성된 글이 그대로 기록된다.

    2026-08-26 verify-13-06 결함3 이후 `inspect_opening_completeness`가
    초대 신호(`missing_invitation`)도 보므로, 이 성공 경로의 이중체
    텍스트는 실마리 낱말("우물")과 초대(물음표로 끝나는 질문) 둘 다
    담아야 한다 — 하나라도 빠지면 D-09 폴백으로 떨어져 이 시험이 보려던
    "성공 경로"가 아니게 된다."""
    action_classifier = FakeProvider(complete_value="[]")
    situation_judge = _situation_judge_provider()
    master_gm = FakeProvider(
        stream_text="우물 속에서 무언가 부드럽게 움직인다. 다들 숨을 죽이고 지켜본다. 이제 무엇을 하겠는가?"
    )
    session_id = SESSION_ID + "-sketch-ok"
    with web_client_with_fake_provider(
        action_classifier=action_classifier, situation_judge=situation_judge, master_gm=master_gm
    ) as client:
        cookies = lock_creation_roster(client, session_id)
        client.cookies.clear()
        client.cookies.set("gptrpg_character", cookies["hero-1"])

        response = _open(client, "hero-1", session_id=session_id, scenario_id=WELL_BELOW_ID)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["opened"] is True
        assert body["source"] == "sketch"

        events = _opening_events(client, session_id=session_id)
        assert len(events) == 1
        event = events[0]
        assert event["scenario_id"] == WELL_BELOW_ID
        assert event["source"] == "sketch"
        assert event["text"].strip() != ""
        assert "우물" in event["text"]


def test_sketch_opening_fallback_to_authors_five_when_master_gm_provider_fails(
    web_client_with_fake_provider,
):
    """`master_gm` 제공자 호출 자체가 실패하면(연결 끊김 등) D-09 폴백 —
    HTTP 200, `source == "fallback"`, 텍스트는 저자의 다섯 칸 그대로다.
    화면에는 오류를 안 낸다."""
    action_classifier = FakeProvider(complete_value="[]")
    situation_judge = _situation_judge_provider()
    master_gm = _StreamFailingProvider()
    session_id = SESSION_ID + "-sketch-fallback-provider-failure"
    with web_client_with_fake_provider(
        action_classifier=action_classifier, situation_judge=situation_judge, master_gm=master_gm
    ) as client:
        cookies = lock_creation_roster(client, session_id)
        client.cookies.clear()
        client.cookies.set("gptrpg_character", cookies["hero-1"])

        response = _open(client, "hero-1", session_id=session_id, scenario_id=WELL_BELOW_ID)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["opened"] is True
        assert body["source"] == "fallback"

        events = _opening_events(client, session_id=session_id)
        assert len(events) == 1
        event = events[0]
        assert event["source"] == "fallback"
        assert event["text"] == render_scripted_opening(WELL_BELOW.opening)


def test_sketch_opening_regenerates_exactly_once_then_falls_back_when_hook_term_missing(
    web_client_with_fake_provider,
):
    """생성된 글이 저자의 실마리 낱말을 하나도 담지 않으면(D-08, Task 1
    ⓐ) 같은 facts로 정확히 한 번 다시 만들고, 그래도 안 담으면 D-09
    폴백으로 떨어진다 — 제공자 `stream()`이 정확히 2회 불린다(10-03 상한
    3회보다 좁다)."""
    action_classifier = FakeProvider(complete_value="[]")
    situation_judge = _situation_judge_provider()
    master_gm = FakeProvider(stream_text="복도가 조용하다. 아무 일도 없어 보인다.")
    session_id = SESSION_ID + "-sketch-regenerate-then-fallback"
    with web_client_with_fake_provider(
        action_classifier=action_classifier, situation_judge=situation_judge, master_gm=master_gm
    ) as client:
        cookies = lock_creation_roster(client, session_id)
        client.cookies.clear()
        client.cookies.set("gptrpg_character", cookies["hero-1"])

        response = _open(client, "hero-1", session_id=session_id, scenario_id=WELL_BELOW_ID)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["source"] == "fallback"

        assert len(master_gm.calls) == 2

        events = _opening_events(client, session_id=session_id)
        assert len(events) == 1
        assert events[0]["source"] == "fallback"
        assert events[0]["text"] == render_scripted_opening(WELL_BELOW.opening)


def test_sketch_opening_returns_503_and_records_nothing_when_provider_not_configured(
    tmp_db_path, tmp_path
):
    """제공자 설정 자체가 없으면(D-09 ②갈래, 12.3 D-13) 503이고 사건이
    안 생긴다. `web_client_with_fake_provider`는 항상 대역으로 채워 이
    갈래를 낼 수 없으므로 `create_app`을 직접 다뤄 `situation_judge` 해석이
    실패하는 앱을 조립한다(`tests/test_gm_slot.py::_CountingProvider` 조립
    방식과 같다)."""
    from starlette.testclient import TestClient

    from gptrpg.agents.providers import MissingApiKey
    from gptrpg.imagery import imagery_config_from_env
    from gptrpg.web.app import create_app

    config_path = tmp_path / "agents.json"
    config_path.write_text(
        json.dumps(
            {
                "action_classifier": {"provider": "nim", "model": "fake-model"},
                "master_gm": {"provider": "nim", "model": "fake-model"},
            }
        ),
        encoding="utf-8",
    )
    action_classifier = FakeProvider(complete_value="[]")

    def _resolver(role: str, choices, env):
        if role == "situation_judge":
            raise MissingApiKey("situation_judge", "NVIDIA_API_KEY")
        return action_classifier

    app = create_app(
        db_path=tmp_db_path,
        provider_resolver=_resolver,
        agent_config_path=config_path,
        imagery_config=imagery_config_from_env({"GPTRPG_IMAGERY_DIR": str(tmp_path / "media")}),
    )
    session_id = SESSION_ID + "-sketch-no-provider"
    with TestClient(app) as client:
        cookies = lock_creation_roster(client, session_id)
        client.cookies.clear()
        client.cookies.set("gptrpg_character", cookies["hero-1"])

        response = _open(client, "hero-1", session_id=session_id, scenario_id=WELL_BELOW_ID)
        assert response.status_code == 503, response.text

        assert _opening_events(client, session_id=session_id) == []


# ---------------------------------------------------------------------------
# verify-13-06 결함4 — 오프닝의 블로킹 AI 호출이 이벤트 루프를 막아 다른
# 브라우저의 폴링까지 정지시키던 회귀(T-04-06과 같은 실패 모양).
# ---------------------------------------------------------------------------


class _SlowSituationJudgeProvider:
    """`situation_judge` 전용 이중체 — `complete()`가 `delay_s`만큼 실제로
    블로킹(`time.sleep`)한 뒤 응답한다. `judge_opening_situation`이
    `asyncio.to_thread`로 옮겨지지 않았으면 이 sleep이 이벤트 루프
    자체를 막는다 — 그 사실을 `test_opening_sketch_scene_does_not_block_the_event_loop_during_slow_ai_calls`가 잡는다."""

    name = "opening-slow-situation-judge"

    def __init__(self, *, delay_s: float, scene_summary: str = "우물가에 서늘한 정적이 감돈다.") -> None:
        self.delay_s = delay_s
        self.scene_summary = scene_summary

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        time.sleep(self.delay_s)
        return AgentResult(
            ok=True,
            value=json.dumps([{"scene_summary": self.scene_summary, "facts": []}]),
            elapsed_ms=int(self.delay_s * 1000),
            prompt_tokens=1,
            completion_tokens=1,
        )

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("이 이중체는 complete()만 시험한다")

    def last_result(self) -> AgentResult:
        raise NotImplementedError("이 이중체는 complete()만 시험한다")

    def note_result(self, result: AgentResult) -> None:  # pragma: no cover - 미사용
        pass


def _make_opening_test_app(tmp_db_path, tmp_path, *, situation_judge, master_gm, action_classifier):
    """`tests/test_gm_slot.py::_make_app`과 같은 조립 — `TestClient`(스레드
    포탈)를 거치지 않고 앱 자체를 돌려준다. `TestClient`가 만든 sqlite
    연결은 포탈의 배경 스레드에 묶이므로, 이 시험처럼 진짜 동시 `httpx.AsyncClient`
    호출 둘을 같은 이벤트 루프에서 띄우면(`asyncio.gather`) 그 연결을 다른
    스레드에서 건드리게 되어 `sqlite3.ProgrammingError`가 난다 — 그래서
    앱을 직접 만들고 `app.router.lifespan_context(app)`을 이 시험 함수
    **자신의** 이벤트 루프 안에서 연다."""
    config_path = tmp_path / "agents.json"
    config_path.write_text(
        json.dumps(
            {
                "action_classifier": {"provider": "nim", "model": "fake-model"},
                "master_gm": {"provider": "nim", "model": "fake-model"},
            }
        ),
        encoding="utf-8",
    )
    providers = {
        "action_classifier": action_classifier,
        "situation_judge": situation_judge,
        "master_gm": master_gm,
    }

    def _resolver(role: str, choices, env):
        return providers.get(role, action_classifier)

    return create_app(
        db_path=tmp_db_path,
        provider_resolver=_resolver,
        agent_config_path=config_path,
        imagery_config=imagery_config_from_env({"GPTRPG_IMAGERY_DIR": str(tmp_path / "media")}),
    )


async def _async_lock_creation_roster(client: AsyncClient, session_id: str) -> str:
    """`tests/conftest.lock_creation_roster`의 async 판 — 한 명(`hero-1`)짜리
    파티를 만들어 명단을 잠근다(`dungeonworld_like`의 최소 인원이 3명이라
    실제로는 세 명 다 완성·동의해야 한다). 서명 쿠키(`hero-1`)를 돌려준다."""
    party = [(f"hero-{n}", f"b-hero-{n}", f"이름{n}") for n in range(1, 4)]
    steps: tuple[tuple[str, dict], ...] = (
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
    )

    response = await client.post(
        f"/api/sessions/{session_id}/creation/party-size",
        json={"player_character_count": 3, "rulebook_id": "dungeonworld_like"},
    )
    assert response.status_code == 200, response.text

    cookies: dict[str, str] = {}
    for character_id, browser_id, name in party:
        # 이전 캐릭터가 `/complete`에서 구운 쿠키를 여기서 지운다 — 안 지우면
        # 다음 캐릭터의 첫 항목 제출이 「쿠키 불일치」 403을 받는다(동기판
        # `lock_creation_roster`의 `client.cookies.clear()`와 같은 이유).
        client.cookies.clear()
        for step_id, payload in (*steps, ("name", {"text_value": name})):
            body = {
                "character_id": character_id,
                "browser_id": browser_id,
                "step_id": step_id,
                "rulebook_id": "dungeonworld_like",
                "text_value": None,
            }
            body.update(payload)
            step_response = await client.post(f"/api/sessions/{session_id}/creation/step", json=body)
            assert step_response.status_code == 200, step_response.text
        complete_response = await client.post(
            f"/api/sessions/{session_id}/creation/complete",
            json={
                "character_id": character_id,
                "browser_id": browser_id,
                "rulebook_id": "dungeonworld_like",
                "one_line_intro": f"{name}는 조용한 마을을 떠나온 모험가다.",
            },
        )
        assert complete_response.status_code == 200, complete_response.text
        cookies[character_id] = complete_response.cookies.get("gptrpg_character")

    for character_id, browser_id, _name in party:
        client.cookies.clear()
        client.cookies.set("gptrpg_character", cookies[character_id])
        consent_response = await client.post(
            f"/api/sessions/{session_id}/creation/consent",
            json={"character_id": character_id, "browser_id": browser_id, "agree": True},
        )
        assert consent_response.status_code == 200, consent_response.text
    assert consent_response.json()["locked"] is True, "정원 전원 동의에서 잠겨야 한다"
    return cookies["hero-1"]


async def test_opening_sketch_scene_does_not_block_the_event_loop_during_slow_ai_calls(
    tmp_db_path, tmp_path
):
    """오프닝의 상황판단/서술 호출이 이벤트 루프를 막지 않는다(T-04-06,
    verify-13-06 결함4 회귀). `httpx.AsyncClient` + `asyncio.gather`로 실제
    동시 요청 둘을 같은 이벤트 루프에서 띄운다(`TestClient`는 스레드
    포탈이라 진짜 동시성을 못 낸다 — `tests/test_gm_slot.py` 도크스트링과
    같은 이유).

    `situation_judge`가 0.5초 동안 실제로 블로킹(`time.sleep`)하는 동안,
    **완전히 무관한 가벼운 폴링 요청**(`GET .../events`)이 같은 이벤트
    루프에서 함께 돈다. 고치기 전에는 이 폴링도 situation_judge의 sleep이
    끝날 때까지 멎어 있었다 — 다른 세 브라우저의 화면이 오프닝이 끝날
    때까지 캐릭터 생성 화면에 멈춰 있던 정확한 원인이다. 고친 뒤에는
    폴링이 situation_judge의 지연과 무관하게 빨리 끝나야 한다."""
    action_classifier = FakeProvider(complete_value="[]")
    situation_judge = _SlowSituationJudgeProvider(delay_s=0.5)
    master_gm = FakeProvider(
        stream_text="우물 속에서 무언가 부드럽게 움직인다. 이제 무엇을 하겠는가?"
    )
    session_id = SESSION_ID + "-sketch-does-not-block-loop"
    app = _make_opening_test_app(
        tmp_db_path,
        tmp_path,
        situation_judge=situation_judge,
        master_gm=master_gm,
        action_classifier=action_classifier,
    )

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as setup_client:
            character_cookie = await _async_lock_creation_roster(setup_client, session_id)

        async with (
            AsyncClient(
                transport=transport,
                base_url="http://test",
                cookies={"gptrpg_character": character_cookie},
            ) as opening_client,
            AsyncClient(transport=transport, base_url="http://test") as poll_client,
        ):

            async def _call_opening():
                return await opening_client.post(
                    f"/api/sessions/{session_id}/opening",
                    json={"character_id": "hero-1", "scenario_id": WELL_BELOW_ID},
                )

            # **바깥(gather 밖)에서 잰다.** 이벤트 루프가 막히면 `_poll_...`
            # 코루틴 자신도 재개되지 못하므로, 그 안에서 `time.monotonic()`을
            # 부르면 시작 시각 자체가 막힌 만큼 밀려 찍혀 경과 시간이
            # 거꾸로 **짧게** 측정된다(이 시험을 처음 짤 때 실제로 겪은
            # 실수 — 봉쇄 전 코드로도 통과하는 거짓 초록이었다). 그래서
            # 두 코루틴이 시작되기 **전**, `gather` 밖에서 기준 시각을 하나
            # 잡고 폴링 완료 시각까지의 전체 경과를 그 기준으로 잰다.
            overall_start = time.monotonic()

            async def _poll_while_opening_is_in_flight():
                # 오프닝이 슬롯을 먼저 잡을 시간을 아주 조금 준다 — 순서를
                # 보장해야 "느린 호출이 진행 중"이라는 전제가 성립한다.
                await asyncio.sleep(0.05)
                response = await poll_client.get(
                    f"/api/sessions/{session_id}/events", params={"from_seq": 0}
                )
                return response, time.monotonic() - overall_start

            opening_response, (poll_response, poll_elapsed) = await asyncio.gather(
                _call_opening(), _poll_while_opening_is_in_flight()
            )

    assert opening_response.status_code == 200, opening_response.text
    assert poll_response.status_code == 200, poll_response.text
    # situation_judge 혼자만으로도 0.5초를 블로킹한다. 안 막혔으면 폴링은
    # 자기 몫의 사전 대기(0.05초) + 가벼운 GET 하나(수 ms)만큼, 대략
    # 0.1초 안쪽에 끝난다. 막혔으면 situation_judge의 블로킹이 끝날 때까지
    # (오프닝 응답이 돌아올 때까지) 아예 시작도 못 하므로 0.5초에 가깝게
    # 걸린다 — 둘 사이 확실히 갈리는 문턱(0.3초)으로 가른다.
    assert poll_elapsed < 0.3, (
        f"폴링이 전체 기준으로 {poll_elapsed:.3f}초 걸렸다 — 오프닝의 AI 호출이 이벤트 루프를 막았다"
        "(verify-13-06 결함4)"
    )
