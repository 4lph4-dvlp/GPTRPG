"""웹에서 확인 요청 한 번이 「이야기 조건」으로 시계를 한 칸 돌린다 — 09-01 Task 1.

한 줄기 끝까지: 판단(`agents.clock_judge`) → 배경 실행(`turn.clock_condition`) →
사건 기록(`session_actor`) → 재생(`event_log`)까지 실제로 통과하는지가 이
파일의 증거다. `TestClient`는 `BackgroundTasks`를 응답 반환 시점에 동기적으로
돌리므로 요청이 끝난 직후 저장소를 읽으면 배경 산출물을 볼 수 있다.
"""

import json

from fastapi.testclient import TestClient

from conftest import FakeProvider
from conftest import select_character as _select_character_at
from gptrpg.agents.envelope import AgentResult
from gptrpg.event_log.schema import EVENT_SCHEMA_VERSION
from gptrpg.event_log.store import EventStore
from gptrpg.session_actor.projection import rebuild_state
from gptrpg.turn.context import CLOCK_SEGMENT_COUNT

SESSION_ID = "s1"

_NARRATION_TEXT = "문이 요란하게 부서진다. 안에서 서늘한 바람이 흘러나온다."


class _ClockJudgeDouble:
    """`clock_judge` 역할 전용 대역 — 관문 호출과 깊은 판단 호출을 호출 순서로 구분한다.

    호출은 관문(`judge_clock_signal`)·깊은 판단(`judge_clock_condition`)이
    한 턴에 정확히 한 번씩(신호가 "check"일 때만 두 번째) 번갈아 일어난다는
    것을 이용해 **홀수 번째 호출 = 관문, 짝수 번째 호출 = 깊은 판단**으로
    구분한다 — 여러 턴을 연달아 돌리는 시험(상한 검사)에서도 매 턴 같은
    패턴이 반복되므로 그대로 맞는다. `always_raise`면 매번 예외를 던진다
    (D-05 실패 경로 시험용).
    """

    name = "clock-judge-double"

    def __init__(
        self,
        *,
        signal_response: str = json.dumps([{"signal": "check", "why": "판정이 다음 칸과 관련 있다"}]),
        condition_response: str = json.dumps([{"verdict": "advance", "why": "조건이 충족됐다"}]),
        always_raise: bool = False,
    ) -> None:
        self.signal_response = signal_response
        self.condition_response = condition_response
        self.always_raise = always_raise
        self.calls: list[tuple[list[dict], list[dict]]] = []

    def list_models(self) -> list[str]:
        return ["clock-judge-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        self.calls.append((system, messages))
        if self.always_raise:
            raise RuntimeError("clock judge double가 일부러 실패한다")
        is_signal_call = len(self.calls) % 2 == 1
        value = self.signal_response if is_signal_call else self.condition_response
        return AgentResult(ok=True, value=value, elapsed_ms=3, prompt_tokens=2, completion_tokens=2)

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("clock_judge는 스트리밍하지 않는다")

    def last_result(self) -> AgentResult:
        raise NotImplementedError("clock_judge 대역은 last_result()를 쓰지 않는다")

    def note_result(self, result: AgentResult) -> None:
        pass


def _events(client: TestClient, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events")
    assert response.status_code == 200
    return response.json()["events"]


def _events_of_type(client: TestClient, event_type: str, session_id: str = SESSION_ID) -> list[dict]:
    return [event for event in _events(client, session_id) if event["event_type"] == event_type]


def _declare_body(**overrides) -> dict:
    body = {
        "player_id": "bram",
        "character_id": "bram",
        "raw_text": "경비병을 설득해 통로를 열어 보려 한다",
    }
    body.update(overrides)
    return body


def _select_character(client: TestClient, character_id: str, session_id: str = SESSION_ID) -> None:
    _select_character_at(client, session_id, character_id)


def _declare(client: TestClient, **overrides):
    body = _declare_body(**overrides)
    _select_character(client, body["character_id"])
    return client.post(f"/api/sessions/{SESSION_ID}/actions/declare", json=body)


def _declare_first(client: TestClient, **overrides) -> int:
    response = _declare(client, **overrides)
    assert response.status_code == 200
    return response.json()["declare_seq"]


def _confirm_body(declare_seq: int, **overrides) -> dict:
    # `target`/`modifiers`는 `ConfirmRequest`에서 사라졌다(D-02, 12-01
    # Task 3) — `extra="forbid"`가 이 두 칸을 거절한다.
    body = {
        "player_id": "bram",
        "move": "parley",
        "stat": "CHA",
        "suggestion_move": "parley",
        "suggestion_stat": "CHA",
        "confirmed": True,
        "declare_seq": declare_seq,
        "character_id": "bram",
    }
    body.update(overrides)
    return body


def test_confirm_advances_clock_via_condition_trigger_and_replays(
    web_client_with_fake_provider,
) -> None:
    """한 번의 confirm 요청 뒤, 저장소에 `clock_advanced(trigger="condition")`
    사건이 정확히 하나 있고 재생한 `clock_segment`가 1이다 (ARCH-03)."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    clock_judge = _ClockJudgeDouble()
    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, clock_judge=clock_judge
    ) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        body = response.json()
        assert body["narration_failed"] is False

        clock_advanced = _events_of_type(client, "clock_advanced")

    assert len(clock_advanced) == 1
    assert clock_advanced[0]["trigger"] == "condition"
    assert clock_advanced[0]["caused_by_seq"] == body["resolve_seq"]


def test_replayed_clock_segment_is_one_after_condition_advance(
    web_client_with_fake_provider, tmp_db_path
) -> None:
    """같은 시험을 저장소를 직접 열어 재생까지 확인한다 — 배경 산출물이
    재생으로 복원된다는 ARCH-03의 증거다."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    clock_judge = _ClockJudgeDouble()
    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, clock_judge=clock_judge
    ) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200

    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        state = rebuild_state(store, SESSION_ID)
    finally:
        store.close()
    assert state.clock_segment == 1


def test_event_schema_version_at_least_six() -> None:
    """DP-04(Phase 9) — 위협 시계 조건 검사 자체는 새 사건 종류도 판 올림도
    필요 없었다(그래서 Phase 9 시점에는 5였다). 판이 6으로 오른 것은 Phase 10
    (`safety_flagged`, SAFE-01/03) 때문이지 이 갈래가 다시 올린 것이 아니다 —
    이 시험은 그 사실이 뒤집히지 않았음(위협 시계 조건 검사가 스스로 판을
    또 올리지 않는다)만 확인한다."""
    assert EVENT_SCHEMA_VERSION >= 6


def test_clock_segment_count_unchanged() -> None:
    assert CLOCK_SEGMENT_COUNT == 4


# ---------------------------------------------------------------------------
# 09-01 Task 3 — 판단이 늦거나 죽어도 턴은 끝까지 간다 (ARCH-05/D-05)
# ---------------------------------------------------------------------------


def test_clock_judge_always_raising_still_returns_200_and_records_no_clock_event(
    web_client_with_fake_provider,
) -> None:
    """판단이 매번 예외를 던져도 confirm 응답은 200이고 `narration_failed`가
    참이 아니며, `clock_advanced` 사건이 하나도 없다."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    clock_judge = _ClockJudgeDouble(always_raise=True)
    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, clock_judge=clock_judge
    ) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        body = response.json()
        assert body["narration_failed"] is False
        # 판단 실패를 알리는 값이 응답 본문 어느 칸에도 없다.
        assert "clock" not in json.dumps(body).lower()

        clock_advanced = _events_of_type(client, "clock_advanced")

    assert clock_advanced == []


def test_signal_skip_registers_no_background_task_and_never_calls_deep_judgment(
    web_client_with_fake_provider,
) -> None:
    """신호가 `"skip"`이면 배경 작업이 아예 등록되지 않는다 — `clock_advanced`
    사건이 없고, 깊은 판단용 제공자 호출이 한 번도 일어나지 않는다(대역의
    호출 횟수로 단언, DP-01의 관문 구조 그대로)."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    clock_judge = _ClockJudgeDouble(
        signal_response=json.dumps([{"signal": "skip", "why": "이번 턴은 무관하다"}])
    )
    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, clock_judge=clock_judge
    ) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200

        clock_advanced = _events_of_type(client, "clock_advanced")

    assert clock_advanced == []
    # 관문 호출(신호) 딱 한 번만 있었다 — 깊은 판단(두 번째 호출)이 없었다.
    assert len(clock_judge.calls) == 1


def test_deep_judgment_raising_still_returns_200_and_records_no_clock_event(
    web_client_with_fake_provider,
) -> None:
    """관문은 통과했지만 배경의 깊은 판단이 예외를 던지는 경우: 요청은
    200으로 끝났고 `clock_advanced` 사건이 없으며, 예외가 요청 처리로 새어
    나오지 않는다."""

    class _SignalOkThenRaisesDouble(_ClockJudgeDouble):
        def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
            self.calls.append((system, messages))
            if len(self.calls) == 1:
                return AgentResult(
                    ok=True, value=self.signal_response, elapsed_ms=2, prompt_tokens=1, completion_tokens=1
                )
            raise RuntimeError("깊은 판단이 일부러 실패한다")

    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    clock_judge = _SignalOkThenRaisesDouble()
    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, clock_judge=clock_judge
    ) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200

        clock_advanced = _events_of_type(client, "clock_advanced")

    assert clock_advanced == []


def test_clock_at_last_segment_condition_met_still_adds_no_event(
    web_client_with_fake_provider,
) -> None:
    """상한 검사 — 시계가 이미 마지막 칸에 있는 세션에서 조건이 충족돼도
    `clock_advanced` 사건이 추가로 생기지 않는다.

    `run_clock_condition_check`는 `actor.state.clock_segment`(실제로 명령을
    처리해 온 액터의 캐시된 상태)를 본다 — 사건을 저장소에 직접 꽂아 넣으면
    액터의 상태와 저장소가 어긋나 시험이 실제 상한 검사 코드 경로를 타지
    않는다. 그래서 진짜 확인 요청을 `CLOCK_SEGMENT_COUNT + 1`번 연달아
    보내 시계를 실제로 마지막 칸까지 돌린 뒤, 그다음 요청에서 다섯 번째
    사건이 추가되지 않는 것을 확인한다."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    clock_judge = _ClockJudgeDouble()
    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, clock_judge=clock_judge
    ) as client:
        for _ in range(CLOCK_SEGMENT_COUNT + 1):
            declare_seq = _declare_first(client)
            response = client.post(
                f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
            )
            assert response.status_code == 200

        clock_advanced = _events_of_type(client, "clock_advanced")

    # 시계 칸 수만큼만 진행됐다 — 상한을 넘긴 다섯 번째 진행은 없다.
    assert len(clock_advanced) == CLOCK_SEGMENT_COUNT


def test_condition_advance_segment_index_ignores_any_number_embedded_in_why(
    web_client_with_fake_provider,
) -> None:
    """D14 경계 — 조건 충족으로 기록된 `clock_advanced`의 `segment_index`가
    직전 `clock_segment`보다 정확히 1 크다. 대역 응답의 `why` 칸에 전혀 다른
    숫자를 문자열로 넣어 둬도 그 값이 사건 어디에도 나타나지 않는다."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    clock_judge = _ClockJudgeDouble(
        condition_response=json.dumps(
            [{"verdict": "advance", "why": "AI 생각으로는 시계가 999칸으로 가야 한다"}]
        )
    )
    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=gm, clock_judge=clock_judge
    ) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200

        clock_advanced = _events_of_type(client, "clock_advanced")

    assert len(clock_advanced) == 1
    assert clock_advanced[0]["segment_index"] == 1
    assert "999" not in json.dumps(clock_advanced[0])
