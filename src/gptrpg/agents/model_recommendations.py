"""권장 모델보다 작은 모델을 골랐을 때 눈에 보이게 경고한다 (G-11-2).

**막지 않는다.** 사람이 일부러 싼 모델을 쓰는 선택은 존중한다 — 이 모듈은
경고 문구를 만들어 돌려줄 뿐이고, 호출부(웹 서버 기동·CLI 명령)가 그 문구를
stderr에 찍는 것으로 끝난다. 어떤 예외도 던지지 않는다.

**왜 "권장값과 다르면 전부 경고"가 아니라 "실측된 미달 모델과 정확히 같으면만
경고"인지:** 이 저장소의 모델 크기 순서를 아는 방법이 없다(공급자가 크기
메타데이터를 안 준다). "이 모델은 작다"를 코드로 자동 판정할 근거가 없는
채로 아무 모델이나 권장값과 다르면 경고를 찍으면, 실측되지 않은 주장을
만들게 된다(재작업 전례 있음 — 실행자가 없는 시험을 있다고 적었던 사고).
그래서 이 표는 Phase 11이 실제로 네 문장·719조각을 던져 **직접 측정한** 두
모델만 담는다:

- `action_classifier`가 `meta/llama-3.1-8b-instruct`면 "굴릴 필요 없음"
  판정이 실전에서 거의 안 켜진다(`11-MODEL-FINDING.md`) — "문을 연다"조차
  `defend`로 분류했다.
- `master_gm`이 `nvidia/nemotron-3-super-120b-a12b`면 한국어 서사의 40%에
  키릴 문자·영어 낱말·조어가 섞인다(`11-NARRATION-LANGUAGE-FINDING.md`).

새 모델을 바꿔볼 때마다 이 표를 넓히는 것은 이 모듈의 범위 밖이다 — 실제로
재보고 결함이 확인되면 `known_undersized_models`에 그 모델 식별자를 추가하고
근거 문서 경로를 남긴다.

**`rules_core`는 이 모듈을 모른다.** 룰북·모델 어휘는 규칙 코어가 몰라야
한다는 계층 규율(`lint-imports` contract:2) 때문에, 이 표는 `gptrpg.agents`
층에 둔다.
"""

from collections.abc import Mapping
from dataclasses import dataclass

from gptrpg.agents.config import AgentChoice


@dataclass(frozen=True)
class ModelRecommendation:
    """한 역할에 대한 권장값 한 줄과, 실측으로 미달이 확인된 모델 목록."""

    role: str
    recommended_provider: str
    recommended_model: str
    known_undersized_models: tuple[str, ...]
    """이 정확한 모델 식별자로 실측했을 때 결함이 확인된 값만 담는다(추측 금지)."""
    what_breaks: str
    """무엇이 안 켜지는지를 사람이 읽고 다음 행동을 정할 수 있게 구체적으로 적는다."""
    finding_doc: str
    """실측 근거 문서 경로 — 저장소 루트 기준 상대 경로."""


RECOMMENDATIONS: tuple[ModelRecommendation, ...] = (
    ModelRecommendation(
        role="action_classifier",
        recommended_provider="nim",
        recommended_model="nvidia/nemotron-3-super-120b-a12b",
        known_undersized_models=("meta/llama-3.1-8b-instruct",),
        what_breaks=(
            '"굴릴 필요 없음"(no_check) 판정이 실전에서 거의 안 켜진다 — '
            '"문을 연다"처럼 교과서적인 문장조차 defend로 잘못 분류될 수 있다'
        ),
        finding_doc=".planning/phases/11-rulebook-vocabulary/11-MODEL-FINDING.md",
    ),
    ModelRecommendation(
        role="master_gm",
        recommended_provider="nim",
        recommended_model="nvidia/nemotron-3-ultra-550b-a55b",
        known_undersized_models=("nvidia/nemotron-3-super-120b-a12b",),
        what_breaks=(
            "한국어 서사에 키릴 문자·영어 낱말·조어가 섞여 나올 수 있다"
            "(실측 오염률 40%) — narration_guard의 검사는 인코딩 깨짐만 잡고"
            " 언어 이탈은 잡지 못한다"
        ),
        finding_doc=".planning/phases/11-rulebook-vocabulary/11-NARRATION-LANGUAGE-FINDING.md",
    ),
)
"""두 역할의 권장값 표. 새 역할(situation_judge 등)은 아직 실측된 미달 사례가
없으므로 여기 없다 — 없는 역할은 `check_model_recommendations`가 그냥
건너뛴다."""


def _format_warning(rec: ModelRecommendation, choice: AgentChoice) -> str:
    return (
        f"경고: {rec.role} 모델이 {choice.provider}/{choice.model}로 설정되어 있다 — "
        f"실측으로 확인된 문제: {rec.what_breaks} (근거: {rec.finding_doc}). "
        f"권장값: {rec.recommended_provider}/{rec.recommended_model}. "
        f"바꾸려면: uv run gptrpg agents set --role {rec.role} "
        f"--provider {rec.recommended_provider} --model {rec.recommended_model} "
        "(경고일 뿐 막지 않는다 — 지금 설정 그대로 계속 쓸 수 있다)"
    )


def check_model_recommendations(choices: Mapping[str, AgentChoice]) -> list[str]:
    """실측으로 미달이 확인된 모델과 정확히 같은 역할만 경고 문구로 돌려준다.

    `choices`에 역할이 아예 없으면(아직 설정 안 함) 건너뛴다 — 설정이 없을
    때의 안내는 `ConfigNotFound`/`InvalidAgentConfig`가 이미 큰 소리로
    맡는다(이 함수의 일이 아니다). 제공자까지 일치해야 경고한다 — 실측은
    `nim` 제공자로 한 것이라, 같은 모델 식별자 문자열이 다른 제공자 아래
    있으면 실측 대상이 아니다.

    빈 목록을 돌려줄 수 있다(경고 없음) — 예외를 던지지 않는다.
    """
    warnings: list[str] = []
    for rec in RECOMMENDATIONS:
        choice = choices.get(rec.role)
        if choice is None:
            continue
        if choice.provider != rec.recommended_provider:
            continue
        if choice.model in rec.known_undersized_models:
            warnings.append(_format_warning(rec, choice))
    return warnings
