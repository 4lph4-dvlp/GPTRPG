"""결과 카테고리 선택 판단 — 판정 등급이 나온 뒤, 룰북의 닫힌 결과 목록에서
AI가 하나(또는 `max_picks`까지) 고르고 코드가 다시 대조한다(RULE-13, D-11).

`scene_entity_judge.py`/`clock_judge.py`와 같은 모양이다: 닫힌 결과
dataclass + `call_with_one_retry` + 강건 JSON 파싱. **제공자 호출 자체가
실패**하면(재시도까지 실패) 예외를 던지지 않고 빈 판단으로 떨어진다
(D-05/ARCH-05) — 여기까지는 다른 판단들과 같다.

**다만 모델이 닫힌 목록 밖 식별자를 냈을 때는 다르다.** 그것은 제공자
장애가 아니라 계약 위반이므로 `UnknownOutcomeCategoryFromAI`를 조용히
무시하거나 가장 비슷한 것으로 대체하지 않고 그대로 던진다(T-12-27) —
`action_classifier._parse_candidates`가 `UnknownMove`를 던지는 것과 같은
구분·같은 무게다. 결과 카테고리는 자원을 실제로 바꾸는 통로라 무브
이름보다 가볍게 다룰 수 없다.

**두 개의 조기 반환.** 고를 수 있는 목록이 비었거나(`outcome_list.categories
== ()`, RULE-13 empty) 이번 등급에 대가가 붙지 않으면(`costs=False`) 모델을
아예 부르지 않고 빈 선택 + 빈 `AgentResult`를 돌려준다 — AI 호출이 0회다.
이 조기 반환은 `gather` 밖의 조건 분기가 아니라 **함수 안의 순수 판단**
이다 — `turn/judgments.gather_turn_judgments`는 언제나 `pick_outcome`을
부르고, 부를지 말지를 그 함수 밖에서 조건 분기로 정하지 않는다(그 함수
도크스트링이 금지하는 「조건부 병렬화」에 해당하지 않는다).
"""

from dataclasses import dataclass

from gptrpg.agents.context import OutcomePickerContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import SCENE_ENTITY_TIMEOUT_S, call_with_one_retry
from gptrpg.agents.json_parsing import try_parse_json_array
from gptrpg.agents.prompt_assembly import build_outcome_picker_prompt
from gptrpg.agents.providers.base import Provider
from gptrpg.rules_core.rulebook import OutcomeList


class UnknownOutcomeCategoryFromAI(Exception):
    """모델이 결과 목록 밖의 카테고리 식별자를 돌려줬을 때 던진다.

    조용히 무시하거나 가장 비슷한 항목으로 대체하지 않는다(T-12-27) — 결과
    카테고리는 자원을 실제로 바꾸는 통로라 무브 이름보다 무겁게 다룬다.
    모델이 낸 원문 문자열을 예외 메시지에 싣지 않는다(T-12-29, T-10-03
    관례) — 값은 `category_id` 속성으로만 노출한다.
    """

    def __init__(self, category_id: str) -> None:
        super().__init__("모델이 결과 목록 밖의 카테고리 식별자를 돌려줬다")
        self.category_id = category_id


@dataclass(frozen=True)
class OutcomePick:
    """결과 선택 판단 결과 — 고른 카테고리 식별자 목록 + 그 호출의 `AgentResult`.

    여기 담기는 순서는 모델이 답한 순서일 뿐이다 — **적용 순서는 이 목록의
    순서가 아니라** `rules_core.rulebook.ordered_categories`가 룰북 선언
    순서로 다시 정한다(RULE-13 ordering, 재생 일치).
    """

    category_ids: tuple[str, ...]
    ai: AgentResult


def _parse_picks(raw_text: str, allowed_ids: frozenset[str], max_picks: int) -> tuple[str, ...]:
    """모델이 돌려준 텍스트를 카테고리 식별자 튜플로 바꾼다.

    문자열이 아닌 원소는 건너뛴다 — 형식이 깨진 원소 하나 때문에 턴 전체가
    죽지 않는다(`scene_entity_judge._parse_entities`/`action_classifier.
    _parse_candidates`와 같은 규율). 문자열인데 닫힌 목록 밖이면
    `UnknownOutcomeCategoryFromAI` — 조용히 넘어가지 않는다. `max_picks`
    보다 많이 오면 앞에서부터 자른다(`scene_entity_judge`가 `NEW_ENTITY_LIMIT`
    으로 하는 것과 같은 모양).
    """
    parsed = try_parse_json_array(raw_text)
    picks: list[str] = []
    for item in parsed:
        if not isinstance(item, str):
            continue
        if item not in allowed_ids:
            raise UnknownOutcomeCategoryFromAI(item)
        picks.append(item)
    return tuple(picks)[:max_picks]


def pick_outcome(
    *,
    provider: Provider,
    model: str,
    ctx: OutcomePickerContext,
    outcome_list: OutcomeList,
    costs: bool,
    rulebook_display_name: str,
) -> OutcomePick:
    """제공자를 불러 룰북의 닫힌 결과 목록에서 이번 판정에 어울리는
    카테고리를 고른다.

    **두 조기 반환(함수 안의 순수 판단, `gather` 밖 조건 분기가 아니다):**
    `outcome_list.categories`가 비었거나 `costs`가 거짓이면 모델을 아예
    부르지 않고 빈 선택 + 빈 `AgentResult`를 돌려준다.

    `call_with_one_retry`(D-27/D-28)를 거친다. 재시도까지 실패하면 예외를
    던지지 않고 `category_ids=()`인 빈 선택을 돌려준다(D-05). **모델이
    닫힌 목록 밖 식별자를 냈을 때는 다르다** — `_parse_picks`가 던지는
    `UnknownOutcomeCategoryFromAI`를 여기서 흡수하지 않고 그대로
    올려보낸다(T-12-27).

    `max_tokens=1024`, `timeout_s=SCENE_ENTITY_TIMEOUT_S` — 닫힌 목록에서
    몇 개를 고르는 경량 판단이라 `scene_entity_judge`와 같은 층의 값을
    쓴다(D-27이 잠근 두 값 `CLASSIFIER_TIMEOUT_S`/`GM_TIMEOUT_S`는 건드리지
    않는다).
    """
    if not outcome_list.categories or not costs:
        empty_ai = AgentResult(
            ok=True, value=None, elapsed_ms=0, prompt_tokens=0, completion_tokens=0
        )
        return OutcomePick(category_ids=(), ai=empty_ai)

    system, messages = build_outcome_picker_prompt(
        rulebook_display_name=rulebook_display_name,
        ctx=ctx,
    )

    def _call_once() -> AgentResult:
        return provider.complete(
            model=model,
            system=system,
            messages=messages,
            max_tokens=1024,
            timeout_s=SCENE_ENTITY_TIMEOUT_S,
        )

    result, _last_error_text = call_with_one_retry(_call_once, timeout_s=SCENE_ENTITY_TIMEOUT_S)
    if not result.ok:
        return OutcomePick(category_ids=(), ai=result)

    allowed_ids = frozenset(category.category_id for category in outcome_list.categories)
    picks = _parse_picks(str(result.value), allowed_ids, outcome_list.max_picks)
    return OutcomePick(category_ids=picks, ai=result)
