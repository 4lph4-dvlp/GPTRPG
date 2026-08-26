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

from gptrpg.agents.context import NarrationFacts
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.master_gm import (
    STREAM_STALL_TIMEOUT_S,
    _drain_with_stall_timeout,
    chunk_sentences,
    narrate,
)
from gptrpg.agents.narration_guard import NOTICE_FILTERED, NOTICE_GAVE_UP
from gptrpg.agents.providers.nim_provider import NimProvider

_FAKE_KEY = "fake-key-does-not-touch-network"


def _texts(chunks) -> list[str]:
    """`narrate()`가 이제 `NarrationChunk`를 낸다(10-01) — 이 파일의 기존
    시험은 순서·조각 수만 보면 되므로 `.text`만 뽑아 비교한다. `disposition`
    까지 확인하는 시험은 `tests/test_safety_flag_pipeline.py`가 담당한다."""
    return [chunk.text for chunk in chunks]


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
        self.stream_call_count = 0

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s) -> Iterator[str]:
        self.stream_call_count += 1
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
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _TwoSentenceStreamProvider()
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
        )
    )
    assert len(sentences) >= 2
    assert _texts(sentences) == ["문이 요란하게 부서진다.", "안에서 서늘한 바람이 흘러나온다."]
    assert all(chunk.disposition == "clean" for chunk in sentences)
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
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _StallsForeverStreamProvider(stall_s=1.0)
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
            stall_timeout_s=0.05,
        )
    )
    assert sentences == []
    assert provider.last_result().ok is False
    assert provider.last_result().elapsed_ms >= 0


def test_narrate_keeps_already_emitted_sentence_when_stream_stalls_mid_way() -> None:
    """이미 나간 조각은 스톨 뒤에도 살아남고, 재시도 없이 거기서 끝난다.

    10-01부터 `narrate()`는 문장을 1개 지연 버퍼에 보류했다가 다음 문장(또는
    스트림 종료)이 와야 판정해 내보낸다 — 이 문장은 스톨이 나기 전까지
    다음 문장을 못 만나 보류 중이었다. 그래도 이 보장은 깨지지 않는다:
    스톨 예외가 지연 버퍼를 빠져나가기 직전에 보류 문장을 판정해 내보낸다
    (`agents/master_gm.narrate`의 안쪽 `except Exception: ... raise` 갈래).
    """
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _EmitsOneThenStallsForeverProvider(stall_s=1.0)
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
            stall_timeout_s=0.05,
        )
    )
    assert _texts(sentences) == ["이미 나간 문장이다."]
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
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _DelegateShapedStallsForeverProvider(stall_s=1.0)
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
            stall_timeout_s=0.05,
        )
    )
    assert sentences == []
    assert provider.last_result().ok is False


def test_narrate_keeps_already_emitted_sentence_through_delegate_shaped_provider() -> None:
    """위임 모양 이중체에서도 이미 나간 문장은 보존되고 실패 껍데기는 위임 대상에 도달한다."""
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _DelegateShapedEmitsOneThenStallsForeverProvider(stall_s=1.0)
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
            stall_timeout_s=0.05,
        )
    )
    assert _texts(sentences) == ["이미 나간 문장이다(위임 모양)."]
    assert provider.last_result().ok is False


# ---------------------------------------------------------------------------
# 정상 완주 경로에서는 note_result()가 호출되지 않는다 — 성공한 스트림의
# 토큰·시간을 실패 껍데기가 덮어쓰지 않는다.
# ---------------------------------------------------------------------------


def test_narrate_does_not_call_note_result_on_successful_completion() -> None:
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _TwoSentenceStreamProvider()
    note_result_calls: list[AgentResult] = []
    provider.note_result = note_result_calls.append  # type: ignore[method-assign]

    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
        )
    )

    assert _texts(sentences) == ["문이 요란하게 부서진다.", "안에서 서늘한 바람이 흘러나온다."]
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

    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    sentences = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
        )
    )

    assert _texts(sentences) == ["문이 삐걱거리며 열린다."]
    assert provider.last_result().ok is False


# ---------------------------------------------------------------------------
# 10-03: 걸린 문장을 만나면 그 자리에서 재생성을 한 번 시도한다(D-06/D-07,
# SAFE-04). 재시도(MAX_ATTEMPTS)와는 다른 자리에서 일어나므로, 정상 경로에서는
# provider.stream() 호출이 여전히 정확히 1회다.
# ---------------------------------------------------------------------------


def test_narrate_clean_stream_calls_provider_stream_exactly_once() -> None:
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _TwoSentenceStreamProvider()
    list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
        )
    )
    assert provider.stream_call_count == 1


class _BlocksOnceThenCleanProvider:
    """`narrate()`의 재생성 경로 시험용 — 첫 호출은 걸리는 문장(생각 블록)을
    내고, 두 번째 호출(재생성)은 깨끗한 문장을 낸다. `messages`(재생성
    프롬프트)는 안 들여다본다 — `stream_calls`에 `(system, messages)` 짝을
    그대로 쌓아 뒀다가 시험이 직접 대조한다."""

    name = "blocks-once-then-clean"

    def __init__(self) -> None:
        self.stream_calls: list[tuple[list[dict], list[dict]]] = []
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s) -> Iterator[str]:
        self.stream_calls.append((system, messages))
        if len(self.stream_calls) == 1:
            yield "문이 열린다. <think>이건 안돼.</think>"
        else:
            yield "안전한 다음 문장이다."
        self._last_result = AgentResult(
            ok=True, value="", elapsed_ms=5, prompt_tokens=3, completion_tokens=3
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def test_narrate_regenerates_once_after_a_blocked_sentence_and_calls_stream_twice() -> None:
    """차단 1회 시나리오 — provider.stream() 호출 횟수가 2다(정상 1 + 재생성 1)."""
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _BlocksOnceThenCleanProvider()
    chunks = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
        )
    )

    assert len(provider.stream_calls) == 2
    assert [chunk.disposition for chunk in chunks] == ["clean", "blocked", "clean"]
    assert chunks[0].text == "문이 열린다."
    assert chunks[1].text == "이야기 한 부분을 걸렀어요. 이어서 씁니다."
    assert chunks[2].text == "안전한 다음 문장이다."
    assert provider.last_result().ok is True


def test_narrate_regeneration_prompt_carries_avoid_text_and_written_so_far() -> None:
    """재생성 프롬프트의 messages에는 걸린 문장 원문과 지금까지 쓴 문장이
    실려 있다(D-06/D-07) — 이 원문이 가는 곳은 모델(messages)이지 화면이
    아니다."""
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _BlocksOnceThenCleanProvider()
    list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
        )
    )

    _first_system, first_messages = provider.stream_calls[0]
    _regen_system, regen_messages = provider.stream_calls[1]
    first_turn_text = first_messages[0]["content"]
    regen_turn_text = regen_messages[0]["content"]

    assert "이건 안돼" not in first_turn_text
    assert "이건 안돼" in regen_turn_text
    assert "문이 열린다." in regen_turn_text


def test_narrate_regeneration_reuses_identical_system_object() -> None:
    """첫 호출과 재생성 호출의 system 인자가 같은 객체다(캐시 유지, D-02②)."""
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _BlocksOnceThenCleanProvider()
    list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
        )
    )

    first_system, _ = provider.stream_calls[0]
    regen_system, _ = provider.stream_calls[1]
    assert first_system is regen_system


# ---------------------------------------------------------------------------
# 10-03 Task 2: 재생성 스트림에서도 걸리면 D-08 종료 — NOTICE_GAVE_UP을 마지막
# 으로 내보내고, 실패 껍데기가 성공한 스트림의 토큰 값을 살린다(T-10-10).
# ---------------------------------------------------------------------------


class _AlwaysBlocksSingleSentenceProvider:
    """매 호출마다 문장부호가 하나도 없는 완결된 생각 블록 하나만 낸다 —
    `messages`(재생성 지시)는 안 들여다본다. 문장 경계가 스트림 맨 끝에만
    있으므로 `chunk_sentences`가 그 문장을 내보내려면 델타 소스를 끝까지
    드레인해야 하고, 그 과정에서 `provider.stream()`의 뒷정리 코드
    (`self._last_result = ...`)가 먼저 실행된다 — 그래서 걸린 문장이
    판정되는 시점에는 이미 실제 토큰 값이 `_last_result`에 들어 있다."""

    name = "always-blocks-single-sentence"

    def __init__(self) -> None:
        self.stream_call_count = 0
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s) -> Iterator[str]:
        self.stream_call_count += 1
        yield "<think>계속 안 되는 생각</think>"
        self._last_result = AgentResult(
            ok=True,
            value="",
            elapsed_ms=7,
            prompt_tokens=100 + self.stream_call_count,
            completion_tokens=50 + self.stream_call_count,
            cached_prompt_tokens=10,
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def test_narrate_gives_up_with_notice_after_regeneration_also_blocks() -> None:
    """재생성 스트림도 걸리면 NOTICE_GAVE_UP이 마지막 조각으로 나오고,
    provider.stream() 호출이 정확히 2회(정상 1 + 재생성 1)로 끝난다 —
    재생성이 재시도되지 않는다(D-08). 재생성 자신의 "걸렀어요" 안내는
    억눌러지고(D-08 종료 안내 하나로 합쳐진다) 첫 차단의 안내만 남는다 —
    두 안내 조각이 연달아 나가지 않는다."""
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _AlwaysBlocksSingleSentenceProvider()
    chunks = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
        )
    )

    assert provider.stream_call_count == 2
    assert [chunk.disposition for chunk in chunks] == ["blocked", "blocked"]
    assert chunks[-1].text == NOTICE_GAVE_UP
    assert chunks[-1].reason == "think_block"


def test_narrate_give_up_failure_envelope_preserves_tokens_from_last_successful_stream() -> None:
    """두 번 다 걸린 턴도 실제로 쓴 토큰이 살아 있다(T-10-10) — 실패
    껍데기가 토큰을 0으로 지우지 않는다."""
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _AlwaysBlocksSingleSentenceProvider()
    list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
        )
    )

    result = provider.last_result()
    assert result.ok is False
    assert result.prompt_tokens > 0
    assert result.completion_tokens > 0
    # 재생성 호출(두 번째 stream())이 낸 토큰 값이다 — 첫 호출 값(101/51)이
    # 아니라 마지막으로 성공한 스트림의 값(102/52)을 살린다.
    assert result.prompt_tokens == 102
    assert result.completion_tokens == 52


# ---------------------------------------------------------------------------
# 10-07 Task 3 (WR-01): 한 턴의 제공자 stream() 호출 상한 3회를 **실제로
# 호출을 세는 시험**이 진다 — 이름만 그런 상수(`MAX_REGENERATIONS`, 이
# 계획에서 지웠다)가 아니다.
# ---------------------------------------------------------------------------


class _FailsOnceThenBlocksThenCleanProvider:
    """3회 상한 시나리오용 — 첫 호출(정상 경로 1차 시도)은 조각을 하나도
    못 내고 죽는다(재시도 유발), 둘째 호출(정상 경로 2차 시도, 재시도)은
    걸리는 문장을 낸다(재생성 유발), 셋째 호출(재생성)은 깨끗한 문장을
    낸다. `MAX_ATTEMPTS`(2, 재시도)와 재생성(1)이 같은 턴에서 겹치는
    **가장 나쁜 경우**를 재현한다 — 이 경로가 정확히 3회에서 멈추는지가
    이 파일의 핵심 회귀 방지 대상이다."""

    name = "fails-once-then-blocks-then-clean"

    def __init__(self) -> None:
        self.stream_call_count = 0
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s) -> Iterator[str]:
        self.stream_call_count += 1
        if self.stream_call_count == 1:
            raise RuntimeError("연결이 거절됐다 — 조각이 하나도 안 나간 채 죽는다")
        if self.stream_call_count == 2:
            yield "<think>걸리는 생각</think>"
        else:
            yield "재생성이 낸 깨끗한 문장이다."
        self._last_result = AgentResult(
            ok=True, value="", elapsed_ms=5, prompt_tokens=3, completion_tokens=3
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def test_narrate_never_exceeds_three_provider_stream_calls_in_a_single_turn() -> None:
    """**이 시험이 존재하는 이유:** 03-04 Task 3 라이브 검증에서 재시도와
    재생성이 같은 루프에 섞여 실제로 ~22분 동안 터미널이 먹통이 된 사고가
    났다(`STREAM_STALL_TIMEOUT_S` 도크스트링·RESEARCH.md Pitfall 2 참조) —
    재시도 횟수와 검사-재생성 횟수가 곱해지면서 호출이 무한히 늘어난 것이
    그 사고의 곱셈이었다. 이 시험은 그 사고가 나던 자리와 정확히 같은
    조건(정상 경로 재시도 `MAX_ATTEMPTS`=2회 + 재생성 1회가 한 턴에서
    겹치는 가장 나쁜 경우)을 재현해, 제공자 `stream()` 호출이 **정확히
    3회에서 멈추고 더 늘어나지 않는지**를 실제로 센다.

    호출 횟수 보증을 지키던 것은 예전에 `MAX_REGENERATIONS`라는 이름의
    상수였는데, 그 상수는 실제로는 아무 데서도 안 읽혔다(WR-01, 10-07) —
    이름만 지키고 있었다. 이제 그 보증은 이 시험이 진다: 나중에 누가
    재생성 블록을 반복문으로 바꾸면(리뷰의 (a)안, 이 계획이 명시적으로
    거부한 방향) 호출 횟수가 3을 넘고 이 시험이 빨간불로 막는다."""
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _FailsOnceThenBlocksThenCleanProvider()
    chunks = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
        )
    )

    assert provider.stream_call_count == 3
    assert provider.stream_call_count <= 3
    assert [chunk.disposition for chunk in chunks] == ["blocked", "clean"]
    assert provider.last_result().ok is True


@pytest.mark.parametrize(
    "provider_factory",
    [
        lambda: _TwoSentenceStreamProvider(),  # 깨끗한 서사 — 정확히 1회
        lambda: _BlocksOnceThenCleanProvider(),  # 한 번 걸리고 재생성 성공 — 정확히 2회
        lambda: _AlwaysBlocksSingleSentenceProvider(),  # 두 번 걸려 포기 — 정확히 2회
        lambda: _FailsOnceThenBlocksThenCleanProvider(),  # 재시도+재생성 겹침(최악) — 정확히 3회
    ],
)
def test_narrate_stream_call_count_stays_within_the_three_call_ceiling_across_all_paths(
    provider_factory,
) -> None:
    """네 경로(깨끗함/재생성 성공/재생성도 걸림/재시도+재생성 겹침) 전부를
    한자리에서 훑어 `stream_call_count`가 하나도 예외 없이 3 이하임을
    단언한다 — 어떤 경로에서도 상한을 넘지 않는다는 것이 각 경로별 개별
    시험이 아니라 이 표 하나로도 확인된다."""
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = provider_factory()
    list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
        )
    )
    # `_BlocksOnceThenCleanProvider`는 `stream_call_count` 대신 `stream_calls`
    # 목록(호출별 (system, messages) 짝)을 쌓는다 — 두 이중체 스타일 다 지원한다.
    call_count = getattr(provider, "stream_call_count", None)
    if call_count is None:
        call_count = len(provider.stream_calls)
    assert call_count <= 3


# ---------------------------------------------------------------------------
# verify-13-06 사람 확인 결함1 — 서사 스트림 자기 반복. 2026-08-26 well_below
# 실측(session verify-13-06, turn seq 112)에서 한 턴의 narration_appended
# 27조각 중 12조각이 앞선 조각과 바이트 단위로 같았다 — 스트림이 문장 하나를
# 다 쓴 뒤 마침표 없이 곧바로 처음부터 되풀이했다(13번째 조각의 텍스트가
# 직전 문장의 꼬리 + 첫 문장의 반복을 이음매 없이 이어 붙인 모양이었다).
# 이 이중체는 그 정확한 모양(마침표 없는 이음매)을 재현한다.
# ---------------------------------------------------------------------------


class _RepeatsEarlierSentenceMidStreamProvider:
    """`narrate()`의 자기 반복 검사(narration_repeat) 시험용 — 한 번의
    `stream()` 호출 안에서 문장 둘을 낸 뒤, 마침표 없는 꼬리에 곧바로 첫
    문장을 다시 이어 붙인다(2026-08-26 well_below 실측과 정확히 같은
    이음매 없는 모양 — `chunk_sentences`가 꼬리와 반복을 한 조각으로 합친다).
    재생성 호출(두 번째 `stream()`)은 실제로 새 문장을 낸다."""

    name = "repeats-earlier-sentence"

    _S0 = "쓰러진 돌기둥 사이로 차가운 밤바람이 스며들었다."
    _S1 = "저 멀리서 늑대의 울음소리가 희미하게 들려왔다."

    def __init__(self) -> None:
        self.stream_calls: list[tuple[list[dict], list[dict]]] = []
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s) -> Iterator[str]:
        self.stream_calls.append((system, messages))
        if len(self.stream_calls) == 1:
            # 마침표 없는 꼬리 바로 뒤에 S0를 다시 이어 붙인다 — 실측에서
            # 관찰된 이음매 없는 되풀이를 그대로 흉내낸다.
            yield f"{self._S0} {self._S1} 정체 모를 발소리가 서서히 가까워지고 있었다"
            yield f"{self._S0} {self._S1}"
        else:
            yield "재생성이 실제로 새로 쓴 문장이다."
        self._last_result = AgentResult(
            ok=True, value="", elapsed_ms=5, prompt_tokens=3, completion_tokens=3
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def test_narrate_stops_narration_stream_that_repeats_itself_without_sentence_boundary() -> None:
    """verify-13-06 사람 확인 결함1 재현 — 같은 스트림 안에서 이미 낸 문장을
    마침표 없이 곧바로 되풀이하면 `narrate()`가 그 자리에서 스트림 소비를
    멈추고 재생성 한 번으로 넘어간다. **이 고침 전에는 이 시험이 실패한다**
    — 되풀이된 문장이 `chunks`에 그대로 두 번(원본 + 이음매 없는 반복)
    나갔을 것이다."""
    facts = NarrationFacts(
        check_summary="hack_and_slash 판정 결과 hit (목표 10)",
        scene_summary="",
        facts=(),
        scene_entities=(),
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    provider = _RepeatsEarlierSentenceMidStreamProvider()
    chunks = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=facts,
            rulebook_display_name="던전월드 계열",
        )
    )

    assert len(provider.stream_calls) == 2  # 원래 스트림 + 재생성 1회, 더 안 는다
    assert [chunk.disposition for chunk in chunks] == ["clean", "clean", "blocked", "clean"]
    assert chunks[2].reason == "narration_repeat"
    assert chunks[2].text == NOTICE_FILTERED
    # 되풀이된 원문 자체는 화면에 두 번 나가지 않는다 — 셋째 조각은 걸린
    # 원문이 아니라 안내 문구고, S0는 정확히 한 번만 화면 텍스트에 남는다.
    combined_text = "".join(chunk.text for chunk in chunks if chunk.disposition != "blocked")
    assert combined_text.count(_RepeatsEarlierSentenceMidStreamProvider._S0) == 1
    assert provider.last_result().ok is True
