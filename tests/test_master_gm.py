"""서사 문장 조각내기가 경계값까지 단단한지 시험한다 (03-03 Task 3).

`chunk_sentences`는 제공자 없이 도는 순수 함수라 델타 목록을 직접 만들어
넘긴다. `narrate()`는 여기서 순서·조각 수만 확인하고, 재시도·타임아웃
동작은 `tests/test_agents_retry.py`가 이미 다룬다.

파일 뒤쪽 절(`_drain_with_stall_timeout`)은 03-04 Task 3 라이브 검증에서
나온 문제의 수정이다 — `provider.stream()`이 실제로 멈췄을 때 아무 예외도
없이 무한정 블로킹하는 사례가 있었다(터미널이 ~22분 동안 응답 없이
붙잡힘). 이 이중체들은 "느리지만 계속 진행 중"이 아니라 "완전히 멈췄다"를
시뮬레이션한다.
"""

import time
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from gptrpg.agents.context import ClockState, TurnContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.master_gm import (
    STREAM_STALL_TIMEOUT_S,
    _drain_with_stall_timeout,
    chunk_sentences,
    narrate,
)
from gptrpg.agents.providers.nim_provider import NimProvider

_FAKE_KEY = "fake-key-does-not-touch-network"


def test_three_sentences_yield_three_chunks() -> None:
    result = list(chunk_sentences(["문장 하나. 문장 둘! 문장 셋?"]))
    assert result == ["문장 하나.", "문장 둘!", "문장 셋?"]


def test_no_terminal_punctuation_yields_exactly_one_chunk_not_zero() -> None:
    result = list(chunk_sentences(["문장 부호가 전혀 없는 한 덩어리 응답"]))
    assert len(result) == 1
    assert result == ["문장 부호가 전혀 없는 한 덩어리 응답"]


def test_stream_cut_off_mid_sentence_yields_remaining_buffer_as_last_chunk() -> None:
    result = list(chunk_sentences(["문장이 중간에서 끊긴다 그대로"]))
    assert len(result) == 1
    assert result[-1] == "문장이 중간에서 끊긴다 그대로"


def test_delta_boundary_splitting_sentence_terminator_still_merges_to_one() -> None:
    """한 델타가 마침표 직전까지, 다음 델타가 마침표부터 — 문장이 하나로 합쳐진다."""
    result = list(chunk_sentences(["이것은 하나의 문장이다", "."]))
    assert len(result) == 1
    assert result == ["이것은 하나의 문장이다."]


def test_whitespace_only_deltas_yield_zero_chunks() -> None:
    result = list(chunk_sentences(["   ", "\n\n", "  "]))
    assert result == []


def test_korean_sentence_endings_chunk_like_english() -> None:
    result = list(
        chunk_sentences(
            ["오늘 하루도 무사히 지나갔다.", " 정말 다행이에요.", " 내일은 괜찮을까?"]
        )
    )
    assert result == ["오늘 하루도 무사히 지나갔다.", "정말 다행이에요.", "내일은 괜찮을까?"]


def test_multiple_spaces_and_newlines_between_sentences_are_trimmed_no_empty_chunk() -> None:
    result = list(chunk_sentences(["문장 하나.\n\n\n다음 문장 두울."]))
    assert result == ["문장 하나.", "다음 문장 두울."]
    assert "" not in result


def test_chunk_order_matches_input_order() -> None:
    result = list(chunk_sentences(["첫 번째. ", "두 번째. ", "세 번째."]))
    assert result == ["첫 번째.", "두 번째.", "세 번째."]


class _TwoSentenceStreamProvider:
    """`narrate()` 시험용 — 두 문장짜리 서사를 결정적으로 스트리밍한다."""

    name = "two-sentence-stream"

    def __init__(self) -> None:
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s) -> Iterator[str]:
        yield "문이 요란하게 부서진다. "
        yield "안에서 서늘한 바람이 흘러나온다."
        self._last_result = AgentResult(
            ok=True, value="", elapsed_ms=5, prompt_tokens=2, completion_tokens=2
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result


def test_narrate_yields_at_least_two_chunks_in_order() -> None:
    ctx = TurnContext(
        scene_entities=(),
        character_state=(),
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )
    provider = _TwoSentenceStreamProvider()
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            ctx=ctx,
            check_summary="hack_and_slash 판정 결과 hit (목표 10)",
            rulebook_display_name="던전월드 계열",
        )
    )
    assert len(sentences) >= 2
    assert sentences == ["문이 요란하게 부서진다.", "안에서 서늘한 바람이 흘러나온다."]
    assert provider.last_result().ok is True


def test_stream_stall_timeout_default_is_documented_value() -> None:
    assert STREAM_STALL_TIMEOUT_S == 90.0


def test_drain_with_stall_timeout_passes_through_fast_items() -> None:
    result = list(_drain_with_stall_timeout(iter(["가", "나", "다"]), stall_timeout_s=1.0))
    assert result == ["가", "나", "다"]


def test_drain_with_stall_timeout_raises_after_no_item_for_the_deadline() -> None:
    def _forever_stalled() -> Iterator[str]:
        time.sleep(1.0)
        yield "이건 절대 안 나온다"

    with pytest.raises(TimeoutError):
        list(_drain_with_stall_timeout(_forever_stalled(), stall_timeout_s=0.05))


class _StallsForeverStreamProvider:
    """narrate() 스톨 감지 시험용 — `stream()`이 아무 조각도 없이 오래 멈춘다."""

    name = "stalls-forever"

    def __init__(self, *, stall_s: float) -> None:
        self._stall_s = stall_s
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s) -> Iterator[str]:
        time.sleep(self._stall_s)
        yield "이건 절대 안 나온다"

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


class _EmitsOneThenStallsForeverProvider:
    """narrate() 스톨 감지 시험용 — 문장 하나를 낸 뒤 멈춘다(이미 나간 조각은 살아남아야 한다)."""

    name = "emits-then-stalls"

    def __init__(self, *, stall_s: float) -> None:
        self._stall_s = stall_s
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s) -> Iterator[str]:
        yield "이미 나간 문장이다. "
        time.sleep(self._stall_s)
        yield "이건 절대 안 나온다"

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


class _DelegateStub:
    """`_DelegateShapedStallsForeverProvider`가 상태를 실제로 두는 안쪽 객체."""

    def __init__(self) -> None:
        self._last_result: AgentResult | None = None

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete() 또는 stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


class _DelegateShapedStallsForeverProvider:
    """G-03-3 최소 재현용 — `NimProvider`/`OpenRouterProvider`와 같은 위임 구조.

    안쪽 `_DelegateStub`에 모든 상태를 두고 바깥은 자기 `_last_result`를
    **갖지 않는다**. 편의를 위해 안쪽 상태를 바깥에도 복제해 두면(예:
    `self._last_result = self._delegate._last_result`처럼 동기화) 이 이중체의
    존재 이유가 사라진다 — 직접 어댑터 모양 이중체만으로는 위임 구멍이
    잡히지 않는다는 것을 증명하는 것이 이 이중체의 유일한 목적이다.
    """

    name = "delegate-shaped-stalls-forever"

    def __init__(self, *, stall_s: float) -> None:
        self._stall_s = stall_s
        self._delegate = _DelegateStub()

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s) -> Iterator[str]:
        time.sleep(self._stall_s)
        yield "이건 절대 안 나온다"

    def last_result(self) -> AgentResult:
        return self._delegate.last_result()

    def note_result(self, result: AgentResult) -> None:
        self._delegate.note_result(result)


class _DelegateShapedEmitsOneThenStallsForeverProvider:
    """위 이중체의 「조각 하나를 낸 뒤 멈춘다」 변형 — 위임 모양은 그대로."""

    name = "delegate-shaped-emits-then-stalls"

    def __init__(self, *, stall_s: float) -> None:
        self._stall_s = stall_s
        self._delegate = _DelegateStub()

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s) -> Iterator[str]:
        yield "이미 나간 문장이다(위임 모양). "
        time.sleep(self._stall_s)
        yield "이건 절대 안 나온다"

    def last_result(self) -> AgentResult:
        return self._delegate.last_result()

    def note_result(self, result: AgentResult) -> None:
        self._delegate.note_result(result)


def test_narrate_gives_up_and_marks_failure_when_stream_never_produces_anything() -> None:
    """조각이 하나도 안 나온 채 멈추면 재시도(MAX_ATTEMPTS)까지 소진한 뒤 실패로
    떨어진다 — 터미널이 무한정 멈추지 않는다."""
    ctx = TurnContext(
        scene_entities=(),
        character_state=(),
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )
    provider = _StallsForeverStreamProvider(stall_s=1.0)
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            ctx=ctx,
            check_summary="hack_and_slash 판정 결과 hit (목표 10)",
            rulebook_display_name="던전월드 계열",
            stall_timeout_s=0.05,
        )
    )
    assert sentences == []
    assert provider.last_result().ok is False
    assert provider.last_result().elapsed_ms >= 0


def test_narrate_keeps_already_emitted_sentence_when_stream_stalls_mid_way() -> None:
    """이미 나간 조각은 스톨 뒤에도 살아남고, 재시도 없이 거기서 끝난다."""
    ctx = TurnContext(
        scene_entities=(),
        character_state=(),
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )
    provider = _EmitsOneThenStallsForeverProvider(stall_s=1.0)
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            ctx=ctx,
            check_summary="hack_and_slash 판정 결과 hit (목표 10)",
            rulebook_display_name="던전월드 계열",
            stall_timeout_s=0.05,
        )
    )
    assert sentences == ["이미 나간 문장이다."]
    assert provider.last_result().ok is False


# ---------------------------------------------------------------------------
# G-03-3 핵심 회귀: 위임 모양 이중체(NimProvider/OpenRouterProvider와 같은
# 구조)로 narrate()를 실패시켜도 last_result().ok가 False로 돌아온다
# (RuntimeError가 아니다) — 03-UAT.md 3번 시험 사고의 최소 재현.
# ---------------------------------------------------------------------------


def test_narrate_marks_failure_through_delegate_shaped_provider_when_stream_never_produces_anything() -> (
    None
):
    """03-06 이전이면 여기서 RuntimeError가 났다 — provider._last_result 직접 대입은
    위임 어댑터에서 아무도 읽지 않는 새 속성 하나만 만들고 값을 잃어버렸다."""
    ctx = TurnContext(
        scene_entities=(),
        character_state=(),
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )
    provider = _DelegateShapedStallsForeverProvider(stall_s=1.0)
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            ctx=ctx,
            check_summary="hack_and_slash 판정 결과 hit (목표 10)",
            rulebook_display_name="던전월드 계열",
            stall_timeout_s=0.05,
        )
    )
    assert sentences == []
    assert provider.last_result().ok is False


def test_narrate_keeps_already_emitted_sentence_through_delegate_shaped_provider() -> None:
    """위임 모양 이중체에서도 이미 나간 문장은 보존되고 실패 껍데기는 위임 대상에 도달한다."""
    ctx = TurnContext(
        scene_entities=(),
        character_state=(),
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )
    provider = _DelegateShapedEmitsOneThenStallsForeverProvider(stall_s=1.0)
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            ctx=ctx,
            check_summary="hack_and_slash 판정 결과 hit (목표 10)",
            rulebook_display_name="던전월드 계열",
            stall_timeout_s=0.05,
        )
    )
    assert sentences == ["이미 나간 문장이다(위임 모양)."]
    assert provider.last_result().ok is False


# ---------------------------------------------------------------------------
# 정상 완주 경로에서는 note_result()가 호출되지 않는다 — 성공한 스트림의
# 토큰·시간을 실패 껍데기가 덮어쓰지 않는다.
# ---------------------------------------------------------------------------


def test_narrate_does_not_call_note_result_on_successful_completion() -> None:
    ctx = TurnContext(
        scene_entities=(),
        character_state=(),
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )
    provider = _TwoSentenceStreamProvider()
    note_result_calls: list[AgentResult] = []
    provider.note_result = note_result_calls.append  # type: ignore[method-assign]

    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            ctx=ctx,
            check_summary="hack_and_slash 판정 결과 hit (목표 10)",
            rulebook_display_name="던전월드 계열",
        )
    )

    assert sentences == ["문이 요란하게 부서진다.", "안에서 서늘한 바람이 흘러나온다."]
    assert provider.last_result().ok is True
    assert note_result_calls == []


# ---------------------------------------------------------------------------
# IN-01 회귀: 진짜 위임 어댑터(`NimProvider`가 실제 `OpenAIProvider`를
# 감싼 그대로)를 `narrate()`로 직접 몬다 — 모양만 비슷한 이중체가 아니라
# 진짜 두 계층 프로덕션 스택이 G-03-3이 고친 대로 동작하는지 확인한다.
# SDK 클라이언트 생성자만 네트워크 없이 가짜로 바꿔치기한다
# (`tests/test_providers.py`의 `_no_network`와 같은 방식).
# ---------------------------------------------------------------------------


class _FakeStreamChunk:
    """`openai` SDK가 스트리밍 중 돌려주는 청크 하나를 흉내 낸다."""

    def __init__(self, *, delta_content: str | None, usage=None) -> None:
        self.choices = [SimpleNamespace(delta=SimpleNamespace(content=delta_content))]
        self.usage = usage


class _FakeOpenAIClientStreamRaisesAfterOneChunk:
    """`openai.OpenAI(...)`를 대신하는 가짜 — 조각 하나를 낸 뒤 스트림이 죽는다.

    `OpenAIProvider.__init__`이 넘기는 키워드 인자(`api_key`/`base_url`/
    `default_headers`/`max_retries`)를 전부 받아들이되 저장만 하고 실제
    네트워크는 전혀 타지 않는다.
    """

    def __init__(self, *, api_key, base_url=None, default_headers=None, **_kwargs):
        self.api_key = api_key
        self.base_url = base_url
        self.default_headers = default_headers
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, *, stream: bool, **_kwargs):
        assert stream is True, "narrate()는 항상 stream=True로 부른다"
        return self._stream_gen()

    def _stream_gen(self):
        yield _FakeStreamChunk(delta_content="문이 삐걱거리며 열린다. ")
        raise RuntimeError("네트워크가 스트림 중간에 갑자기 끊겼다")


def test_narrate_through_real_delegating_nim_provider_keeps_emitted_chunk_and_marks_failure(
    monkeypatch,
) -> None:
    """진짜 `NimProvider`(진짜 `OpenAIProvider`를 감싼 위임 그대로, 이중체가
    아니다)를 `narrate()`로 직접 몬다. SDK 클라이언트 생성자만 네트워크 없이
    가짜로 바꿔치기하고, 그 가짜가 조각 하나를 낸 뒤 스트림 중간에 죽는다.
    두 계층 위임 전체(`NimProvider.note_result()` -> `OpenAIProvider.note_result()`
    -> `OpenAIProvider._last_result`)가 실제로 이어져 있는지, 사적 속성을
    직접 건드리는 옛 버그(G-03-3)가 다시 생기지 않았는지 확인한다."""
    monkeypatch.setattr(
        "gptrpg.agents.providers.openai_provider.OpenAI",
        _FakeOpenAIClientStreamRaisesAfterOneChunk,
    )

    provider = NimProvider(_FAKE_KEY)

    ctx = TurnContext(
        scene_entities=(),
        character_state=(),
        clock_state=ClockState(clock_id="threat", segment_index=0, segment_count=6),
        recent_turns=(),
    )
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            ctx=ctx,
            check_summary="hack_and_slash 판정 결과 hit (목표 10)",
            rulebook_display_name="던전월드 계열",
        )
    )

    assert sentences == ["문이 삐걱거리며 열린다."]
    assert provider.last_result().ok is False
