"""판정 뒤 두 판단을 한 자리에서 병렬로 부른다 — situation_judge + clock_judge(관문).

**"무엇을 병렬로 돌릴지 정하는 런타임 분기가 아예 존재하지 않는다"는 ARCH-04를
코드 모양으로 만드는 자리다.** `gather_turn_judgments`의 `asyncio.gather`에는
`judge_situation`과 `judge_clock_signal` 두 코루틴이 **항상** 나열된다 — 이
둘이 서로의 출력을 쓰지 않는다는 사실은 D-03에 선언돼 있고, 그 사실이 여기
정적으로 박힌다. 조건부 병렬화(`if ...: gather(...) else: 순차`)는 이 파일에서
금지다 — 09-03이 세 번째 코루틴(장면 신규 대상 판단)을 같은 자리에 더할 때도
호출부는 다시 안 고친다(DP-07).

09-01이 `web/routes_actions.py`·`cli/turn_flow.py`에 인라인으로 둔 시계 신호
관문 호출(`build_clock_judge_context` + `judge_clock_signal`)이 이 모듈로
옮겨 왔다 — 두 호출부가 각자 인라인으로 부르면 판단이 두 번 돈다.

**실패 처리를 위로 미루지 않는다.** `judge_situation`/`judge_clock_signal`
모두 두 시도 다 실패해도 예외를 던지지 않는 계약이다(D-05/ARCH-05) — 그래서
`asyncio.gather`에 `return_exceptions=True`를 쓸 필요가 없다: 예외가 이
함수까지 올라올 길이 애초에 없다.
"""

import asyncio
from dataclasses import dataclass

from gptrpg.agents.clock_judge import ClockSignal, judge_clock_signal
from gptrpg.agents.context import NarrationFacts, TurnContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.providers.base import Provider
from gptrpg.agents.situation_judge import SituationJudgment, judge_situation
from gptrpg.turn.clock_condition import build_clock_judge_context


@dataclass(frozen=True)
class TurnJudgments:
    """한 턴에 병렬로 돈 판단 결과 묶음.

    (09-03이 여기에 `entity`(장면 신규 대상 판단) 칸을 하나 더한다 — 호출부
    구조는 그대로 두고 `gather_turn_judgments`의 `asyncio.gather`에 세 번째
    코루틴만 나열이 늘어난다.)
    """

    situation: SituationJudgment
    clock: ClockSignal


async def gather_turn_judgments(
    *,
    situation_provider: Provider,
    situation_model: str,
    clock_provider: Provider,
    clock_model: str,
    ctx: TurnContext,
    check_summary: str,
    rulebook_display_name: str,
) -> TurnJudgments:
    """상황판단·시계 신호 관문을 `asyncio.gather`로 동시에 부른다.

    시계 판단용 문맥(`ClockJudgeContext`)은 이 함수 안에서
    `build_clock_judge_context(ctx, check_summary)`로 만든다 — 시계 판단이
    필요로 하는 좁은 칸만 여기서 뽑는다(ARCH-06).
    """
    judge_ctx = build_clock_judge_context(ctx, check_summary)

    situation_judgment, clock_signal = await asyncio.gather(
        asyncio.to_thread(
            judge_situation,
            provider=situation_provider,
            model=situation_model,
            ctx=ctx,
            check_summary=check_summary,
            rulebook_display_name=rulebook_display_name,
        ),
        asyncio.to_thread(
            judge_clock_signal,
            provider=clock_provider,
            model=clock_model,
            ctx=judge_ctx,
            rulebook_display_name=rulebook_display_name,
        ),
    )
    return TurnJudgments(situation=situation_judgment, clock=clock_signal)


def empty_turn_judgments() -> TurnJudgments:
    """`gather_turn_judgments` 자체가 실패했을 때(방어적 경로, D-05) 쓰는 빈 판단.

    `judge_situation`/`judge_clock_signal`은 이미 실패해도 예외를 던지지
    않는 계약이라(D-05/ARCH-05) 이 경로는 정상적으로는 밟히지 않는다 — 그래도
    `gather_turn_judgments` 호출부 자체의 예상 못한 실패(예: 설정 조회 오류)가
    확인 요청/턴을 막지 않는다는 것을 웹·CLI가 같은 값으로 보장한다.
    """
    empty_ai = AgentResult(ok=False, value=None, elapsed_ms=0, prompt_tokens=0, completion_tokens=0)
    return TurnJudgments(
        situation=SituationJudgment(scene_summary="", facts=(), ai=empty_ai),
        clock=ClockSignal(should_check=False, why="", ai=empty_ai),
    )


def build_narration_facts(
    *, ctx: TurnContext, check_summary: str, judgments: TurnJudgments
) -> NarrationFacts:
    """판단 결과 + `TurnContext`의 안전한 칸(장면 대상·캐릭터 상태·최근 대화)만
    골라 `NarrationFacts`를 조립한다.

    시계 상태는 애초에 옮길 칸이 없다 — `NarrationFacts`가 그 칸을 갖고
    있지 않다(ARCH-02).
    """
    return NarrationFacts(
        check_summary=check_summary,
        scene_summary=judgments.situation.scene_summary,
        facts=judgments.situation.facts,
        scene_entities=ctx.scene_entities,
        character_state=ctx.character_state,
        recent_turns=ctx.recent_turns,
    )
