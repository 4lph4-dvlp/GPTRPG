"""서사 스트림이 어떤 이유로든 실패해도 턴 전체가 raw traceback으로 죽지 않는지
확인한다 (G-03-3, 03-UAT.md 3번 시험).

`tests/test_turn_tracer.py`의 `_read_events`·`_install_fake_provider`·`_run_turn`과
같은 모양을 쓰되(하위 프로세스를 띄우지 않고 `main([...])`을 그 자리에서 부른다),
이 파일의 이중체들은 실패 모양이 파일마다 다르므로 공유 픽스처(`conftest.py`)로
올리지 않고 이 파일 안에 둔다 — 공유 픽스처로 올리면 정상 경로 시험들이 함께
흔들린다.
"""

import json

from gptrpg.agents import providers as providers_module
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.master_gm import NarrationChunk
from gptrpg.cli import turn_flow as turn_flow_module
from gptrpg.cli.main import main
from gptrpg.event_log.store import EventStore
from gptrpg.session_actor.actor import AppendNarration, CommandRejected, RecordAiCall, SessionActor

_CANDIDATE_JSON = json.dumps([{"move": "hack_and_slash", "stat": "STR"}])
"""분류기가 던전월드 계열의 실제 무브 하나를 확실히 후보로 내도록 고정한 JSON."""


def _read_events(db: str, session: str):
    store = EventStore(db)
    store.initialize()
    try:
        return store.read_events(session)
    finally:
        store.close()


def _install_fake_provider(monkeypatch, fake_provider, *, name="fake", env_var="FAKE_API_KEY"):
    """가짜 제공자를 `agents.providers` 등록소에 임시로 끼워 넣는다."""
    monkeypatch.setitem(providers_module.PROVIDER_ENV_VARS, name, env_var)
    monkeypatch.setitem(providers_module.PROVIDER_FACTORIES, name, lambda api_key: fake_provider)
    monkeypatch.setenv(env_var, "test-key")


def _run_turn(db: str, session: str, text: str, *, monkeypatch) -> int:
    # 확인 화면은 항상 승인한다("" -> Enter) — 이 파일의 시험은 서사 실패
    # 낙하 경로가 목적이라 확인 화면 자체는 다루지 않는다.
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


# ---------------------------------------------------------------------------
# 시험 1: 조각 하나를 낸 뒤 stream()이 예외를 던진다
# ---------------------------------------------------------------------------


class _EmitsOneThenRaisesProvider:
    """조각 하나를 낸 뒤 `stream()`이 예외를 던진다 — 규약은 지킨다(narrate()가
    내부에서 note_result()로 실패 껍데기를 남긴다)."""

    name = "emits-one-then-raises"

    def __init__(self) -> None:
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        result = AgentResult(ok=True, value=_CANDIDATE_JSON, elapsed_ms=1, prompt_tokens=5, completion_tokens=3)
        self._last_result = result
        return result

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        yield "문이 삐걱거리며 열린다. "
        raise RuntimeError("네트워크가 갑자기 끊겼다")

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def test_one_chunk_then_stream_raises_exits_nonzero_and_keeps_emitted_chunk(
    tmp_db_path, monkeypatch
):
    db = str(tmp_db_path)
    provider = _EmitsOneThenRaisesProvider()
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code != 0

    events = _read_events(db, "s1")
    types = [event.event_type for event in events]
    assert "check_resolved" in types

    narration_events = [event for event in events if event.event_type == "narration_appended"]
    assert len(narration_events) == 1
    assert narration_events[0].chunk_index == 0

    ai_events = [event for event in events if event.event_type == "ai_invoked"]
    gm_ai_event = ai_events[-1]
    assert gm_ai_event.prompt_tokens == 0
    assert gm_ai_event.completion_tokens == 0


# ---------------------------------------------------------------------------
# 시험 2 (UAT 사고 최소 재현): note_result()로 받은 값을 버리고 last_result()가
# 항상 RuntimeError를 던지는 이중체 — 제공자가 Provider 프로토콜을 어겨도
# CLI는 죽지 않는다.
# ---------------------------------------------------------------------------


class _DiscardsNoteResultProvider:
    """스트림이 시작도 못 하고 매번 죽고, `note_result()`로 받은 값을 버린다."""

    name = "discards-note-result"

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        return AgentResult(ok=True, value=_CANDIDATE_JSON, elapsed_ms=1, prompt_tokens=5, completion_tokens=3)

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise RuntimeError("스트림이 시작도 못 하고 죽었다")
        yield  # pragma: no cover - 제너레이터 함수 모양을 유지하기 위한 도달 불가 코드

    def last_result(self) -> AgentResult:
        raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")

    def note_result(self, result: AgentResult) -> None:
        pass  # 규약 위반 — 받은 값을 조용히 버린다


def test_provider_violating_note_result_contract_exits_nonzero_with_stderr_line(
    tmp_db_path, monkeypatch, capsys
):
    db = str(tmp_db_path)
    provider = _DiscardsNoteResultProvider()
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code != 0

    events = _read_events(db, "s1")
    ai_events = [event for event in events if event.event_type == "ai_invoked"]
    gm_ai_event = ai_events[-1]
    assert gm_ai_event.prompt_tokens == 0
    assert gm_ai_event.completion_tokens == 0

    stderr = capsys.readouterr().err
    assert "오류:" in stderr


# ---------------------------------------------------------------------------
# 시험 3: 첫 조각이 나오기 전에 stream()이 매번 실패한다 (규약은 지킨다)
# ---------------------------------------------------------------------------


class _AlwaysFailsBeforeFirstChunkProvider:
    """첫 조각이 나오기 전에 `stream()`이 매번 실패한다 — 규약은 지킨다."""

    name = "always-fails-before-first-chunk"

    def __init__(self) -> None:
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        result = AgentResult(ok=True, value=_CANDIDATE_JSON, elapsed_ms=1, prompt_tokens=5, completion_tokens=3)
        self._last_result = result
        return result

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise ConnectionError("연결이 매번 거부됐다")
        yield  # pragma: no cover - 제너레이터 함수 모양을 유지하기 위한 도달 불가 코드

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def test_stream_always_fails_before_first_chunk_exits_nonzero_with_zero_narration_events(
    tmp_db_path, monkeypatch
):
    db = str(tmp_db_path)
    provider = _AlwaysFailsBeforeFirstChunkProvider()
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code != 0

    events = _read_events(db, "s1")
    types = [event.event_type for event in events]
    assert "check_resolved" in types
    assert not any(event.event_type == "narration_appended" for event in events)

    ai_events = [event for event in events if event.event_type == "ai_invoked"]
    # 09-03: 분류기 + 상황판단 + 장면 신규 대상 + 시계 신호 관문 + 진행자(실패해도 기록된다) 다섯 건.
    assert len(ai_events) == 5


# ---------------------------------------------------------------------------
# 시험 4: turn_flow가 쓰는 narrate 이름을 문장 하나를 낸 뒤 예외를 던지는
# 생성기로 바꿔치기한다 (G-03-3이 지정한 이중체 모양 그대로)
# ---------------------------------------------------------------------------


def _stub_narrate_emits_one_then_raises(
    *, provider, model, facts, rulebook_display_name, resource_axes=()
):
    """`narrate()` 이름 자체를 바꿔치기하는 이중체(10-01부터 `NarrationChunk`를
    낸다) — `turn_flow._submit_narration_chunk`가 기대하는 반환 모양을
    맞춘다."""
    yield NarrationChunk(text="이미 나간 문장 하나.")
    raise RuntimeError("서사 생성기 자체가 죽었다")


def test_narrate_name_replaced_with_failing_generator_exits_nonzero_and_keeps_emitted_chunk(
    tmp_db_path, monkeypatch
):
    db = str(tmp_db_path)

    class _ClassifierOnlyProvider:
        """이 시험에서는 `narrate`가 통째로 바꿔치기되므로 stream()은 절대 안 불린다."""

        name = "classifier-only"

        def list_models(self) -> list[str]:
            return ["fake-model"]

        def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
            return AgentResult(ok=True, value=_CANDIDATE_JSON, elapsed_ms=1, prompt_tokens=5, completion_tokens=3)

        def stream(self, *, model, system, messages, max_tokens, timeout_s):
            raise NotImplementedError("이 시험은 narrate() 이름 자체를 바꿔치기한다 — stream()은 안 불린다")
            yield  # pragma: no cover

        def last_result(self) -> AgentResult:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")

        def note_result(self, result: AgentResult) -> None:
            pass

    _install_fake_provider(monkeypatch, _ClassifierOnlyProvider())
    monkeypatch.setattr(turn_flow_module, "narrate", _stub_narrate_emits_one_then_raises)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code != 0

    events = _read_events(db, "s1")
    narration_events = [event for event in events if event.event_type == "narration_appended"]
    assert len(narration_events) == 1
    assert narration_events[0].text == "이미 나간 문장 하나."

    ai_events = [event for event in events if event.event_type == "ai_invoked"]
    # 09-03: 분류기 + 상황판단 + 장면 신규 대상 + 시계 신호 관문 + 진행자 다섯 건.
    assert len(ai_events) == 5


# ---------------------------------------------------------------------------
# 시험 5 (WR-01 회귀): 서사 자체는 정상인데 AppendNarration 제출이 액터/저장소
# 결함으로 실패한다 — 「서사가 끝까지 나오지 못했다」로 뭉개지지 않고 실제
# 결함이 그대로 드러나야 한다.
# ---------------------------------------------------------------------------


class _NormalTwoSentenceNarrationProvider:
    """스트림은 완전히 정상이다 — 이 시험의 실패는 액터 쪽에서만 난다."""

    name = "normal-two-sentence-narration"

    def __init__(self) -> None:
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        result = AgentResult(ok=True, value=_CANDIDATE_JSON, elapsed_ms=1, prompt_tokens=5, completion_tokens=3)
        self._last_result = result
        return result

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        yield "문이 삐걱거리며 열린다. "
        yield "안에서 서늘한 바람이 흘러나온다."
        self._last_result = AgentResult(ok=True, value="...", elapsed_ms=1, prompt_tokens=7, completion_tokens=4)

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def test_actor_submit_failure_during_append_narration_propagates_undisguised(
    tmp_db_path, monkeypatch, capsys
):
    """`actor.submit(AppendNarration(...))`가 실패하면 그 실패의 실제 메시지가
    그대로 드러나야 한다 — 서사 실패로 오분류한 "서사가 끝까지 나오지 못했다"
    문구로 뭉개지면 안 된다(WR-01)."""
    db = str(tmp_db_path)
    provider = _NormalTwoSentenceNarrationProvider()
    _install_fake_provider(monkeypatch, provider)

    original_submit = SessionActor.submit

    async def _submit_that_rejects_append_narration(self, command):
        if isinstance(command, AppendNarration):
            raise CommandRejected("가짜 이벤트 스키마 결함 — 서사와는 무관하다")
        return await original_submit(self, command)

    monkeypatch.setattr(SessionActor, "submit", _submit_that_rejects_append_narration)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code != 0

    stderr = capsys.readouterr().err
    assert "가짜 이벤트 스키마 결함" in stderr
    assert "서사가 끝까지 나오지 못했다" not in stderr


# ---------------------------------------------------------------------------
# 시험 6 (WR-02 회귀): 서사는 정상적으로 끝났는데 마지막의 「항상 제출한다」
# RecordAiCall 제출 자체가 실패한다 — raw traceback으로 새지 않고 그 자리에서
# 사람이 읽을 오류로 죽어야 한다.
# ---------------------------------------------------------------------------


def test_record_ai_call_submission_failure_after_successful_narration_degrades_gracefully(
    tmp_db_path, monkeypatch, capsys
):
    """서사 스트림이 끝까지 정상 완주해도, 닫는 `RecordAiCall` 제출 자체가
    실패하면 raw traceback이 아니라 exit 1 + 사람이 읽을 stderr 한 줄로
    끝나야 한다(WR-02, G-03-3의 원래 목표)."""
    db = str(tmp_db_path)
    provider = _NormalTwoSentenceNarrationProvider()
    _install_fake_provider(monkeypatch, provider)

    original_submit = SessionActor.submit

    async def _submit_that_rejects_master_gm_record_ai_call(self, command):
        if isinstance(command, RecordAiCall) and command.agent_role == "master_gm":
            # `CommandRejected`가 아니라 일부러 `_cmd_turn`의 알려진 예외
            # 목록에 없는 타입을 쓴다 — WR-02 이전에는 이런 결함이 raw
            # traceback으로 그대로 새 나갔다.
            raise RuntimeError("가짜 기록 계층 결함 — RecordAiCall 제출 자체가 죽는다")
        return await original_submit(self, command)

    monkeypatch.setattr(SessionActor, "submit", _submit_that_rejects_master_gm_record_ai_call)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code != 0

    stderr = capsys.readouterr().err
    assert "오류:" in stderr
    assert "가짜 기록 계층 결함" in stderr

    events = _read_events(db, "s1")
    narration_events = [event for event in events if event.event_type == "narration_appended"]
    assert len(narration_events) == 2  # 서사 자체는 끝까지 정상적으로 나갔다


# ---------------------------------------------------------------------------
# 시험 7 (09-02, ARCH-05): situation_judge가 두 시도 모두 실패해도 서사는
# 그대로 나오고 턴이 끝까지 간다 — 빈 사실 묶음으로 서술이 이어진다(D-05).
# ---------------------------------------------------------------------------


class _SituationJudgeAlwaysFailsProvider:
    """`--provider fake --model fake-model`이 모든 역할에 같은 이름을 쓰게
    만들므로, `system` 프롬프트의 역할 지시문 텍스트(`prompt_assembly.py`가
    박아 넣는 고정 문구)로 상황판단 호출만 골라 실패시키는 대역이 필요하다.
    분류기·시계 신호 관문·진행자는 정상 동작한다."""

    name = "situation-judge-always-fails"

    def __init__(self) -> None:
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        combined = " ".join(block.get("text", "") for block in system)
        if "상황판단 담당" in combined:
            raise RuntimeError("situation_judge 대역이 일부러 실패한다")
        if "위협 시계 관문 판단자" in combined:
            return AgentResult(
                ok=True,
                value=json.dumps([{"signal": "skip", "why": "이번 턴은 무관하다"}]),
                elapsed_ms=1,
                prompt_tokens=1,
                completion_tokens=1,
            )
        # 행동 분류기
        return AgentResult(ok=True, value=_CANDIDATE_JSON, elapsed_ms=1, prompt_tokens=5, completion_tokens=3)

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        yield "문이 삐걱거리며 열린다. "
        yield "안에서 서늘한 바람이 흘러나온다."
        self._last_result = AgentResult(ok=True, value="...", elapsed_ms=1, prompt_tokens=7, completion_tokens=4)

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def test_situation_judge_both_attempts_fail_narration_still_completes_and_turn_exits_zero(
    tmp_db_path, monkeypatch
):
    """상황판단이 두 시도 모두 실패해도 서사는 빈 사실 묶음으로 그대로 나오고
    턴이 끝까지 간다(ARCH-05, D-05) — `_turn_flow`의 종료 코드는 0이다."""
    db = str(tmp_db_path)
    provider = _SituationJudgeAlwaysFailsProvider()
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code == 0

    events = _read_events(db, "s1")
    narration_events = [event for event in events if event.event_type == "narration_appended"]
    assert len(narration_events) == 2

    situation_ai_events = [
        event
        for event in events
        if event.event_type == "ai_invoked" and event.agent_role == "situation_judge"
    ]
    assert len(situation_ai_events) == 1
    assert situation_ai_events[0].prompt_tokens == 0
    assert situation_ai_events[0].completion_tokens == 0


# ---------------------------------------------------------------------------
# 시험 8 (09-03, ARCH-04/ARCH-05): scene_entity_judge가 두 시도 모두
# 실패해도 서사는 그대로 나오고 턴이 끝까지 간다 — 나머지 두 판단 결과는
# 그대로 쓰인다. 정상 실행에서는 세 판단 각자 정확히 하나씩 ai_invoked를
# 남긴다.
# ---------------------------------------------------------------------------


class _SceneEntityJudgeAlwaysFailsProvider:
    """`--provider fake --model fake-model`이 모든 역할에 같은 이름을 쓰게
    만들므로, `system` 프롬프트의 역할 지시문 텍스트로 장면 신규 대상 판단
    호출만 골라 실패시키는 대역이 필요하다. 분류기·상황판단·시계 신호
    관문·진행자는 정상 동작한다."""

    name = "scene-entity-judge-always-fails"

    def __init__(self) -> None:
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        combined = " ".join(block.get("text", "") for block in system)
        if "장면 신규 대상 판단자" in combined:
            raise RuntimeError("scene_entity_judge 대역이 일부러 실패한다")
        if "상황판단 담당" in combined:
            return AgentResult(
                ok=True,
                value=json.dumps([{"scene_summary": "장면.", "facts": []}]),
                elapsed_ms=1,
                prompt_tokens=1,
                completion_tokens=1,
            )
        if "위협 시계 관문 판단자" in combined:
            return AgentResult(
                ok=True,
                value=json.dumps([{"signal": "skip", "why": "이번 턴은 무관하다"}]),
                elapsed_ms=1,
                prompt_tokens=1,
                completion_tokens=1,
            )
        # 행동 분류기
        return AgentResult(ok=True, value=_CANDIDATE_JSON, elapsed_ms=1, prompt_tokens=5, completion_tokens=3)

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        yield "문이 삐걱거리며 열린다. "
        yield "안에서 서늘한 바람이 흘러나온다."
        self._last_result = AgentResult(ok=True, value="...", elapsed_ms=1, prompt_tokens=7, completion_tokens=4)

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def test_scene_entity_judge_both_attempts_fail_narration_still_completes_and_turn_exits_zero(
    tmp_db_path, monkeypatch
):
    """장면 신규 대상 판단이 두 시도 모두 실패해도 서사는 그대로 나오고
    턴이 끝까지 간다(ARCH-05, D-05) — `_turn_flow`의 종료 코드는 0이다."""
    db = str(tmp_db_path)
    provider = _SceneEntityJudgeAlwaysFailsProvider()
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code == 0

    events = _read_events(db, "s1")
    narration_events = [event for event in events if event.event_type == "narration_appended"]
    assert len(narration_events) == 2

    entity_ai_events = [
        event
        for event in events
        if event.event_type == "ai_invoked" and event.agent_role == "scene_entity_judge"
    ]
    assert len(entity_ai_events) == 1
    assert entity_ai_events[0].prompt_tokens == 0
    assert entity_ai_events[0].completion_tokens == 0


# ---------------------------------------------------------------------------
# 시험 9 (10-03, D-08): 두 번 다 걸리는 서사 — 웹(tests/test_web_actions.py
# ::test_narration_blocked_twice_gives_up_with_notice_and_keeps_roll_result)과
# 같은 시나리오를 명령줄 경로에서 돈다. 웹만 고치고 명령줄을 놓치는 회귀가
# 이 프로젝트에서 반복해서 났으므로(Pitfall 1), 두 경로 시험을 반드시
# 짝으로 둔다.
# ---------------------------------------------------------------------------


class _AlwaysBlocksSingleSentenceProvider:
    """매 호출마다 문장부호가 하나도 없는 완결된 생각 블록 하나만 낸다 —
    `messages`(재생성 지시)는 안 들여다본다. 첫 스트림도 재생성 스트림도
    둘 다 걸려서 D-08 종료 경로(`NOTICE_GAVE_UP`)를 탄다.
    `tests/test_web_actions.py`의 같은 이름 대역과 같은 모양이다."""

    name = "always-blocks-single-sentence"

    def __init__(self) -> None:
        self.stream_call_count = 0
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        result = AgentResult(ok=True, value=_CANDIDATE_JSON, elapsed_ms=1, prompt_tokens=5, completion_tokens=3)
        self._last_result = result
        return result

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        self.stream_call_count += 1
        yield "<think>계속 안 되는 생각</think>"
        self._last_result = AgentResult(
            ok=True,
            value="",
            elapsed_ms=7,
            prompt_tokens=100 + self.stream_call_count,
            completion_tokens=50 + self.stream_call_count,
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def test_narration_blocked_twice_exits_zero_with_gave_up_notice_and_keeps_roll_result(
    tmp_db_path, monkeypatch, capsys
):
    """두 번 다 걸린 턴도 명령줄 경로에서 기존 서사 실패 종료 코드를 그대로
    쓴다(새 종료 코드를 만들지 않았다) — 표준출력에 안내 문구가 있고, 표준
    오류에 운영자 한 줄이 사유와 함께 찍히며, 판정 결과 사건은 그대로
    남는다."""
    db = str(tmp_db_path)
    provider = _AlwaysBlocksSingleSentenceProvider()
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    # 명령줄의 기존 서사 실패 종료 코드를 그대로 재사용한다 — 새 종료
    # 코드를 만들지 않았다(시험 1의 순수 스트림 실패와 같은 exit_code 값).
    assert exit_code != 0

    captured = capsys.readouterr()
    assert "이야기를 끝까지 쓰지 못했어요." in captured.out
    assert "<think>" not in captured.out

    stderr = captured.err
    assert "오류:" in stderr

    events = _read_events(db, "s1")
    types = [event.event_type for event in events]
    # 판정 결과 사건은 그대로 남는다(TRUST-06, D-08).
    assert "check_resolved" in types

    narration_events = [event for event in events if event.event_type == "narration_appended"]
    assert narration_events[-1].text == "이야기를 끝까지 쓰지 못했어요."

    flag_events = [event for event in events if event.event_type == "safety_flagged"]
    assert len(flag_events) == 2
    for flag in flag_events:
        assert flag.source == "narration"
        assert flag.reason == "think_block"
        assert flag.disposition == "blocked"

    ai_events = [event for event in events if event.event_type == "ai_invoked"]
    gm_ai_events = [event for event in ai_events if event.agent_role == "master_gm"]
    assert len(gm_ai_events) == 1
    # 재생성까지 간 턴도 토큰이 0으로 지워지지 않는다(T-10-10).
    assert gm_ai_events[0].prompt_tokens > 0
    assert gm_ai_events[0].completion_tokens > 0

    assert provider.stream_call_count == 2


def test_turn_records_exactly_one_ai_invoked_per_parallel_judgment_role(
    tmp_db_path, monkeypatch
):
    """정상 실행에서 `situation_judge`·`scene_entity_judge`·`clock_judge`
    각각 정확히 하나의 `ai_invoked` 사건을 남긴다(ARCH-04)."""
    db = str(tmp_db_path)

    class _AllRolesSucceedProvider:
        name = "all-roles-succeed"

        def __init__(self) -> None:
            self._last_result: AgentResult | None = None

        def list_models(self) -> list[str]:
            return ["fake-model"]

        def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
            combined = " ".join(block.get("text", "") for block in system)
            if "상황판단 담당" in combined:
                value = json.dumps([{"scene_summary": "장면.", "facts": []}])
            elif "장면 신규 대상 판단자" in combined:
                value = "[]"
            elif "위협 시계 관문 판단자" in combined:
                value = json.dumps([{"signal": "skip", "why": "이번 턴은 무관하다"}])
            else:
                value = _CANDIDATE_JSON
            return AgentResult(ok=True, value=value, elapsed_ms=1, prompt_tokens=1, completion_tokens=1)

        def stream(self, *, model, system, messages, max_tokens, timeout_s):
            yield "문이 삐걱거리며 열린다. "
            yield "안에서 서늘한 바람이 흘러나온다."
            self._last_result = AgentResult(
                ok=True, value="...", elapsed_ms=1, prompt_tokens=7, completion_tokens=4
            )

        def last_result(self) -> AgentResult:
            if self._last_result is None:
                raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
            return self._last_result

        def note_result(self, result: AgentResult) -> None:
            self._last_result = result

    _install_fake_provider(monkeypatch, _AllRolesSucceedProvider())

    exit_code = _run_turn(db, "s1", "문을 부수고 들어간다", monkeypatch=monkeypatch)
    assert exit_code == 0

    events = _read_events(db, "s1")
    ai_events = [event for event in events if event.event_type == "ai_invoked"]
    for role in ("situation_judge", "scene_entity_judge", "clock_judge"):
        matching = [event for event in ai_events if event.agent_role == role]
        assert len(matching) == 1, f"{role}: {len(matching)}개"
