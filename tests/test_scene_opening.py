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

import json

from conftest import FakeProvider, lock_creation_roster, seed_character_created, select_character

from gptrpg.agents.envelope import AgentResult
from gptrpg.rulebooks.lamplight_vigil import LAMPLIGHT_VIGIL
from gptrpg.rulebooks.threat_clocks import WELL_BELOW, WELL_BELOW_ID
from gptrpg.rules_core.scenario import render_scripted_opening

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
    """상황판단·서술 둘 다 성공하고 생성된 글이 저자의 실마리 낱말을 실제로
    담으면 `source == "sketch"`이고 그 생성된 글이 그대로 기록된다."""
    action_classifier = FakeProvider(complete_value="[]")
    situation_judge = _situation_judge_provider()
    master_gm = FakeProvider(stream_text="우물 속에서 무언가 부드럽게 움직인다. 다들 숨을 죽이고 지켜본다.")
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
