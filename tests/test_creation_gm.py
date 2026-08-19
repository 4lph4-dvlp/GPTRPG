"""`creation_gm` — 자기소개 진행 다회 왕복 계약 시험(D-03/D-05/D-06, Phase 12.1-03).

`tests/test_outcome_picker.py`의 가짜 제공자 패턴(호출 횟수·타임아웃을
기록하는 이중체)을 그대로 빌린다. 계약 위반 경로(목록 밖 식별자·빈 후보·
`needs_more=True`인데 질문 없음)와 폴백 경로(제공자 두 번 실패)를 전부
고정한다.
"""

import json

from gptrpg.agents.creation_gm import (
    CreationGmContractViolation,
    CreationGmFollowUp,
    CreationGmNomination,
    announce_requirements,
    judge_hooks,
    nominate_speaker,
)
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import MAX_ATTEMPTS
from gptrpg.rules_core.rulebook import CreationStepDecl, PartySizeRange, Rulebook

import pytest


class _CreationGmStub:
    """`creation_gm` 시험 전용 이중체 — 호출 횟수·타임아웃을 기록하고,
    `fail_times`번까지는 예외를 던진 뒤 `complete_value`를 돌려준다."""

    name = "creation-gm-stub"

    def __init__(self, *, fail_times: int = 0, complete_value: str = "") -> None:
        self.fail_times = fail_times
        self.complete_value = complete_value
        self.call_count = 0
        self.timeouts: list[float] = []

    def list_models(self) -> list[str]:
        return ["stub-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        self.call_count += 1
        self.timeouts.append(timeout_s)
        if self.call_count <= self.fail_times:
            raise RuntimeError("creation gm provider unavailable")
        return AgentResult(
            ok=True, value=self.complete_value, elapsed_ms=2, prompt_tokens=1, completion_tokens=1
        )

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        raise NotImplementedError("creation_gm은 스트리밍하지 않는다")

    def last_result(self) -> AgentResult:
        raise NotImplementedError("이 이중체는 complete()만 시험한다")


def _rulebook_with_steps(*steps: CreationStepDecl) -> Rulebook:
    return Rulebook(
        rulebook_id="test-creation-gm-rulebook",
        display_name="시험용 룰북",
        resolution_method="2d6",
        grade_bands=(),
        resource_axes=(),
        check_trigger_mode="declared_list",
        creation_steps=steps,
        party_size_range=PartySizeRange(min_player_characters=1, max_player_characters=4),
    )


# ---------------------------------------------------------------------------
# announce_requirements — 룰북 선언에서 그대로 나온 항목 목록, 하드코딩 없음
# ---------------------------------------------------------------------------


def test_announce_requirements_response_mentions_every_step_label():
    rulebook = _rulebook_with_steps(
        CreationStepDecl(step_id="name", kind="free_text", label="캐릭터 이름"),
        CreationStepDecl(step_id="backstory", kind="free_text", label="지난 이야기"),
    )
    provider = _CreationGmStub(complete_value="캐릭터 이름과 지난 이야기가 필요합니다.")
    text = announce_requirements(rulebook, provider, "stub-model")
    assert "캐릭터 이름" in text
    assert "지난 이야기" in text


def test_announce_requirements_prompt_carries_no_hardcoded_step_names_from_a_different_rulebook():
    """룰북을 바꾸면 안내 문구가 따라 바뀐다 — 다른 룰북 항목 이름이 이
    함수·프롬프트 어디에도 하드코딩되어 있지 않다."""
    rulebook_a = _rulebook_with_steps(
        CreationStepDecl(step_id="only_a", kind="free_text", label="던전월드전용항목")
    )
    rulebook_b = _rulebook_with_steps(
        CreationStepDecl(step_id="only_b", kind="free_text", label="오픈퀘스트전용항목")
    )
    provider_a = _CreationGmStub(complete_value="")  # 빈 값 -> 기본 문구로 떨어진다
    provider_b = _CreationGmStub(complete_value="")
    text_a = announce_requirements(rulebook_a, provider_a, "stub-model")
    text_b = announce_requirements(rulebook_b, provider_b, "stub-model")
    assert "던전월드전용항목" in text_a
    assert "오픈퀘스트전용항목" not in text_a
    assert "오픈퀘스트전용항목" in text_b
    assert "던전월드전용항목" not in text_b


def test_announce_requirements_falls_back_to_rulebook_step_list_when_provider_fails_twice():
    rulebook = _rulebook_with_steps(
        CreationStepDecl(step_id="name", kind="free_text", label="캐릭터 이름", required=True),
        CreationStepDecl(step_id="pet", kind="free_text", label="반려동물", required=False),
    )
    provider = _CreationGmStub(fail_times=99)
    text = announce_requirements(rulebook, provider, "stub-model")
    assert "캐릭터 이름" in text
    assert "반려동물" in text
    assert provider.call_count == MAX_ATTEMPTS


# ---------------------------------------------------------------------------
# nominate_speaker — D-06 지목, 닫힌 후보 목록 재대조
# ---------------------------------------------------------------------------


def test_nominate_speaker_with_empty_candidates_raises_without_calling_provider():
    provider = _CreationGmStub()
    with pytest.raises(CreationGmContractViolation):
        nominate_speaker((), (), provider, "stub-model")
    assert provider.call_count == 0


def test_nominate_speaker_returns_nomination_from_closed_candidate_list():
    provider = _CreationGmStub(
        complete_value=json.dumps([{"character_id": "a", "say": "다음은 a님 차례입니다."}])
    )
    nomination = nominate_speaker(("a", "b"), (), provider, "stub-model")
    assert isinstance(nomination, CreationGmNomination)
    assert nomination.character_id in ("a", "b")
    assert nomination.character_id == "a"
    assert nomination.say


def test_nominate_speaker_rejects_a_character_id_outside_the_candidate_list():
    provider = _CreationGmStub(
        complete_value=json.dumps([{"character_id": "outsider", "say": "그럼 이제..."}])
    )
    with pytest.raises(CreationGmContractViolation):
        nominate_speaker(("a", "b"), (), provider, "stub-model")


def test_nominate_speaker_rejects_an_empty_say():
    provider = _CreationGmStub(complete_value=json.dumps([{"character_id": "a", "say": ""}]))
    with pytest.raises(CreationGmContractViolation):
        nominate_speaker(("a", "b"), (), provider, "stub-model")


def test_nominate_speaker_falls_back_to_first_candidate_when_provider_fails_twice():
    provider = _CreationGmStub(fail_times=99)
    nomination = nominate_speaker(("a", "b"), (), provider, "stub-model")
    assert nomination.character_id == "a"
    assert nomination.say
    assert provider.call_count == MAX_ATTEMPTS


# ---------------------------------------------------------------------------
# judge_hooks — D-05 위층, 갈고리 목적, 숫자 칸 없음
# ---------------------------------------------------------------------------


def test_judge_hooks_returns_follow_up_question_when_needs_more():
    provider = _CreationGmStub(
        complete_value=json.dumps(
            [{"needs_more": True, "question": "그 마을에서 특히 기억에 남는 사람이 있나요?"}]
        )
    )
    follow_up = judge_hooks(("이름",), ("플레이어: 저는 마을 출신입니다",), provider, "stub-model")
    assert isinstance(follow_up, CreationGmFollowUp)
    assert follow_up.needs_more is True
    assert follow_up.question


def test_judge_hooks_returns_no_follow_up_when_satisfied():
    provider = _CreationGmStub(complete_value=json.dumps([{"needs_more": False, "question": None}]))
    follow_up = judge_hooks(("이름",), (), provider, "stub-model")
    assert follow_up.needs_more is False
    assert follow_up.question is None


def test_judge_hooks_rejects_needs_more_true_with_empty_question():
    provider = _CreationGmStub(
        complete_value=json.dumps([{"needs_more": True, "question": ""}])
    )
    with pytest.raises(CreationGmContractViolation):
        judge_hooks(("이름",), (), provider, "stub-model")


def test_judge_hooks_falls_back_to_no_follow_up_when_provider_fails_twice():
    provider = _CreationGmStub(fail_times=99)
    follow_up = judge_hooks(("이름",), (), provider, "stub-model")
    assert follow_up.needs_more is False
    assert follow_up.question is None
    assert provider.call_count == MAX_ATTEMPTS


def test_creation_gm_nomination_and_follow_up_have_no_numeric_fields():
    """D14 — 반환 dataclass 어디에도 숫자 칸이 없다."""
    import dataclasses

    nomination_types = {str(f.type) for f in dataclasses.fields(CreationGmNomination)}
    follow_up_types = {str(f.type) for f in dataclasses.fields(CreationGmFollowUp)}
    for type_repr in nomination_types | follow_up_types:
        assert "int" not in type_repr
        assert "float" not in type_repr


# ---------------------------------------------------------------------------
# 소스 단언 — D-05 목적 번역 실수와 Pitfall 2를 시험으로 막는다
# ---------------------------------------------------------------------------


def test_creation_gm_source_mentions_the_hook_purpose_word():
    import pathlib

    source = pathlib.Path("src/gptrpg/agents/creation_gm.py").read_text(encoding="utf-8")
    assert "갈고리" in source


def test_creation_gm_source_never_tells_the_model_to_roll_dice():
    import pathlib

    source = pathlib.Path("src/gptrpg/agents/creation_gm.py").read_text(encoding="utf-8")
    assert "주사위를 굴" not in source


def test_creation_follow_up_prompt_does_not_use_the_wrong_purpose_phrase_as_the_stated_reason():
    """되묻는 목적을 「더 자세하게」로 세우지 않는다 — Pitfall 2(「주사위를
    굴려서」)도 프롬프트에 지시문으로 안 들어간다."""
    from gptrpg.agents.prompt_assembly import build_creation_follow_up_prompt

    system, _messages = build_creation_follow_up_prompt(step_labels=("이름",), transcript=())
    permanent_text = system[0]["text"]
    assert "갈고리" in permanent_text
    assert "주사위를 굴려서" not in permanent_text
