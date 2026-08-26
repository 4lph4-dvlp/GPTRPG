"""겹친 요청이 GM 제공자를 두 번 부르는 결함을 닫는 시험(D-02/D-03, Phase 13-02).

**이 시험의 핵심은 사건 개수가 아니라 제공자 호출 횟수다.** 오늘의 결함은
「사건은 하나인데 AI 호출은 둘」이다(`_prepare_gm_spoke`의 큐 안 재검사가
사건은 하나로 접지만, 그 전에 이미 AI가 두 번 불린 뒤다) — 이 저장소가
12.3에서 아홉 차례 반복해 겪은 실패 모양(감시 장치가 「확인 못 한 것」을
「통과」로 접는 것)과 같은 종류다. 그래서 아래 가짜 제공자(`_CountingProvider`)
는 사건이 아니라 `complete()` 호출 횟수를 직접 센다.

**겹침 재현 방식.** `httpx.AsyncClient` + `ASGITransport` + `asyncio.gather`로
같은 이벤트 루프 안에서 진짜 동시 요청 둘을 띄운다(`tests/test_web_actions.py`
의 `test_concurrent_confirm_...`와 같은 조립 — `TestClient`는 스레드 포탈이라
진짜 동시성을 못 낸다). 가짜 제공자의 `complete()`에 짧은 `time.sleep`을
넣어 **첫 호출이 아직 안 끝난 동안 둘째가 사전 검사를 지나가게 만드는
창**을 연다 — 이 대기가 없으면 두 코루틴이 우연히 순차로 실행돼 시험이
거짓으로 초록이 될 수 있다(겹침이 재현되지 않은 채 통과).

`tests/test_web_actions.py::_make_app_with_fake_provider`와 같은 이유로
`TestClient`가 아니라 `create_app()`이 돌려주는 앱 자체를 다룬다.
"""

import asyncio
import json
import threading
import time
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from gptrpg.agents.envelope import AgentResult
from gptrpg.imagery import imagery_config_from_env
from gptrpg.web.app import create_app

SESSION_PREFIX = "gm-slot"

_ABILITY_ARRAY_PAYLOAD = {
    "axis_values": [
        {"axis_name": "STR", "value": 2},
        {"axis_name": "DEX", "value": 1},
        {"axis_name": "CON", "value": 1},
        {"axis_name": "INT", "value": 0},
        {"axis_name": "WIS", "value": 0},
        {"axis_name": "CHA", "value": -1},
    ]
}


class _CountingProvider:
    """`creation_gm` 역할 전용 가짜 제공자 — `complete()` 호출 **횟수**를
    센다(사건 개수가 아니다). `delay_s`만큼 각 호출 안에서 대기해 겹침
    재현 창을 연다. `fail_times`번까지는 예외를 던져 「제공자 실패」를
    흉내 낸다."""

    name = "gm-slot-counting-stub"

    def __init__(
        self, *, complete_value: str = "", delay_s: float = 0.0, fail_times: int = 0
    ) -> None:
        self.complete_value = complete_value
        self.delay_s = delay_s
        self.fail_times = fail_times
        self.call_count = 0
        self._lock = threading.Lock()

    def list_models(self) -> list[str]:
        return ["gm-slot-stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        with self._lock:
            self.call_count += 1
            n = self.call_count
        # 겹침 재현의 핵심 창 — 이 대기가 없으면 두 코루틴이 우연히
        # 순차로 실행돼 시험이 거짓으로 초록이 될 수 있다(§docstring).
        time.sleep(self.delay_s)
        if n <= self.fail_times:
            raise RuntimeError("gm slot stub provider unavailable")
        return AgentResult(
            ok=True, value=self.complete_value, elapsed_ms=2, prompt_tokens=1, completion_tokens=1
        )

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("creation_gm은 스트리밍하지 않는다")

    def last_result(self) -> AgentResult:
        raise NotImplementedError("이 이중체는 complete()만 시험한다")

    def note_result(self, result: AgentResult) -> None:  # pragma: no cover - 미사용
        pass


def _make_app(tmp_db_path: Path, tmp_path: Path, *, creation_gm: _CountingProvider):
    """`tests/conftest.web_client_with_fake_provider`와 같은 조립이지만
    `TestClient`로 감싸지 않고 앱 자체를 돌려준다(`tests/test_web_actions.py`
    의 `_make_app_with_fake_provider`와 같은 이유 — 진짜 동시성에는 앱을
    직접 다뤄야 한다)."""
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
    providers = {"creation_gm": creation_gm}

    def _resolver(role: str, choices, env):
        return providers.get(role, creation_gm)

    return create_app(
        db_path=tmp_db_path,
        provider_resolver=_resolver,
        agent_config_path=config_path,
        imagery_config=imagery_config_from_env({"GPTRPG_IMAGERY_DIR": str(tmp_path / "media")}),
    )


def _events(payload: dict, event_type: str) -> list[dict]:
    return [event for event in payload["events"] if event["event_type"] == event_type]


async def _get_events(client: AsyncClient, session_id: str) -> dict:
    response = await client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert response.status_code == 200, response.text
    return response.json()


async def _fix_party_size(
    client: AsyncClient, session_id: str, *, size: int, rulebook_id: str = "dungeonworld_like"
) -> None:
    response = await client.post(
        f"/api/sessions/{session_id}/creation/party-size",
        json={"player_character_count": size, "rulebook_id": rulebook_id},
    )
    assert response.status_code == 200, response.text


async def _submit_step(
    client: AsyncClient,
    session_id: str,
    character_id: str,
    browser_id: str,
    step_id: str,
    payload: dict,
    *,
    rulebook_id: str = "dungeonworld_like",
) -> None:
    body = {
        "character_id": character_id,
        "browser_id": browser_id,
        "step_id": step_id,
        "rulebook_id": rulebook_id,
        "text_value": None,
    }
    body.update(payload)
    response = await client.post(f"/api/sessions/{session_id}/creation/step", json=body)
    assert response.status_code == 200, response.text


async def _complete_character(
    client: AsyncClient,
    session_id: str,
    character_id: str,
    browser_id: str,
    name: str,
    *,
    rulebook_id: str = "dungeonworld_like",
) -> None:
    """`tests/conftest.lock_creation_roster`의 완성 단계를 async로 옮긴
    것 — 동의는 하지 않는다(동의하면 명단이 잠겨 `wrap_up`이 409가 된다,
    `announce`/`nominate`/`follow_up`도 마찬가지다)."""
    for step_id, payload in (
        ("archetype", {"picked": ["몸으로 먼저 막아선다"]}),
        ("backstory", {"text_value": "시험용 이야기"}),
        ("ability_array", _ABILITY_ARRAY_PAYLOAD),
        ("hp", {}),
        ("name", {"text_value": name}),
    ):
        await _submit_step(
            client, session_id, character_id, browser_id, step_id, payload, rulebook_id=rulebook_id
        )
    response = await client.post(
        f"/api/sessions/{session_id}/creation/complete",
        json={
            "character_id": character_id,
            "browser_id": browser_id,
            "rulebook_id": rulebook_id,
            "one_line_intro": f"{name}는 조용한 마을을 떠나온 모험가다.",
        },
    )
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# 겹친 요청 — 제공자 호출 1회, 사건 1건, 한쪽 200·다른 쪽 409
# ---------------------------------------------------------------------------


async def test_announce_overlap_calls_provider_exactly_once(tmp_db_path, tmp_path):
    """안내가 겹쳐도 제공자는 한 번만 불린다(D-02/D-03)."""
    provider = _CountingProvider(complete_value="필수 항목을 알려드릴게요.", delay_s=0.05)
    app = _make_app(tmp_db_path, tmp_path, creation_gm=provider)
    session_id = f"{SESSION_PREFIX}-announce-overlap"

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with (
            AsyncClient(transport=transport, base_url="http://test") as client_a,
            AsyncClient(transport=transport, base_url="http://test") as client_b,
        ):
            response_a, response_b = await asyncio.gather(
                client_a.post(f"/api/sessions/{session_id}/creation/announce", json={}),
                client_b.post(f"/api/sessions/{session_id}/creation/announce", json={}),
            )

        async with AsyncClient(transport=transport, base_url="http://test") as reader:
            events_payload = await _get_events(reader, session_id)

    assert provider.call_count == 1, (
        f"제공자가 {provider.call_count}번 불렸다 — 겹친 요청이 AI를 두 번 부른다(D-03 결함)"
    )
    assert sorted([response_a.status_code, response_b.status_code]) == [200, 409]
    assert len(_events(events_payload, "creation_gm_spoke")) == 1


async def test_nominate_overlap_calls_provider_exactly_once(tmp_db_path, tmp_path):
    """같은 후보 목록으로 지목이 겹쳐도 제공자는 한 번만 불린다."""
    provider = _CountingProvider(
        complete_value=json.dumps([{"character_id": "hero-1", "say": "이름1 님, 들려주세요."}]),
        delay_s=0.05,
    )
    app = _make_app(tmp_db_path, tmp_path, creation_gm=provider)
    session_id = f"{SESSION_PREFIX}-nominate-overlap"

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as setup_client:
            await _fix_party_size(setup_client, session_id, size=3)
            await _submit_step(
                setup_client,
                session_id,
                "hero-1",
                "b-hero-1",
                "archetype",
                {"picked": ["몸으로 먼저 막아선다"]},
            )

        async with (
            AsyncClient(transport=transport, base_url="http://test") as client_a,
            AsyncClient(transport=transport, base_url="http://test") as client_b,
        ):
            response_a, response_b = await asyncio.gather(
                client_a.post(f"/api/sessions/{session_id}/creation/nominate", json={}),
                client_b.post(f"/api/sessions/{session_id}/creation/nominate", json={}),
            )

        async with AsyncClient(transport=transport, base_url="http://test") as reader:
            events_payload = await _get_events(reader, session_id)

    assert provider.call_count == 1, (
        f"제공자가 {provider.call_count}번 불렸다 — 겹친 요청이 AI를 두 번 부른다(D-03 결함)"
    )
    assert sorted([response_a.status_code, response_b.status_code]) == [200, 409]
    assert len(_events(events_payload, "creation_gm_spoke")) == 1


async def test_follow_up_overlap_calls_provider_exactly_once(tmp_db_path, tmp_path):
    """같은 캐릭터로 되묻기가 겹쳐도 제공자는 한 번만 불린다."""
    provider = _CountingProvider(
        complete_value=json.dumps([{"needs_more": True, "question": "그다음엔 무슨 일이 있었나요?"}]),
        delay_s=0.05,
    )
    app = _make_app(tmp_db_path, tmp_path, creation_gm=provider)
    session_id = f"{SESSION_PREFIX}-follow-up-overlap"

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with (
            AsyncClient(transport=transport, base_url="http://test") as client_a,
            AsyncClient(transport=transport, base_url="http://test") as client_b,
        ):
            body = {"character_id": "hero-1"}
            response_a, response_b = await asyncio.gather(
                client_a.post(f"/api/sessions/{session_id}/creation/follow-up", json=body),
                client_b.post(f"/api/sessions/{session_id}/creation/follow-up", json=body),
            )

        async with AsyncClient(transport=transport, base_url="http://test") as reader:
            events_payload = await _get_events(reader, session_id)

    assert provider.call_count == 1, (
        f"제공자가 {provider.call_count}번 불렸다 — 겹친 요청이 AI를 두 번 부른다(D-03 결함)"
    )
    assert sorted([response_a.status_code, response_b.status_code]) == [200, 409]
    assert len(_events(events_payload, "creation_gm_spoke")) == 1


async def test_wrap_up_overlap_calls_provider_exactly_once(tmp_db_path, tmp_path):
    """정리가 겹쳐도 제공자는 한 번만 불린다."""
    provider = _CountingProvider(
        complete_value=json.dumps(
            [
                {
                    "say": "다들 준비되셨나요?",
                    "intros": [{"character_id": "hero-1", "intro": "용감한 모험가"}],
                }
            ]
        ),
        delay_s=0.05,
    )
    app = _make_app(tmp_db_path, tmp_path, creation_gm=provider)
    session_id = f"{SESSION_PREFIX}-wrap-up-overlap"

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as setup_client:
            await _fix_party_size(setup_client, session_id, size=3)
            await _complete_character(setup_client, session_id, "hero-1", "b-hero-1", "이름1")

        async with (
            AsyncClient(transport=transport, base_url="http://test") as client_a,
            AsyncClient(transport=transport, base_url="http://test") as client_b,
        ):
            response_a, response_b = await asyncio.gather(
                client_a.post(f"/api/sessions/{session_id}/creation/wrap-up", json={}),
                client_b.post(f"/api/sessions/{session_id}/creation/wrap-up", json={}),
            )

        async with AsyncClient(transport=transport, base_url="http://test") as reader:
            events_payload = await _get_events(reader, session_id)

    assert provider.call_count == 1, (
        f"제공자가 {provider.call_count}번 불렸다 — 겹친 요청이 AI를 두 번 부른다(D-03 결함)"
    )
    assert sorted([response_a.status_code, response_b.status_code]) == [200, 409]
    assert len(_events(events_payload, "creation_gm_spoke")) == 1


# ---------------------------------------------------------------------------
# 겹치지 않은 정상 경로 · 이미 말한 뒤 캐시 경로 — 회귀 없음
# ---------------------------------------------------------------------------


async def test_announce_normal_path_calls_provider_once_and_returns_message(
    tmp_db_path, tmp_path
):
    """겹치지 않은 정상 경로 — 한 번 부르고 끝나면 제공자 호출 1회 + 200 +
    지금과 같은 응답 모양(message/seq)."""
    provider = _CountingProvider(complete_value="필수 항목을 알려드릴게요.", delay_s=0.0)
    app = _make_app(tmp_db_path, tmp_path, creation_gm=provider)
    session_id = f"{SESSION_PREFIX}-announce-normal"

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/sessions/{session_id}/creation/announce", json={}
            )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["message"] == "필수 항목을 알려드릴게요."
    assert isinstance(body["seq"], int)
    assert provider.call_count == 1


async def test_announce_cache_path_calls_provider_zero_times_on_second_call(
    tmp_db_path, tmp_path
):
    """이미 말한 뒤 — 캐시 경로가 그대로 이긴다: 제공자 호출 0회, 200,
    지난 말 그대로(D-12 — 제공자 설정 문제가 있어도 캐시 응답에는 안
    닿는다)."""
    provider = _CountingProvider(complete_value="필수 항목을 알려드릴게요.", delay_s=0.0)
    app = _make_app(tmp_db_path, tmp_path, creation_gm=provider)
    session_id = f"{SESSION_PREFIX}-announce-cache"

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            first = await client.post(f"/api/sessions/{session_id}/creation/announce", json={})
            assert first.status_code == 200, first.text
            assert provider.call_count == 1

            second = await client.post(f"/api/sessions/{session_id}/creation/announce", json={})

    assert second.status_code == 200, second.text
    assert second.json() == first.json()
    assert provider.call_count == 1, "캐시가 있는데도 제공자를 다시 불렀다"


# ---------------------------------------------------------------------------
# 실패해도 슬롯이 풀린다 — 같은 키로 다시 부르면 막히지 않는다(T-13-08)
# ---------------------------------------------------------------------------


async def test_follow_up_provider_failure_does_not_leave_the_slot_stuck(tmp_db_path, tmp_path):
    """제공자가 두 번 다 실패하면 되묻기는 `needs_more=False`로 떨어지고
    **사건을 남기지 않는다**(캐시가 안 생긴다, D-02 ④). 그래서 같은
    키로 다시 부르면 캐시가 아니라 **슬롯을 다시 거친다** — 슬롯이 안
    풀렸다면 이 두 번째 호출이 영원히 409(`GmSlotBusy`)로 막힌다.
    `call_with_one_retry`가 한 번의 호출 안에서 이미 제공자를 2회
    부른다(1회 실패 + 1회 재시도, 둘 다 실패)."""
    provider = _CountingProvider(complete_value="", delay_s=0.0, fail_times=1_000_000)
    app = _make_app(tmp_db_path, tmp_path, creation_gm=provider)
    session_id = f"{SESSION_PREFIX}-follow-up-failure"

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            body = {"character_id": "hero-1"}

            first = await client.post(
                f"/api/sessions/{session_id}/creation/follow-up", json=body
            )
            assert first.status_code == 200, first.text
            assert first.json()["needs_more"] is False
            assert first.json()["gm_answered"] is False
            assert provider.call_count == 2, "call_with_one_retry가 정확히 두 번 시도해야 한다"

            second = await client.post(
                f"/api/sessions/{session_id}/creation/follow-up", json=body
            )

    assert second.status_code == 200, second.text  # 409면 슬롯이 안 풀린 것(T-13-08 위반)
    assert second.json()["needs_more"] is False
    assert provider.call_count == 4, "슬롯이 풀렸으면 두 번째 호출도 제공자를 다시 불러야 한다"
