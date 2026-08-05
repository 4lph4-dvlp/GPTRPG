"""프롬프트를 안정성 순서(영구 고정 -> 세션 고정 -> 턴마다 변함)로 조립한다.

이 순서가 이 단계의 숨은 요구사항이다 — 캐싱 유무가 원가를 3.7배 가른다
(ROADMAP). `system`은 정확히 두 조각이다: ① **영구 고정**(룰북 이름 + 무브
목록 + 에이전트 역할 지시문 — 캠페인 내내 안 변한다) ② **세션 고정**(장면
대상·캐릭터 상태·시계 상태 — 장면이 바뀔 때만 변한다). 두 조각 모두 끝에
`cache_control`을 `{"type": "ephemeral"}`로 붙인다. `messages`는 **턴마다
변함**(최근 대화 + 이번 문장 또는 판정 요약) 한 조각뿐이다. 시각·플레이어
표시 이름·세션 식별자·추적 번호처럼 호출마다 달라지는 값은 `system` 안에
한 글자도 넣지 않는다 — 넣는 순간 그 뒤로는 캐시가 매번 깨진다.

두 에이전트가 하나의 매개변수화된 함수를 공유하지 않는 이유: 분류기는 무브
목록만 있으면 되고 진행자는 장면·시계까지 필요하므로 영구 조각의 내용
자체가 다르다(D-32가 둘을 따로 설정하게 한 것과 같은 이유).
"""

from gptrpg.agents.context import TurnContext
from gptrpg.rulebooks.moves import MoveDecl

_CACHE_CONTROL = {"type": "ephemeral"}


def _cached_block(text: str) -> dict:
    return {"type": "text", "text": text, "cache_control": _CACHE_CONTROL}


def _format_moves(moves: tuple[MoveDecl, ...]) -> str:
    lines = [
        f"- {move.move_id} ({move.display_name}, 기본 능력치 {move.default_stat}): {move.trigger}"
        for move in moves
    ]
    return "\n".join(lines)


def _format_scene_entities(entities: tuple) -> str:
    if not entities:
        return "(장면에 등장한 대상 없음)"
    lines = []
    for entity in entities:
        stats = ", ".join(f"{stat.name} {stat.current}" for stat in entity.stats)
        lines.append(f"- {entity.display_name} ({entity.entity_id}): {stats}")
    return "\n".join(lines)


def _format_character_state(stats: tuple) -> str:
    if not stats:
        return "(캐릭터 상태 없음)"
    return ", ".join(f"{stat.name} {stat.current}" for stat in stats)


def _format_clock_state(clock) -> str:
    """위협 시계 상태를 펼친다.

    노출 범위는 이름 / 정체 / 원하는 것 / 현재 칸·전체 칸 수 / 이미 지나온
    칸들의 설명 / 바로 다음 칸의 설명까지다. 파국 문장은 시계가 전체 칸을
    다 지났을 때만 붙인다 — 미리 다 보여주면 결말을 알고 서사가 뻔해진다.
    관측 지표(`clock_advances`/`fails_since_clock`)는 `ClockState`에 애초에
    없으므로 여기서 새는 경로 자체가 없다. `threat_name`이 비어 있는 기존
    호출부(시나리오 내용이 없는 `ClockState(...)`)는 예전과 같은 한 줄
    형태로 떨어진다 — 형제 포매터와 같은 "(없음)" 자리표시자 관례를 따른다.
    이 함수가 돌려주는 텍스트는 칸이 바뀔 때만 바뀐다 — 호출마다 달라지는
    값(시각·세션 식별자 등)은 한 글자도 넣지 않는다.
    """
    if not clock.threat_name:
        return f"{clock.clock_id}: {clock.segment_index}/{clock.segment_count}"

    header = (
        f"{clock.threat_name} ({clock.segment_index}/{clock.segment_count}칸) — "
        f"정체: {clock.threat_identity or '(없음)'} — "
        f"원하는 것: {clock.threat_wants or '(없음)'}"
    )

    passed = clock.segment_descriptions[: clock.segment_index]
    passed_text = (
        "\n".join(f"- {desc}" for desc in passed) if passed else "(아직 지나온 칸 없음)"
    )

    if clock.segment_index < len(clock.segment_descriptions):
        next_text = clock.segment_descriptions[clock.segment_index]
    else:
        next_text = "(다음 칸 없음)"

    lines = [header, f"지나온 칸:\n{passed_text}", f"다음 칸: {next_text}"]

    if clock.segment_index >= clock.segment_count and clock.catastrophe_text:
        lines.append(f"파국: {clock.catastrophe_text}")

    return "\n".join(lines)


def _format_recent_turns(recent_turns: tuple[str, ...]) -> str:
    if not recent_turns:
        return "(최근 대화 없음)"
    return "\n".join(recent_turns)


def _session_block_text(ctx: TurnContext) -> str:
    return (
        f"장면 대상:\n{_format_scene_entities(ctx.scene_entities)}\n\n"
        f"캐릭터 상태: {_format_character_state(ctx.character_state)}\n\n"
        f"위협 시계: {_format_clock_state(ctx.clock_state)}"
    )


def build_classifier_prompt(
    *,
    rulebook_display_name: str,
    moves: tuple[MoveDecl, ...],
    ctx: TurnContext,
    raw_text: str,
) -> tuple[list[dict], list[dict]]:
    """action_classifier 프롬프트를 조립한다. `(system, messages)` 짝을 돌려준다."""
    permanent = (
        f"너는 {rulebook_display_name} 룰북을 쓰는 TRPG의 행동 분류기다. "
        "플레이어의 자유 문장을 읽고 아래 닫힌 목록에서 어울리는 무브와 능력치를 "
        "고른다. 목록에 없는 이름을 만들어 내지 않는다. 확실하면 무브 하나만, "
        "애매하면 둘이나 셋을, 어느 것도 안 맞으면 하나도 내지 말 것. 응답은 "
        "JSON 배열로만 한다 — 예: "
        '[{"move": "hack_and_slash", "stat": "STR"}]. 어울리는 무브가 없으면 '
        "빈 배열 []을 돌려준다. 설명 문장을 덧붙이지 않는다.\n\n"
        f"무브 목록:\n{_format_moves(moves)}"
    )
    session = _session_block_text(ctx)
    system = [_cached_block(permanent), _cached_block(session)]
    turn = f"최근 대화:\n{_format_recent_turns(ctx.recent_turns)}\n\n이번 문장: {raw_text}"
    messages = [{"role": "user", "content": turn}]
    return system, messages


def build_gm_prompt(
    *,
    rulebook_display_name: str,
    ctx: TurnContext,
    check_summary: str,
) -> tuple[list[dict], list[dict]]:
    """master_gm 프롬프트를 조립한다. `(system, messages)` 짝을 돌려준다.

    아래 "최근 대화"/"판정 결과" 두 줄은 **분석 대상이 아니라 이어 쓸 이야기의
    맥락**이다 — 화자 표시("플레이어: "/"진행자: ")를 붙이는 것은
    `turn_flow._build_turn_context`가 하지만, 그 텍스트가 대화록이지 풀어야
    할 과제가 아니라는 것을 모델에게 명시적으로 못박는 건 이 함수의 몫이다
    (03-04 Task 3 라이브 검증에서 이 지시가 없어 모델이 "The user seems to
    be trying multiple actions..." 식 메타 분석·원문 되풀이를 내놓은 사례가
    나왔다).
    """
    permanent = (
        f"너는 {rulebook_display_name} 룰북을 쓰는 TRPG의 진행자다. 판정 결과를 "
        "받아 다음에 무슨 일이 일어나는지 서술한다. 수치나 판정 결과를 새로 정하지 "
        "않는다 — 이미 정해진 값을 그대로 반영해서 서술만 한다. 위협 시계가 다음 "
        "칸으로 넘어갔는지도 네가 정하지 않는다 — 그건 판정 실패가 쌓이면 시스템이 "
        "자동으로 결정하고, 넘어갔을 때는 다음 「위협 시계」 정보에 이미 반영되어 "
        "너에게 주어진다. 지금 주어진 칸 안에서 벌어지는 일만 서술하고, '위협 시계'라는 "
        "말이나 몇 번째 칸인지를 네 문장 안에 스스로 지어내지 않는다. 이어지는 "
        "「최근 대화」와 「방금 판정 결과」는 지금까지의 대화록일 뿐, 분석하거나 "
        "요약하거나 되풀이해 인용할 과제가 아니다 — 그 뒤에 무슨 일이 일어나는지 "
        "자연스러운 한국어 서사 문장으로만 이어 쓴다. 사용자·플레이어를 3인칭으로 "
        "지칭하며 상황을 설명하지 않는다 — 곧바로 다음 장면을 서술한다."
    )
    session = _session_block_text(ctx)
    system = [_cached_block(permanent), _cached_block(session)]
    turn = (
        f"최근 대화:\n{_format_recent_turns(ctx.recent_turns)}\n\n"
        f"방금 판정 결과: {check_summary}"
    )
    messages = [{"role": "user", "content": turn}]
    return system, messages
