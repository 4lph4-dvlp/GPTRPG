"""위협 시계 조건 검사의 배경 실행 자리 — 웹과 CLI가 **같은 함수**를 부른다.

두 경로가 갈리지 않게 하는 것이 이 파일의 존재 이유다. `gptrpg.turn`은
`agents`와 `session_actor`를 둘 다 내려다볼 수 있는 유일한 층이다
(`.importlinter` contract:2) — 판단은 `agents`에 있고, 사건 제출은 여기
`turn`에서 한다.

**D3를 못박는다: 이 함수 밖에 배경 산출물을 사건으로 남기는 다른 경로를
만들지 않는다.** 배경 작업이 `SessionActor.submit()`을 우회해 다른 쓰기
경로로 사건을 남기면 세션당 단일 쓰기 주체 원칙이 깨진다.
"""

import asyncio
import sys

from gptrpg.agents.clock_judge import judge_clock_condition
from gptrpg.agents.context import CLOCK_JUDGE_RECENT_TURNS_LIMIT, ClockJudgeContext, TurnContext
from gptrpg.agents.providers.base import Provider
from gptrpg.session_actor.actor import AdvanceClock, SessionActor


def build_clock_judge_context(ctx: TurnContext, check_summary: str) -> ClockJudgeContext:
    """`TurnContext`에서 시계 판단이 필요로 하는 네 칸만 뽑는다.

    **정체·원하는 것·파국 문장은 옮기지 않는다** — `ClockJudgeContext`
    자체가 그 칸을 갖고 있지 않다(ARCH-06, 조건 검사에 필요 없는 시나리오
    원문을 애초에 못 받게 막는 것이 이 값 객체의 목적).
    """
    clock = ctx.clock_state
    if clock.segment_index < len(clock.segment_descriptions):
        next_segment_description = clock.segment_descriptions[clock.segment_index]
    else:
        next_segment_description = ""

    return ClockJudgeContext(
        clock_position=f"{clock.segment_index}/{clock.segment_count}",
        next_segment_description=next_segment_description,
        recent_turns=ctx.recent_turns[-CLOCK_JUDGE_RECENT_TURNS_LIMIT:],
        check_summary=check_summary,
    )


async def run_clock_condition_check(
    *,
    actor: SessionActor,
    provider: Provider,
    model: str,
    judge_ctx: ClockJudgeContext,
    rulebook_display_name: str,
    narration_text: str,
    resolve_seq: int,
    clock_id: str,
    clock_segment_count: int,
) -> None:
    """배경에서 깊은 조건 판단을 돌리고, 충족되면 시계를 한 칸 돌린다.

    `web/routes_actions.py`의 `_illustrate_scene`과 정확히 같은 3단 구조를
    복제한다:

    1. `asyncio.to_thread`로 `judge_clock_condition`을 작업 스레드에
       내보낸다(막는 AI 호출이 이벤트 루프를 잡지 않게).
    2. 어떤 예외도 위로 던지지 않는다 — `Exception`을 잡아 stderr에 경고
       한 줄만 남기고 반환한다. `condition_met`이 거짓이면 아무 일도 하지
       않고 그냥 반환한다(정상 경로, D-05).
    3. 조건 충족이면 **코드가** 다음 칸 번호를 정한다 —
       `actor.state.clock_segment`를 읽어 상한(`clock_segment_count`)을
       넘으면 아무것도 제출하지 않고 반환하고(`_prepare_clock`은 이 검사를
       하지 않으므로 여기서 해야 한다), 그렇지 않으면
       `AdvanceClock(segment_index=clock_segment + 1, trigger="condition")`를
       제출한다. 제출 실패도 삼키고 stderr 한 줄로 끝낸다.

    `actor.state` 읽기와 `actor.submit`은 반드시 이벤트 루프 스레드에서
    한다(작업 스레드로 내보내지 않는다 — sqlite3 스레드 제약).
    """
    try:
        verdict = await asyncio.to_thread(
            judge_clock_condition,
            provider=provider,
            model=model,
            ctx=judge_ctx,
            rulebook_display_name=rulebook_display_name,
            narration_text=narration_text,
        )
    except Exception as exc:  # noqa: BLE001 - 배경 작업의 실패가 요청 처리를 오염시키지 않는다(D-05)
        print(f"경고: 시계 조건 판단이 실패했다 (seq {resolve_seq}) — {exc}", file=sys.stderr)
        return

    if not verdict.condition_met:
        return

    if actor.state.clock_segment >= clock_segment_count:
        return

    try:
        await actor.submit(
            AdvanceClock(
                clock_id=clock_id,
                segment_index=actor.state.clock_segment + 1,
                trigger="condition",
                caused_by_seq=resolve_seq,
            )
        )
    except Exception as exc:  # noqa: BLE001 - 배경 작업의 실패가 요청 처리를 오염시키지 않는다(D-05)
        print(f"경고: 시계 진행 사건을 남기지 못했다 (seq {resolve_seq}) — {exc}", file=sys.stderr)
