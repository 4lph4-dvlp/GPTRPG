"""같은 배경 검사를 CLI에서도 돌린다 — 09-01 Task 2.

Pitfall 1 회귀 방지가 목적이다: `run_clock_condition_check`을 `await`하지
않고 `asyncio.create_task`로 던지면, `asyncio.run()`이 반환하는 순간
이벤트 루프가 닫혀 배경 산출물이 스케줄되다 말거나 아예 스케줄되지 못한
채 사라진다 — `run_turn` **반환 이후** 새로 연 `EventStore`로 다시 읽어야
이 회귀를 실제로 잡을 수 있다.

`tests/test_turn_flow_failure.py`의 골격(대역 제공자 + 임시 저장소 +
`main([...])` 직접 호출)을 그대로 빌린다.
"""

import json
import threading

from gptrpg.agents import providers as providers_module
from gptrpg.agents.envelope import AgentResult
from gptrpg.cli.main import main
from gptrpg.event_log.schema import EVENT_SCHEMA_VERSION
from gptrpg.event_log.store import EventStore
from gptrpg.session_actor.projection import rebuild_state

_CANDIDATE_JSON = json.dumps([{"move": "hack_and_slash", "stat": "STR"}])
_SIGNAL_CHECK_JSON = json.dumps([{"signal": "check", "why": "판정이 다음 칸과 관련 있다"}])
_SIGNAL_SKIP_JSON = json.dumps([{"signal": "skip", "why": "이번 턴은 무관하다"}])
_VERDICT_ADVANCE_JSON = json.dumps([{"verdict": "advance", "why": "조건이 충족됐다"}])
_SITUATION_JSON = json.dumps([{"scene_summary": "", "facts": []}])


def _install_fake_provider(monkeypatch, fake_provider, *, name="fake", env_var="FAKE_API_KEY"):
    monkeypatch.setitem(providers_module.PROVIDER_ENV_VARS, name, env_var)
    monkeypatch.setitem(providers_module.PROVIDER_FACTORIES, name, lambda api_key: fake_provider)
    monkeypatch.setenv(env_var, "test-key")


def _run_turn(db: str, session: str, text: str, *, monkeypatch) -> int:
    monkeypatch.setattr("builtins.input", lambda *_args: "")
    return main(
        [
            "turn",
            "--db",
            db,
            "--session",
            session,
            "--player",
            "p1",
            "--text",
            text,
            "--provider",
            "fake",
            "--model",
            "fake-model",
        ]
    )


def _read_events(db: str, session: str):
    store = EventStore(db)
    store.initialize()
    try:
        return store.read_events(session)
    finally:
        store.close()


class _MultiRoleProvider:
    """`--provider fake --model fake-model`이 네 역할(action_classifier/
    situation_judge/master_gm/clock_judge) 전부에 같은 제공자 이름을 쓰게
    만드는 대역 하나가 필요하다.

    09-02부터는 `situation_judge`와 `clock_judge`(관문)가 `asyncio.gather`로
    **동시에** 돈다(ARCH-04) — 두 판단이 같은 이 대역 인스턴스의 `complete()`를
    스레드 둘에서 부르므로, "호출 순서"로 역할을 가리는 방식은 더 이상
    안전하지 않다(레이스). 그래서 `system` 프롬프트에 실린 역할 지시문
    텍스트(각 `build_*_prompt`가 박아 넣는 고정 문구, `prompt_assembly.py`
    참조)로 역할을 가린다 — 어느 스레드가 먼저 들어와도 항상 맞는 값을
    돌려준다. `stream()`은 `master_gm.narrate()` 전용이라 `complete()`와
    호출 수를 공유하지 않는다.
    """

    name = "fake"

    def __init__(
        self,
        *,
        classify_value: str = _CANDIDATE_JSON,
        situation_value: str = _SITUATION_JSON,
        signal_value: str = _SIGNAL_CHECK_JSON,
        condition_value: str = _VERDICT_ADVANCE_JSON,
        stream_text: str = "문이 요란하게 부서진다. 안에서 서늘한 바람이 흘러나온다.",
        clock_judge_always_raises: bool = False,
    ) -> None:
        self.classify_value = classify_value
        self.situation_value = situation_value
        self.signal_value = signal_value
        self.condition_value = condition_value
        self.stream_text = stream_text
        self.clock_judge_always_raises = clock_judge_always_raises
        self.complete_calls = 0
        self._lock = threading.Lock()
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        with self._lock:
            self.complete_calls += 1
        combined_system = " ".join(block.get("text", "") for block in system)

        if "행동 분류기" in combined_system:
            return AgentResult(
                ok=True, value=self.classify_value, elapsed_ms=1, prompt_tokens=1, completion_tokens=1
            )
        if "상황판단 담당" in combined_system:
            return AgentResult(
                ok=True, value=self.situation_value, elapsed_ms=1, prompt_tokens=1, completion_tokens=1
            )
        if "위협 시계 관문 판단자" in combined_system:
            if self.clock_judge_always_raises:
                raise RuntimeError("clock judge 대역이 일부러 실패한다")
            return AgentResult(
                ok=True, value=self.signal_value, elapsed_ms=1, prompt_tokens=1, completion_tokens=1
            )
        if "위협 시계 조건 판단자" in combined_system:
            if self.clock_judge_always_raises:
                raise RuntimeError("clock judge 대역이 일부러 실패한다")
            return AgentResult(
                ok=True, value=self.condition_value, elapsed_ms=1, prompt_tokens=1, completion_tokens=1
            )
        raise AssertionError(f"알 수 없는 역할의 프롬프트: {combined_system[:120]!r}")

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        for word in self.stream_text.split(" "):
            if word:
                yield word + " "
        self._last_result = AgentResult(
            ok=True, value=self.stream_text, elapsed_ms=1, prompt_tokens=3, completion_tokens=2
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def test_cli_turn_advances_clock_via_condition_trigger_after_process_exits(
    tmp_db_path, monkeypatch
) -> None:
    """`run_turn` 반환 **이후** 새로 연 `EventStore`에서 `clock_advanced
    (trigger="condition")` 사건을 정확히 하나 찾고, 재생한 `clock_segment`가
    1이다 — 배경 작업을 `await`하지 않고 던졌을 때 프로세스 종료로 산출물이
    사라지는 회귀(Pitfall 1)를 잡는 시험이다."""
    db = str(tmp_db_path)
    provider = _MultiRoleProvider()
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code == 0

    events = _read_events(db, "s1")
    clock_advanced = [event for event in events if event.event_type == "clock_advanced"]
    assert len(clock_advanced) == 1
    assert clock_advanced[0].trigger == "condition"

    store = EventStore(db)
    store.initialize()
    try:
        state = rebuild_state(store, "s1")
    finally:
        store.close()
    assert state.clock_segment == 1


def test_event_schema_version_still_five() -> None:
    assert EVENT_SCHEMA_VERSION == 5


# ---------------------------------------------------------------------------
# 09-01 Task 3 — 판단이 늦거나 죽어도 턴은 끝까지 간다 (ARCH-05/D-05)
# ---------------------------------------------------------------------------


def test_clock_judge_always_raising_still_exits_zero_with_narration_recorded(
    tmp_db_path, monkeypatch
) -> None:
    """판단이 매번 예외를 던져도 `run_turn`의 반환 코드는 0이고 서사 사건은
    그대로 남는다 — 턴은 판단 실패와 무관하게 끝까지 간다(ARCH-05/D-05)."""
    db = str(tmp_db_path)
    provider = _MultiRoleProvider(clock_judge_always_raises=True)
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code == 0

    events = _read_events(db, "s1")
    narration_events = [event for event in events if event.event_type == "narration_appended"]
    # 기본 stream_text는 마침표 둘로 끝나는 두 문장이다 — 판단 실패와
    # 무관하게 그대로 두 조각이 기록된다.
    assert len(narration_events) == 2

    clock_advanced = [event for event in events if event.event_type == "clock_advanced"]
    assert clock_advanced == []


def test_clock_judge_failure_notice_only_on_stderr_never_stdout(
    tmp_db_path, monkeypatch, capsys
) -> None:
    """판단 실패 문구가 `capsys`로 잡은 표준출력에는 없고 표준오류에만
    있다 — 플레이어 화면과 운영자 로그의 구분이다(D-05)."""
    db = str(tmp_db_path)
    provider = _MultiRoleProvider(clock_judge_always_raises=True)
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code == 0

    captured = capsys.readouterr()
    failure_phrase = "clock judge 대역이 일부러 실패한다"
    assert failure_phrase not in captured.out
    assert failure_phrase in captured.err


def test_signal_skip_never_calls_deep_judgment_provider(tmp_db_path, monkeypatch) -> None:
    """신호가 `"skip"`이면 깊은 판단 제공자가 한 번도 안 불린다 —
    관문(judge_clock_signal)만 돌고 배경 작업이 아예 등록되지 않는다(DP-01)."""
    db = str(tmp_db_path)
    provider = _MultiRoleProvider(signal_value=_SIGNAL_SKIP_JSON)
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code == 0

    # ① action_classifier + ② situation_judge + ③ clock_judge 관문(신호=skip)
    # 세 번만 불렸다 — ④ 깊은 판단 호출은 없다.
    assert provider.complete_calls == 3

    events = _read_events(db, "s1")
    clock_advanced = [event for event in events if event.event_type == "clock_advanced"]
    assert clock_advanced == []
