"""상황판단 — 판정 결과·장면·시나리오를 읽어 서술이 쓸 사실 묶음을 만든다.

**이 모듈은 페르소나 지시문·규칙·시나리오 원문을 읽는 유일한 에이전트다** —
그 대가로 서술(`master_gm.narrate`)은 그것들을 아예 받지 않는다(ARCH-02).
`build_situation_prompt`(prompt_assembly.py)가 지금까지 서술 프롬프트가
갖고 있던 진행자 판단 지시문 전체를 흡수했다.

`action_classifier.py`/`clock_judge.py`와 같은 모양이다: 닫힌 결과
dataclass + `call_with_one_retry` + 강건 JSON 파싱, 실패하면(두 시도 모두
실패, 또는 응답이 깨졌으면) 예외를 던지지 않고 빈 판단으로 떨어진다
(D-05/ARCH-05) — 상황판단이 죽어도 서사는 그대로 나오고 턴이 끝까지 간다.
"""

from dataclasses import dataclass

from gptrpg.agents.context import SITUATION_FACTS_LIMIT, TurnContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import SITUATION_TIMEOUT_S, call_with_one_retry
from gptrpg.agents.json_parsing import try_parse_json_array
from gptrpg.agents.prompt_assembly import build_opening_situation_prompt, build_situation_prompt
from gptrpg.agents.providers.base import Provider
from gptrpg.rules_core.rulebook import ResourceAxisDecl
from gptrpg.rules_core.scenario import OpeningDecl


@dataclass(frozen=True)
class SituationJudgment:
    """상황판단 결과 — 서술이 쓸 장면 요약과 사실 목록 + 그 호출의 `AgentResult`."""

    scene_summary: str
    facts: tuple[str, ...]
    ai: AgentResult


def _parse_situation_response(result: AgentResult) -> SituationJudgment:
    """제공자 응답 하나를 `SituationJudgment`로 파싱한다 — `judge_situation`/
    `judge_opening_situation`이 이 함수 하나를 공유한다(13-03 Task 3 ②,
    두 함수의 파싱·자르기가 갈라질 수 없게 한다). 실패(제공자 호출 자체가
    실패, 배열이 비었거나 첫 원소가 dict가 아니거나 칸 모양이 어긋남)는
    빈 판단으로 떨어진다(D-05).

    `facts`는 문자열 원소만 남기고 `SITUATION_FACTS_LIMIT`개로 자른다 —
    **자르는 책임은 여기 있다**(`NarrationFacts`는 넘치면 예외를 던지는
    마지막 방어선이지, 정상적으로 자르는 자리가 아니다).
    """
    if not result.ok:
        return SituationJudgment(scene_summary="", facts=(), ai=result)

    parsed = try_parse_json_array(str(result.value))
    if not parsed or not isinstance(parsed[0], dict):
        return SituationJudgment(scene_summary="", facts=(), ai=result)

    obj = parsed[0]
    scene_summary = obj.get("scene_summary", "")
    if not isinstance(scene_summary, str):
        scene_summary = ""

    raw_facts = obj.get("facts", [])
    if not isinstance(raw_facts, list):
        raw_facts = []
    facts = tuple(fact for fact in raw_facts if isinstance(fact, str))[:SITUATION_FACTS_LIMIT]

    return SituationJudgment(scene_summary=scene_summary, facts=facts, ai=result)


def judge_situation(
    *,
    provider: Provider,
    model: str,
    ctx: TurnContext,
    check_summary: str,
    rulebook_display_name: str,
    resource_axes: tuple[ResourceAxisDecl, ...] = (),
) -> SituationJudgment:
    """제공자를 불러 서술용 사실 묶음을 얻는다.

    `resource_axes`(11-07)는 그대로 `build_situation_prompt`로 넘어간다.
    기본값 `()`은 「안 쓴다」로 선언된 축이 없다는 뜻이다.

    `call_with_one_retry`(D-27/D-28)를 거친다. 재시도까지 실패하면 예외를
    던지지 않고 `scene_summary=""`, `facts=()`인 빈 판단을 돌려준다(D-05).
    응답은 `try_parse_json_array`로 파싱하고, 배열이 비었거나 첫 원소가
    dict가 아니거나 칸 모양이 어긋나면 같은 빈 결과로 떨어진다.

    `facts`는 문자열 원소만 남기고 `SITUATION_FACTS_LIMIT`개로 자른다 —
    **자르는 책임은 여기 있다**(`NarrationFacts`는 넘치면 예외를 던지는
    마지막 방어선이지, 정상적으로 자르는 자리가 아니다).

    `max_tokens=1024`, `timeout_s=SITUATION_TIMEOUT_S`.
    """
    system, messages = build_situation_prompt(
        rulebook_display_name=rulebook_display_name,
        ctx=ctx,
        check_summary=check_summary,
        resource_axes=resource_axes,
    )

    def _call_once() -> AgentResult:
        return provider.complete(
            model=model,
            system=system,
            messages=messages,
            max_tokens=1024,
            timeout_s=SITUATION_TIMEOUT_S,
        )

    result, _last_error_text = call_with_one_retry(_call_once, timeout_s=SITUATION_TIMEOUT_S)
    return _parse_situation_response(result)


def judge_opening_situation(
    *,
    provider: Provider,
    model: str,
    ctx: TurnContext,
    opening: OpeningDecl,
    rulebook_display_name: str,
    resource_axes: tuple[ResourceAxisDecl, ...] = (),
) -> SituationJudgment:
    """오프닝 전용 상황판단(D-05, 13-03 Task 3) — `judge_situation`과 계약이
    정확히 같다: `call_with_one_retry`를 거치고, 재시도까지 실패하면
    예외를 던지지 않고 빈 판단으로 떨어진다(D-05/ARCH-05). 파싱·자르기는
    `_parse_situation_response`를 공유한다 — 두 함수의 계약이 갈라질 수
    없다.

    유일한 차이는 프롬프트 조립뿐이다 —
    `build_opening_situation_prompt(opening=...)`을 써서 판정을 전제하지
    않는 지시문으로 시나리오 오프닝 재료를 넘긴다(`ctx`는 판정 결과 대신
    쓰이지 않는다 — 오프닝에는 판정 결과 자체가 없다).

    `max_tokens=1024`, `timeout_s=SITUATION_TIMEOUT_S` — `judge_situation`과
    같다.
    """
    system, messages = build_opening_situation_prompt(
        rulebook_display_name=rulebook_display_name,
        ctx=ctx,
        opening=opening,
        resource_axes=resource_axes,
    )

    def _call_once() -> AgentResult:
        return provider.complete(
            model=model,
            system=system,
            messages=messages,
            max_tokens=1024,
            timeout_s=SITUATION_TIMEOUT_S,
        )

    result, _last_error_text = call_with_one_retry(_call_once, timeout_s=SITUATION_TIMEOUT_S)
    return _parse_situation_response(result)
