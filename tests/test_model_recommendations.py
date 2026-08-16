"""G-11-2 — 실측으로 미달이 확인된 모델과 정확히 같으면 경고, 아니면 조용함.

`gptrpg.agents.model_recommendations.check_model_recommendations`가 순수
함수이므로 이 파일은 그 함수 자체를 직접 부른다. 웹·CLI 쪽 호출부(경고가
실제로 stderr에 뜨는지)는 `test_agent_config.py`(`agents show`/`agents set`)와
`test_cli.py`(`turn`)가 이미 갖춘 `capsys` 관례를 그대로 따라 각 파일에서
따로 검증한다."""

from gptrpg.agents.config import AgentChoice
from gptrpg.agents.model_recommendations import (
    RECOMMENDATIONS,
    check_model_recommendations,
)


def test_recommendations_cover_exactly_the_two_measured_roles():
    assert {rec.role for rec in RECOMMENDATIONS} == {"action_classifier", "master_gm"}


def test_known_undersized_action_classifier_model_produces_one_warning():
    choices = {
        "action_classifier": AgentChoice(provider="nim", model="meta/llama-3.1-8b-instruct"),
    }
    warnings = check_model_recommendations(choices)
    assert len(warnings) == 1
    assert "action_classifier" in warnings[0]
    assert "meta/llama-3.1-8b-instruct" in warnings[0]
    assert "nvidia/nemotron-3-super-120b-a12b" in warnings[0]  # 권장값이 문구에 있다
    assert "11-MODEL-FINDING.md" in warnings[0]  # 근거 문서 경로가 문구에 있다


def test_known_undersized_master_gm_model_produces_one_warning():
    choices = {
        "master_gm": AgentChoice(provider="nim", model="nvidia/nemotron-3-super-120b-a12b"),
    }
    warnings = check_model_recommendations(choices)
    assert len(warnings) == 1
    assert "master_gm" in warnings[0]
    assert "nvidia/nemotron-3-ultra-550b-a55b" in warnings[0]  # 권장값이 문구에 있다
    assert "11-NARRATION-LANGUAGE-FINDING.md" in warnings[0]


def test_both_roles_undersized_produces_two_warnings():
    choices = {
        "action_classifier": AgentChoice(provider="nim", model="meta/llama-3.1-8b-instruct"),
        "master_gm": AgentChoice(provider="nim", model="nvidia/nemotron-3-super-120b-a12b"),
    }
    assert len(check_model_recommendations(choices)) == 2


def test_recommended_models_produce_no_warning():
    choices = {
        "action_classifier": AgentChoice(
            provider="nim", model="nvidia/nemotron-3-super-120b-a12b"
        ),
        "master_gm": AgentChoice(provider="nim", model="nvidia/nemotron-3-ultra-550b-a55b"),
    }
    assert check_model_recommendations(choices) == []


def test_unmeasured_model_produces_no_warning():
    """실측되지 않은 모델은 「작다」고 주장하지 않는다 — 근거 없는 경고를
    만들지 않는다(no_unverified_claims)."""
    choices = {
        "action_classifier": AgentChoice(provider="nim", model="some-other-model"),
        "master_gm": AgentChoice(provider="anthropic", model="claude-haiku"),
    }
    assert check_model_recommendations(choices) == []


def test_missing_role_is_skipped_without_error():
    """설정이 아예 없는 역할은 건너뛴다 — 없다는 사실 자체는
    `ConfigNotFound`/`InvalidAgentConfig`가 이미 큰 소리로 맡는다."""
    assert check_model_recommendations({}) == []


def test_known_undersized_model_string_under_different_provider_is_not_flagged():
    """실측은 `nim` 제공자로 했다 — 같은 모델 식별자 문자열이 다른 제공자
    아래 있으면 그 실측의 대상이 아니므로 경고하지 않는다."""
    choices = {
        "action_classifier": AgentChoice(
            provider="openrouter", model="meta/llama-3.1-8b-instruct"
        ),
    }
    assert check_model_recommendations(choices) == []


def test_warning_mentions_it_does_not_block():
    choices = {
        "master_gm": AgentChoice(provider="nim", model="nvidia/nemotron-3-super-120b-a12b"),
    }
    warnings = check_model_recommendations(choices)
    assert "막지 않는다" in warnings[0]
