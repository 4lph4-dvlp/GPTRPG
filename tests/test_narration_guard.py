"""`narration_guard`의 원문 겹침 대조(10-02, D-02②) 단위 시험.

`tests/test_narration_isolation.py`가 확립한 관례를 따른다 — 소스 문자열을
이 파일에 다시 적지 않고 `build_gm_prompt`를 실제로 불러 그 결과의 영구
고정 블록 텍스트를 대조 소스로 쓴다. 지시문이 바뀌면 이 시험도 자동으로
새 값을 본다.
"""

from collections.abc import Iterator

from gptrpg.agents import narration_guard, prompt_assembly
from gptrpg.agents.context import NarrationFacts
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.master_gm import narrate
from gptrpg.rulebooks.threat_clocks import THREAT_CAST
from gptrpg.rules_core.entities import Entity, StatEntry

_CHECK_SUMMARY = "hack_and_slash 판정 결과 miss (목표 10)"


def _narration_facts(**overrides) -> NarrationFacts:
    base = dict(
        check_summary=_CHECK_SUMMARY,
        scene_summary="문이 부서지고 서늘한 바람이 흘러든다.",
        facts=("경비병이 쓰러졌다",),
        scene_entities=THREAT_CAST,
        party_state=(),
        actor_character_id=None,
        recent_turns=(),
        new_entities=(),
    )
    base.update(overrides)
    return NarrationFacts(**base)


def _permanent_block_text() -> str:
    """실제 `build_gm_prompt`가 만드는 영구 고정 블록 텍스트."""
    system, _messages = prompt_assembly.build_gm_prompt(
        rulebook_display_name="던전월드 계열", facts=_narration_facts()
    )
    return system[0]["text"]


# ---------------------------------------------------------------------------
# normalize_for_overlap — 정규화 네 단계
# ---------------------------------------------------------------------------


def test_normalize_for_overlap_strips_whitespace_punctuation_and_symbols():
    assert narration_guard.normalize_for_overlap("안녕, 세상!") == "안녕세상"
    assert narration_guard.normalize_for_overlap("안녕 세상") == "안녕세상"


def test_normalize_for_overlap_makes_punctuation_only_variants_equal():
    """구두점만 바꿔 쓴 두 문자열은 정규화 결과가 같다 — 조금만 바꿔 쓴
    유출을 놓치지 않기 위해서다."""
    plain = narration_guard.normalize_for_overlap("이 문장은 진행자 지시문이다")
    with_comma = narration_guard.normalize_for_overlap("이 문장은, 진행자 지시문이다.")
    quoted = narration_guard.normalize_for_overlap('"이 문장은 진행자 지시문이다"')
    assert plain == with_comma == quoted


def test_normalize_for_overlap_casefolds():
    assert narration_guard.normalize_for_overlap("Hello World") == narration_guard.normalize_for_overlap(
        "hello world"
    )


def test_normalize_for_overlap_empty_and_whitespace_only_yield_empty_string():
    assert narration_guard.normalize_for_overlap("") == ""
    assert narration_guard.normalize_for_overlap("   \n\t  ") == ""


# ---------------------------------------------------------------------------
# find_source_overlap — 문턱값과 경계
# ---------------------------------------------------------------------------


def test_find_source_overlap_empty_sentence_is_always_clean():
    permanent = _permanent_block_text()
    matched_len, hit = narration_guard.find_source_overlap("", None, (permanent,))
    assert hit is False
    assert matched_len == 0


def test_find_source_overlap_whitespace_only_sentence_is_always_clean():
    permanent = _permanent_block_text()
    matched_len, hit = narration_guard.find_source_overlap("   \n  ", None, (permanent,))
    assert hit is False
    assert matched_len == 0


def test_find_source_overlap_no_source_texts_skips_check():
    matched_len, hit = narration_guard.find_source_overlap(
        "아무 문장이나 상관없다 이 시험은 소스가 없다는 것만 확인한다", None, ()
    )
    assert hit is False
    assert matched_len == 0


def test_find_source_overlap_exactly_twelve_chars_is_blocked():
    """정규화 후 정확히 12자가 소스와 겹치면 blocked다(경계값 포함)."""
    permanent = _permanent_block_text()
    normalized_source = narration_guard.normalize_for_overlap(permanent)
    assert len(normalized_source) >= 20, "테스트 전제: 영구 블록은 충분히 길다"

    twelve_char_slice = normalized_source[5:17]
    assert len(twelve_char_slice) == narration_guard.MIN_OVERLAP_CHARS

    matched_len, hit = narration_guard.find_source_overlap(twelve_char_slice, None, (permanent,))
    assert hit is True
    assert matched_len == 12


def test_find_source_overlap_eleven_chars_is_clean():
    """11자는 문턱(12) 미만이므로 소스에 그대로 들어 있어도 clean이다."""
    permanent = _permanent_block_text()
    normalized_source = narration_guard.normalize_for_overlap(permanent)

    eleven_char_slice = normalized_source[5:16]
    assert len(eleven_char_slice) == 11

    matched_len, hit = narration_guard.find_source_overlap(eleven_char_slice, None, (permanent,))
    assert hit is False
    assert matched_len == 0


def test_find_source_overlap_short_sentence_never_blocks_even_if_verbatim_in_source():
    """정규화 결과 길이가 12 미만이면, 소스에 통째로 들어 있어도 항상
    clean이다."""
    permanent = _permanent_block_text()
    normalized_source = narration_guard.normalize_for_overlap(permanent)
    short_slice = normalized_source[:8]
    assert len(short_slice) < narration_guard.MIN_OVERLAP_CHARS

    matched_len, hit = narration_guard.find_source_overlap(short_slice, None, (permanent,))
    assert hit is False
    assert matched_len == 0


def test_find_source_overlap_across_sentence_boundary_is_blocked():
    """앞 문장 끝 몇 자 + 뒷 문장 앞 몇 자가 이어져 소스와 일치하면 걸린다
    — 문장 경계에 걸친 유출(D-01의 핵심 근거)도 원문 겹침 검사가 잡는다."""
    permanent = _permanent_block_text()
    normalized_source = narration_guard.normalize_for_overlap(permanent)
    window = normalized_source[20:33]
    assert len(window) >= narration_guard.MIN_OVERLAP_CHARS

    split_at = 7
    boundary_prefix, boundary_suffix = window[:split_at], window[split_at:]

    sentence = f"평범한 앞부분이다 {boundary_prefix}"
    next_sentence = f"{boundary_suffix} 평범한 뒷부분이다"

    matched_len, hit = narration_guard.find_source_overlap(sentence, next_sentence, (permanent,))
    assert hit is True
    assert matched_len >= narration_guard.MIN_OVERLAP_CHARS


def test_find_source_overlap_window_starting_only_in_next_sentence_does_not_block():
    """겹침 창의 시작 위치가 검사 대상 문장 밖(다음 문장 쪽)에만 있으면
    이번 문장을 자르지 않는다. 소스와 무관해야 할 문장 쪽에 우연히 걸릴
    여지를 완전히 없애기 위해 통제된 합성 소스를 쓴다(실제 소스 사용은
    이 파일의 다른 시험이 이미 담당한다)."""
    source = ("abcdefghijklmnop",)
    sentence = "zzzzzzzzzzzzzzzzzzzz"  # 소스에 없는 문자로만 구성 — 절대 안 걸린다
    next_sentence = "abcdefghijkl"  # 소스의 앞 12자와 정확히 같다

    matched_len, hit = narration_guard.find_source_overlap(sentence, next_sentence, source)
    assert hit is False
    assert matched_len == 0


def test_find_source_overlap_reports_actual_max_matched_length():
    """적중한 창은 오른쪽으로 늘려 실제 최대 겹침 길이를 구한다."""
    permanent = _permanent_block_text()
    normalized_source = narration_guard.normalize_for_overlap(permanent)
    longer_slice = normalized_source[5:25]
    assert len(longer_slice) == 20

    matched_len, hit = narration_guard.find_source_overlap(longer_slice, None, (permanent,))
    assert hit is True
    assert matched_len == 20


# ---------------------------------------------------------------------------
# inspect_sentence — 원문 겹침 갈래 통합
# ---------------------------------------------------------------------------


def test_inspect_sentence_blocks_verbatim_instruction_overlap():
    permanent = _permanent_block_text()
    normalized_source = narration_guard.normalize_for_overlap(permanent)
    twelve_char_slice = normalized_source[5:17]

    verdict = narration_guard.inspect_sentence(
        twelve_char_slice, next_sentence=None, source_texts=(permanent,)
    )
    assert verdict.disposition == "blocked"
    assert verdict.reason == "source_overlap"
    assert verdict.matched_len == 12
    assert verdict.text == ""


def test_inspect_sentence_clean_below_threshold():
    permanent = _permanent_block_text()
    normalized_source = narration_guard.normalize_for_overlap(permanent)
    eleven_char_slice = normalized_source[5:16]

    verdict = narration_guard.inspect_sentence(
        eleven_char_slice, next_sentence=None, source_texts=(permanent,)
    )
    assert verdict.disposition == "clean"
    assert verdict.text == eleven_char_slice


def test_inspect_sentence_normal_narration_stays_clean():
    permanent = _permanent_block_text()
    sentence = "부서진 등불이 흔들리며 그림자를 길게 늘어뜨린다."
    verdict = narration_guard.inspect_sentence(
        sentence, next_sentence=None, source_texts=(permanent,)
    )
    assert verdict.disposition == "clean"
    assert verdict.text == sentence


# ---------------------------------------------------------------------------
# 자기 반복(narration_repeat) — verify-13-06 사람 확인 결함1. 2026-08-26
# well_below 실측 turn(seq 112)에서 서사 스트림 하나가 문장 하나를 다 쓴 뒤
# 마침표 없이 곧바로 처음부터 되풀이했다 — 27조각 중 12조각이 앞선 조각과
# 바이트 단위로 같았다. `written_so_far`(이번 서사에서 이미 낸 문장들)를
# 원문 겹침과 같은 창-슬라이딩 대조로 잡는다(source_texts는 관여하지 않는다).
# ---------------------------------------------------------------------------


def test_inspect_sentence_blocks_verbatim_repeat_of_already_written_sentence():
    already_written = "우물 아래에서 낮게 울리는 소리가 들려오기 시작했다."
    verdict = narration_guard.inspect_sentence(
        already_written,
        next_sentence=None,
        source_texts=(),
        written_so_far=(already_written,),
    )
    assert verdict.disposition == "blocked"
    assert verdict.reason == "narration_repeat"
    assert verdict.matched_len >= narration_guard.MIN_OVERLAP_CHARS
    assert verdict.text == ""


def test_inspect_sentence_new_sentence_not_in_written_so_far_stays_clean():
    verdict = narration_guard.inspect_sentence(
        "이번에는 정말로 새로운 문장이다.",
        next_sentence=None,
        source_texts=(),
        written_so_far=("완전히 다른 앞선 문장이 이미 나갔었다.",),
    )
    assert verdict.disposition == "clean"


def test_inspect_sentence_default_written_so_far_is_empty_and_never_blocks_as_repeat():
    """기본값 `()`은 옛 호출부와의 호환이다 — `written_so_far`를 안 주면
    이 갈래는 항상 통과한다."""
    sentence = "이 문장은 어디에도 안 걸린다."
    verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
    assert verdict.disposition == "clean"


def test_inspect_sentence_source_overlap_wins_when_both_would_match():
    """원문 겹침과 자기 반복이 동시에 걸리면(같은 문장이 지시문에도, 이미 쓴
    문장에도 있는 경우) 원문 겹침이 먼저 판정된다(D-02②가 D-03보다 앞선
    안전 갈래) — `reason`이 `narration_repeat`가 아니라 `source_overlap`."""
    shared = "정확히 같은 열두 글자 이상 구절이다"
    verdict = narration_guard.inspect_sentence(
        shared, next_sentence=None, source_texts=(shared,), written_so_far=(shared,)
    )
    assert verdict.disposition == "blocked"
    assert verdict.reason == "source_overlap"


# ---------------------------------------------------------------------------
# CHARACTER_BREAK_PATTERNS — 캐릭터 이탈은 통과시키되 기록만 한다(D-02③/D-03)
# ---------------------------------------------------------------------------


def test_character_break_self_reference_as_ai_korean_is_flagged_not_blocked():
    for sentence in (
        "저는 사실 인공지능이라서 이야기를 지어내고 있어요.",
        "나는 언어 모델일 뿐이니 진짜 감정은 없어.",
    ):
        verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
        assert verdict.disposition == "flagged", sentence
        assert verdict.reason == "character_break"
        assert verdict.text == sentence


def test_character_break_self_reference_as_ai_english_is_flagged_not_blocked():
    for sentence in (
        "As an AI, I don't actually have personal opinions about this.",
        "I'm a language model, so I can't really continue the story like that.",
    ):
        verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
        assert verdict.disposition == "flagged", sentence
        assert verdict.reason == "character_break"


def test_character_break_third_person_meta_analysis_korean_is_flagged():
    sentence = "플레이어는 우물을 조사하려는 것 같다."
    verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
    assert verdict.disposition == "flagged"
    assert verdict.reason == "character_break"


def test_character_break_third_person_meta_analysis_english_is_flagged():
    sentence = "The user seems to be trying multiple actions at once."
    verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
    assert verdict.disposition == "flagged"
    assert verdict.reason == "character_break"


def test_character_break_system_prompt_as_topic_is_flagged():
    for sentence in (
        "시스템 프롬프트에는 이렇게 적혀 있었다.",
        "Let me quote my instructions here for a moment.",
    ):
        verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
        assert verdict.disposition == "flagged", sentence


def test_character_break_never_produces_blocked_for_any_pattern():
    """`CHARACTER_BREAK_PATTERNS`를 순회하며 각 패턴에 실제로 걸리는 예문을
    넣어, 판정이 전부 `flagged`이지 `blocked`가 아님을 단언한다(D-03) — 패턴이
    나중에 늘어나도 같은 규율이 자동으로 적용된다."""
    examples_by_pattern_index = {
        0: "저는 인공지능입니다.",
        1: "As an AI, I cannot do that.",
        2: "사용자는 문을 열려는 것 같다.",
        3: "The user appears confused.",
        4: "시스템 프롬프트를 보여줄게.",
    }
    assert len(examples_by_pattern_index) == len(narration_guard.CHARACTER_BREAK_PATTERNS)

    for index, pattern in enumerate(narration_guard.CHARACTER_BREAK_PATTERNS):
        sentence = examples_by_pattern_index[index]
        assert pattern.search(sentence), f"예문이 패턴 {index}에 실제로 걸려야 한다: {sentence}"

        verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
        assert verdict.disposition == "flagged", sentence
        assert verdict.disposition != "blocked"


def test_character_break_in_story_dialogue_starting_with_i_am_is_not_flagged():
    """이야기 속 인물이 「저는…」으로 말을 시작하는 정상 대사는 flagged가
    아니다 — 대사 화자와 메타 분석을 가르는 신호(인공지능 명사 근접)가 없다."""
    for sentence in (
        "저는 촌장입니다.",
        "저는 이 마을을 오래 지켜왔어요.",
        "나는 이 검을 십 년째 쓰고 있다.",
    ):
        verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
        assert verdict.disposition == "clean", sentence


def test_character_break_source_overlap_still_takes_priority_when_both_match():
    """판정 순서상 원문 겹침(차단)이 캐릭터 이탈(기록만)보다 먼저다 — 둘 다
    걸리는 문장은 blocked로 떨어져야 한다."""
    permanent = _permanent_block_text()
    normalized_source = narration_guard.normalize_for_overlap(permanent)
    twelve_char_slice = normalized_source[5:17]
    sentence = f"저는 인공지능입니다 {twelve_char_slice}"

    verdict = narration_guard.inspect_sentence(
        sentence, next_sentence=None, source_texts=(permanent,)
    )
    assert verdict.disposition == "blocked"
    assert verdict.reason == "source_overlap"


# ---------------------------------------------------------------------------
# narrate() 배선 — 오탐 경계(Task 3, SAFE-02) — 실제 narrate()를 통해 지연
# 버퍼·판정·NarrationChunk까지 관통하는 것을 확인한다.
# ---------------------------------------------------------------------------

_RULEBOOK_DISPLAY_NAME = "던전월드 계열"


_TEST_ACTOR_ID = "test.actor"

_TEST_ACTOR = Entity(
    entity_id=_TEST_ACTOR_ID,
    display_name="테스트 캐릭터",
    rulebook_id="dungeonworld_like",
    stats=(StatEntry(name="체력", form="numeric", current=5, max=10),),
)


def _real_narration_facts() -> NarrationFacts:
    """장면 대상·파티 상태가 채워진 실제 `NarrationFacts` — 세션 고정
    블록이 대조 소스에서 빠졌다는 판단이 실제로 오탐을 안 낸다는 증거로
    쓴다."""
    return NarrationFacts(
        check_summary=_CHECK_SUMMARY,
        scene_summary="문이 부서지고 서늘한 바람이 흘러든다.",
        facts=("경비병이 쓰러졌다",),
        scene_entities=THREAT_CAST,
        party_state=(_TEST_ACTOR,),
        actor_character_id=_TEST_ACTOR_ID,
        recent_turns=(),
        new_entities=(),
    )


class _NormalNarrationProvider:
    """장면 대상 이름과 캐릭터 상태값을 자연스럽게 언급하는 서사를 낸다."""

    name = "normal-narration"

    def __init__(self) -> None:
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s) -> Iterator[str]:
        yield "촌장 담녹이 문 앞에서 걱정스러운 얼굴로 서 있다. "
        yield "체력 5로 버티며 다음 상황을 지켜본다."
        self._last_result = AgentResult(
            ok=True, value="", elapsed_ms=5, prompt_tokens=2, completion_tokens=2
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result


def test_narrate_does_not_block_narration_mentioning_scene_entity_and_character_state():
    """세션 고정 블록을 대조 소스에서 뺀 판단이 실제로 오탐을 없앤다는 증거
    — 장면 대상 이름·캐릭터 상태값을 언급하는 서사가 clean으로 나온다."""
    provider = _NormalNarrationProvider()
    chunks = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=_real_narration_facts(),
            rulebook_display_name=_RULEBOOK_DISPLAY_NAME,
        )
    )
    assert len(chunks) == 2
    for chunk in chunks:
        assert chunk.disposition == "clean", chunk
    assert "촌장 담녹" in chunks[0].text
    assert "체력 5" in chunks[1].text


class _LeakingProvider:
    """영구 고정 블록의 한 구절을 그대로 옮긴 문장을 낸다(세션1에서 실제로
    난 "진행자 지시문 전체가 서사로 유출"의 축소판).

    `messages`(재생성 프롬프트)와 무관하게 매번 같은 자리(둘째 문장)에서
    걸린다는 뜻이다(10-03, `narrate()`가 재생성을 한 번 시도했다가 또
    걸리는 경로를 확인하는 데 쓴다). **첫 문장은 호출마다 다르게 낸다**
    (verify-13-06 결함1 이후 — `narrate()`가 이제 자기 반복도 잡으므로,
    재생성 호출이 원래 스트림의 첫 문장을 그대로 되풀이하면 이 시험이
    보려는 `source_overlap` 자리에 닿기도 전에 `narration_repeat`로 먼저
    걸린다. 이 이중체는 원문 유출 검사만 겨눈 시험이라 자기 반복이라는
    다른 변수를 섞지 않는다). `note_result()`도 구현한다 — 10-03부터
    두 번 다 걸린 턴은 `narrate()`가 이 메서드로 실패 껍데기를 남긴다."""

    name = "leaking-narration"

    def __init__(self, leaked_phrase: str) -> None:
        self._leaked_phrase = leaked_phrase
        self._last_result: AgentResult | None = None
        self._call_count = 0

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s) -> Iterator[str]:
        self._call_count += 1
        first_sentence = (
            "평범한 서사 한 문장이 먼저 나간다."
            if self._call_count == 1
            else "재생성이라 앞 문장과는 다른 서사를 낸다."
        )
        yield f"{first_sentence} "
        yield f"{self._leaked_phrase}. "
        yield "평범한 서사 한 문장이 뒤이어 나간다."
        self._last_result = AgentResult(
            ok=True, value="", elapsed_ms=5, prompt_tokens=2, completion_tokens=2
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


# ---------------------------------------------------------------------------
# 깨진 글자(U+FFFD) — 통과시키되 기록만 한다(10-06, SAFE-01)
# ---------------------------------------------------------------------------


def test_corrupted_glyph_is_flagged_not_blocked_and_keeps_original_text():
    sentence = f"담로의 손이 {narration_guard.REPLACEMENT_CHAR * 2} 굳었다"
    verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
    assert verdict.disposition == "flagged"
    assert verdict.reason == "corrupted_glyph"
    assert verdict.text == sentence
    assert verdict.matched_len == 2


def test_count_corrupted_glyphs_counts_replacement_char_only():
    assert narration_guard.count_corrupted_glyphs("깨끗한 문장") == 0
    assert narration_guard.count_corrupted_glyphs(narration_guard.REPLACEMENT_CHAR * 3) == 3
    assert (
        narration_guard.count_corrupted_glyphs(f"팡{narration_guard.REPLACEMENT_CHAR}낡")
        == 1
    )


def test_clean_sentence_without_replacement_char_stays_clean():
    sentence = "부서진 등불이 흔들리며 그림자를 길게 늘어뜨린다."
    verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
    assert verdict.disposition == "clean"
    assert verdict.text == sentence


def test_already_blocked_think_block_sentence_with_corrupted_glyph_stays_blocked():
    """생각 블록으로 이미 `blocked`인 문장은 깨진 글자가 섞여 있어도 사유가
    바뀌지 않는다 — 판정 순서상 생각 블록이 깨진 글자 갈래보다 먼저다."""
    sentence = f"<think>몰래 생각한다{narration_guard.REPLACEMENT_CHAR}</think> 이어진다."
    verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
    assert verdict.disposition == "blocked"
    assert verdict.reason == "think_block"


def test_already_blocked_source_overlap_sentence_with_corrupted_glyph_stays_blocked():
    permanent = _permanent_block_text()
    normalized_source = narration_guard.normalize_for_overlap(permanent)
    twelve_char_slice = normalized_source[5:17]
    sentence = f"{twelve_char_slice} {narration_guard.REPLACEMENT_CHAR}"

    verdict = narration_guard.inspect_sentence(
        sentence, next_sentence=None, source_texts=(permanent,)
    )
    assert verdict.disposition == "blocked"
    assert verdict.reason == "source_overlap"


def test_character_break_wins_over_corrupted_glyph_when_both_match():
    """판정 순서상 캐릭터 이탈이 깨진 글자보다 먼저다(먼저 온 갈래가 이긴다)
    — 두 사유를 합치는 칸을 새로 만들지 않는다."""
    sentence = f"저는 인공지능입니다 {narration_guard.REPLACEMENT_CHAR}"
    verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
    assert verdict.disposition == "flagged"
    assert verdict.reason == "character_break"


def test_sentence_of_only_corrupted_glyphs_does_not_raise():
    sentence = narration_guard.REPLACEMENT_CHAR * 3
    verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
    assert verdict.disposition == "flagged"
    assert verdict.reason == "corrupted_glyph"
    assert verdict.matched_len == 3


def test_corrupted_glyph_branch_never_produces_blocked():
    """`character_break`가 `blocked`를 절대 안 만든다는 회귀 시험
    (`test_character_break_never_produces_blocked_for_any_pattern`)과 짝을
    이루는 시험 — 깨진 글자 갈래도 어떤 개수·문맥에서도 `blocked`를 돌려주는
    코드 경로가 존재하지 않는다."""
    for count in (1, 2, 10, 37):
        sentence = f"평범한 서사 문장이다 {narration_guard.REPLACEMENT_CHAR * count} 이어진다"
        verdict = narration_guard.inspect_sentence(sentence, next_sentence=None, source_texts=())
        assert verdict.disposition == "flagged", sentence
        assert verdict.disposition != "blocked"
        assert verdict.reason == "corrupted_glyph"


# ---------------------------------------------------------------------------
# 10-07 Task 1 (WR-02): `matched_len <= subject_len`이 모든 갈래에서
# 예외 없이 성립한다 — 문장 경계를 넘는 겹침에서도.
# ---------------------------------------------------------------------------


def test_source_overlap_crossing_boundary_keeps_matched_len_within_subject_len():
    """리뷰가 재현한 그 모양을 그대로 고정한다(WR-02) — 40자짜리 원문 중
    1자만 `sentence`에, 나머지 39자를 `next_sentence`에 두면 겹침이 문장
    경계를 넘는다. 정정 전에는 `matched_len=40, subject_len=1`로
    `matched_len > subject_len`이 났다 — 이제는 `subject_len`이 이어 붙인
    길이(41)를 담아 불변식이 깨지지 않는다."""
    source = "A" * 40
    sentence = source[0]
    next_sentence = source[1:]

    verdict = narration_guard.inspect_sentence(
        sentence, next_sentence=next_sentence, source_texts=(source,)
    )

    assert verdict.disposition == "blocked"
    assert verdict.reason == "source_overlap"
    assert verdict.matched_len == 40
    assert verdict.subject_len == len(sentence) + len(next_sentence)
    assert verdict.matched_len <= verdict.subject_len


def test_source_overlap_not_crossing_boundary_keeps_subject_len_as_sentence_length():
    """겹침이 경계를 안 넘으면(문장 하나로 다 채워지면) `subject_len`은
    지금까지와 같은 `len(sentence)`다 — 이 계획이 이 경우의 동작을 안
    바꾼다는 것을 못박는다."""
    permanent = _permanent_block_text()
    normalized_source = narration_guard.normalize_for_overlap(permanent)
    twelve_char_slice = normalized_source[5:17]

    verdict = narration_guard.inspect_sentence(
        twelve_char_slice, next_sentence=None, source_texts=(permanent,)
    )

    assert verdict.disposition == "blocked"
    assert verdict.reason == "source_overlap"
    assert verdict.subject_len == len(twelve_char_slice)
    assert verdict.matched_len <= verdict.subject_len


def test_matched_len_never_exceeds_subject_len_across_all_four_branches():
    """**모든 갈래에 대한 불변식 시험(WR-02)** — 생각 블록/원문 겹침(경계
    안·밖)/캐릭터 이탈/깨진 글자 각각에 대해 `matched_len <= subject_len`을
    단언한다. 갈래가 나중에 늘어도 이 시험이 새 갈래를 강제하도록, 여기
    목록에 새 갈래를 추가하지 않고 넘어가면 `assert len(cases) == ...`가
    아니라 각 갈래를 개별 함수로 짚어 사람이 놓치지 않게 한다."""
    permanent = _permanent_block_text()
    normalized_source = narration_guard.normalize_for_overlap(permanent)
    twelve_char_slice = normalized_source[5:17]
    crossing_source = "B" * 40

    cases: dict[str, narration_guard.GuardVerdict] = {
        "think_block": narration_guard.inspect_sentence(
            "<think>몰래 생각한다</think> 이어진다.", next_sentence=None, source_texts=()
        ),
        "source_overlap_within_sentence": narration_guard.inspect_sentence(
            twelve_char_slice, next_sentence=None, source_texts=(permanent,)
        ),
        "source_overlap_crosses_boundary": narration_guard.inspect_sentence(
            crossing_source[0], next_sentence=crossing_source[1:], source_texts=(crossing_source,)
        ),
        "character_break": narration_guard.inspect_sentence(
            "저는 사실 인공지능이라서 이야기를 지어내고 있어요.", next_sentence=None, source_texts=()
        ),
        "corrupted_glyph": narration_guard.inspect_sentence(
            f"담로의 손이 {narration_guard.REPLACEMENT_CHAR * 2} 굳었다",
            next_sentence=None,
            source_texts=(),
        ),
    }

    expected_reasons = {
        "think_block": "think_block",
        "source_overlap_within_sentence": "source_overlap",
        "source_overlap_crosses_boundary": "source_overlap",
        "character_break": "character_break",
        "corrupted_glyph": "corrupted_glyph",
    }
    for name, verdict in cases.items():
        assert verdict.reason == expected_reasons[name], name
        assert verdict.matched_len <= verdict.subject_len, (
            f"{name}: matched_len={verdict.matched_len} subject_len={verdict.subject_len}"
        )


def test_source_overlap_never_truncates_matched_len_to_subject_len():
    """`matched_len`을 자르는 방식(리뷰의 (b)안)을 쓰지 않는다는 것을
    직접 확인한다 — 경계를 넘는 겹침에서 `matched_len`이 원래 `len(sentence)`
    (1)보다 훨씬 크게(40) 그대로 유지된다. 정직해진 것은 분모
    (`subject_len`)이지 분자가 아니다."""
    source = "C" * 40
    sentence = source[0]
    next_sentence = source[1:]

    verdict = narration_guard.inspect_sentence(
        sentence, next_sentence=next_sentence, source_texts=(source,)
    )

    assert verdict.matched_len == 40
    assert verdict.matched_len > len(sentence)


def test_narrate_blocks_narration_that_quotes_permanent_block_verbatim():
    """영구 고정 블록 구절을 그대로 옮긴 문장은 걸리고, `NarrationChunk`가
    `reason="source_overlap"`과 0보다 큰 `matched_len`을 싣고 나온다 —
    호출부가 사건에 담을 값이 실제로 채워진다는 뜻이다.

    10-03부터 `narrate()`는 걸린 문장을 만나면 그 자리에서 스트림 소비를
    멈추고 재생성을 한 번 시도한다(D-06). `_LeakingProvider`는 재생성
    프롬프트가 와도 매번 같은 세 문장을 내므로, 재생성도 같은 자리에서
    다시 걸린다 — 그래서 `provider.stream()`이 두 번(원래 스트림 + 재생성)
    불리고, 두 번 다 첫 문장은 clean, 둘째 문장에서 걸려 멈춘다. 재생성
    자신의 "걸렀어요" 안내는 억눌러지고(D-08 종료 안내 하나로 합친다) 두
    번 다 걸렸다는 안내(`NOTICE_GAVE_UP`)가 마지막으로 나온다."""
    system, _messages = prompt_assembly.build_gm_prompt(
        rulebook_display_name=_RULEBOOK_DISPLAY_NAME, facts=_real_narration_facts()
    )
    permanent = system[0]["text"]
    # 문장부호가 안 섞인 구간을 골라 leaked_phrase 자체가 chunk_sentences의
    # 문장 경계로 조각나지 않게 한다(정규화해도 정확히 12자 — 문턱 그대로).
    # 앞뒤 정상 서사(어느 문장이든 "다"로 끝나는 흔한 한국어 종결)와 이어
    # 붙여도 우연히 소스 다른 자리와 겹치지 않는 구절을 골랐다.
    anchor = "네 문장 안에 스스로 지어내지"
    assert anchor in permanent, "테스트 전제: 이 구절이 영구 블록에 있어야 한다"
    leaked_phrase = anchor

    provider = _LeakingProvider(leaked_phrase)
    chunks = list(
        narrate(
            provider=provider,
            model="stub-model",
            facts=_real_narration_facts(),
            rulebook_display_name=_RULEBOOK_DISPLAY_NAME,
        )
    )
    assert [chunk.disposition for chunk in chunks] == [
        "clean",
        "blocked",
        "clean",
        "blocked",
    ]
    assert chunks[1].reason == "source_overlap"
    assert chunks[1].matched_len > 0
    assert chunks[1].text == narration_guard.NOTICE_FILTERED
    assert chunks[3].text == narration_guard.NOTICE_GAVE_UP
    assert chunks[3].reason == "source_overlap"
    assert provider.last_result().ok is False
