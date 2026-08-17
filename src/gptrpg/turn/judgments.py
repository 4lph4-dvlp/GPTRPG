"""판정 뒤 세 판단을 한 자리에서 병렬로 부른다 — situation_judge + scene_entity_judge
+ clock_judge(관문).

**"무엇을 병렬로 돌릴지 정하는 런타임 분기가 아예 존재하지 않는다"는 ARCH-04를
코드 모양으로 만드는 자리다.** `gather_turn_judgments`의 `asyncio.gather`에는
`judge_situation`·`judge_new_entity`·`judge_clock_signal` 세 코루틴이 **항상**
나열된다 — 이 셋이 서로의 출력을 쓰지 않는다는 사실은 D-03에 선언돼 있고, 그
사실이 여기 정적으로 박힌다. 조건부 병렬화(`if ...: gather(...) else: 순차`)는
이 파일에서 금지다 — `tests/test_parallel_judgment.py`(09-03 Task 3)가 이
성질을 구문 트리로 고정한다.

09-01이 `web/routes_actions.py`·`cli/turn_flow.py`에 인라인으로 둔 시계 신호
관문 호출(`build_clock_judge_context` + `judge_clock_signal`)이 이 모듈로
옮겨 왔다 — 두 호출부가 각자 인라인으로 부르면 판단이 두 번 돈다.

**실패 처리를 위로 미루지 않는다.** `judge_situation`/`judge_new_entity`/
`judge_clock_signal` 모두 두 시도 다 실패해도 예외를 던지지 않는 계약이다
(D-05/ARCH-05) — 그래서 `asyncio.gather`에 `return_exceptions=True`를 쓸
필요가 없다: 예외가 이 함수까지 올라올 길이 애초에 없다.
"""

import asyncio
from dataclasses import dataclass

from gptrpg.agents.clock_judge import ClockSignal, judge_clock_signal
from gptrpg.agents.context import (
    EntityJudgeContext,
    ENTITY_JUDGE_RECENT_TURNS_LIMIT,
    NarrationFacts,
    TurnContext,
)
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.providers.base import Provider
from gptrpg.agents.scene_entity_judge import EntityJudgment, judge_new_entity
from gptrpg.agents.situation_judge import SituationJudgment, judge_situation
from gptrpg.rules_core.rulebook import ResourceAxisDecl
from gptrpg.turn.clock_condition import build_clock_judge_context


@dataclass(frozen=True)
class TurnJudgments:
    """한 턴에 병렬로 돈 판단 결과 묶음 — 상황판단·장면 신규 대상·시계 신호."""

    situation: SituationJudgment
    entity: EntityJudgment
    clock: ClockSignal


def _build_entity_judge_context(ctx: TurnContext, check_summary: str) -> EntityJudgeContext:
    """`TurnContext`에서 장면 신규 대상 판단이 필요로 하는 세 칸만 뽑는다.

    `build_clock_judge_context`(turn/clock_condition.py)와 같은 원리 — 정체·
    원하는 것·파국 문장·캐릭터 상태는 옮기지 않는다(ARCH-06, `EntityJudgeContext`
    자체가 그 칸을 갖고 있지 않다)."""
    return EntityJudgeContext(
        scene_entities=ctx.scene_entities,
        recent_turns=ctx.recent_turns[-ENTITY_JUDGE_RECENT_TURNS_LIMIT:],
        check_summary=check_summary,
    )


async def gather_turn_judgments(
    *,
    situation_provider: Provider,
    situation_model: str,
    entity_provider: Provider,
    entity_model: str,
    clock_provider: Provider,
    clock_model: str,
    ctx: TurnContext,
    check_summary: str,
    rulebook_display_name: str,
    resource_axes: tuple[ResourceAxisDecl, ...] = (),
) -> TurnJudgments:
    """상황판단·장면 신규 대상 판단·시계 신호 관문을 `asyncio.gather`로 동시에 부른다.

    시계 판단용 문맥(`ClockJudgeContext`)은 `build_clock_judge_context(ctx,
    check_summary)`로, 장면 신규 대상 판단용 문맥(`EntityJudgeContext`)은
    `_build_entity_judge_context(ctx, check_summary)`로 이 함수 안에서
    만든다 — 각 판단이 필요로 하는 좁은 칸만 여기서 뽑는다(ARCH-06).

    판정 없는 턴(11-06, `web/routes_actions.py`의 `proceed()` ·
    `cli/turn_flow.py`의 `no_check` 갈래)에서는 호출부가
    `check_summary=agents.context.NO_CHECK_SUMMARY`를 넘긴다 — 이 함수의
    시그니처는 바뀌지 않는다.

    `resource_axes`(11-07)는 `judge_situation`으로만 전달된다 —
    `judge_new_entity`/`judge_clock_signal`이 쓰는 프롬프트 조립 함수는
    이 계획에서 손대지 않았다. 기본값 `()`은 「안 쓴다」로 선언된 축이
    없다는 뜻이다.
    """
    clock_judge_ctx = build_clock_judge_context(ctx, check_summary)
    entity_judge_ctx = _build_entity_judge_context(ctx, check_summary)

    situation_judgment, entity_judgment, clock_signal = await asyncio.gather(
        asyncio.to_thread(
            judge_situation,
            provider=situation_provider,
            model=situation_model,
            ctx=ctx,
            check_summary=check_summary,
            rulebook_display_name=rulebook_display_name,
            resource_axes=resource_axes,
        ),
        asyncio.to_thread(
            judge_new_entity,
            provider=entity_provider,
            model=entity_model,
            ctx=entity_judge_ctx,
            rulebook_display_name=rulebook_display_name,
        ),
        asyncio.to_thread(
            judge_clock_signal,
            provider=clock_provider,
            model=clock_model,
            ctx=clock_judge_ctx,
            rulebook_display_name=rulebook_display_name,
        ),
    )
    return TurnJudgments(situation=situation_judgment, entity=entity_judgment, clock=clock_signal)


def empty_turn_judgments() -> TurnJudgments:
    """`gather_turn_judgments` 자체가 실패했을 때(방어적 경로, D-05) 쓰는 빈 판단.

    `judge_situation`/`judge_new_entity`/`judge_clock_signal`은 이미 실패해도
    예외를 던지지 않는 계약이라(D-05/ARCH-05) 이 경로는 정상적으로는 밟히지
    않는다 — 그래도 `gather_turn_judgments` 호출부 자체의 예상 못한 실패(예:
    설정 조회 오류)가 확인 요청/턴을 막지 않는다는 것을 웹·CLI가 같은 값으로
    보장한다.
    """
    empty_ai = AgentResult(ok=False, value=None, elapsed_ms=0, prompt_tokens=0, completion_tokens=0)
    return TurnJudgments(
        situation=SituationJudgment(scene_summary="", facts=(), ai=empty_ai),
        entity=EntityJudgment(entities=(), ai=empty_ai),
        clock=ClockSignal(should_check=False, why="", ai=empty_ai),
    )


def build_narration_facts(
    *, ctx: TurnContext, check_summary: str, judgments: TurnJudgments
) -> NarrationFacts:
    """판단 결과 + `TurnContext`의 안전한 칸(장면 대상·파티 상태·최근 대화)만
    골라 `NarrationFacts`를 조립한다.

    `party_state`/`actor_character_id`는 `ctx`에서 그대로 옮긴다(12-05,
    D-17/D-18) — 서술도 지금 행동한 사람 하나가 아니라 파티 전원의 상태를
    받아야 세션1의 사고가 되풀이되지 않는다.

    `new_entities`는 `judgments.entity.entities`의 `name`만 뽑아 채운다 —
    `judge_new_entity`가 이미 `NEW_ENTITY_LIMIT`으로 잘라 뒀으므로 여기서
    다시 자르지 않는다. 시계 상태는 애초에 옮길 칸이 없다 — `NarrationFacts`가
    그 칸을 갖고 있지 않다(ARCH-02).

    판정 없는 턴에서는 호출부가 `check_summary=agents.context.NO_CHECK_SUMMARY`를
    넘긴다(11-06) — 이 함수의 시그니처는 바뀌지 않는다.
    """
    return NarrationFacts(
        check_summary=check_summary,
        scene_summary=judgments.situation.scene_summary,
        facts=judgments.situation.facts,
        scene_entities=ctx.scene_entities,
        party_state=ctx.party_state,
        actor_character_id=ctx.actor_character_id,
        recent_turns=ctx.recent_turns,
        new_entities=tuple(entity.name for entity in judgments.entity.entities),
    )
