"""세션 하나의 `GameState`에서 여섯 가설에 답할 숫자를 뽑아내는 단 하나의 곳.

이 모듈은 **`cli/`에도 `web/`에도 두지 않는다.** 04-01이 `.importlinter`
contract 2를 `gptrpg.cli | gptrpg.web`(co-equal 층)로 바꾸면 두 층은 서로
import할 수 없다 — `cli`는 `web`을 볼 수 없고 `web`도 `cli`를 볼 수 없다.
그런데 이 모듈이 만드는 값은 CLI의 `gptrpg report` 조회(이 계획)와
`SessionActor`의 자동 저장 훅(04-03) **양쪽**이 불러야 한다. 두 co-equal
층 모두가 아래로 내려다볼 수 있는 가장 가까운 공용 층이 `session_actor`다
(`.importlinter` contract 2: `gptrpg.cli | gptrpg.web` -> `gptrpg.agents` ->
`gptrpg.session_actor` -> ...) — 그래서 `build_report`/`write_report`가
여기 산다.

`build_report`는 **어떤 걸러내기도 하지 않는다.** 실패한 턴, 오류가 난 AI
호출, 서사가 끝까지 안 나온 턴이 전부 그대로 세어진다. 03-06이 실패한
서사에도 `RecordAiCall`을 반드시 제출하도록 만든 것이 바로 이 숫자가
빠지지 않게 하기 위해서였다. 이 숫자는 Phase 6의 가설 판정(재미·원가)에
그대로 들어가는 입력값이므로, 결과가 유리해 보이게 만드는 어떤 필터링도
넣지 않는다 — 실패 턴이 빠지면 「실패는 많은데 시계가 안 돈다」라는 관측
자체가 불가능해진다.
"""

import json
import re
import statistics
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from gptrpg.event_log.schema import GameEvent, utc_now_iso
from gptrpg.rules_core.reducer import GameState, apply_event, initial_state

DEFAULT_REPORTS_DIR = Path(".gptrpg/reports")

# 세션 식별자가 파일 이름으로 그대로 쓰이므로, 경로 조립 전에 허용 글자
# 범위를 여기서 못 박는다 (T-04-05).
SAFE_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# 칸 목록을 코드로 못 박는다 — `rules_core/entities.py`의
# `ENTITY_FIELD_NAMES` 관례를 따른다. 나중에 누가 칸을 더하거나 빼면
# 시험이 즉시 드러낸다.
REPORT_FIELD_NAMES = frozenset(
    {
        "session_id",
        "generated_at",
        "event_count",
        "turn_count",
        "check_count",
        "failure_count",
        "clock_segment",
        "clock_advances",
        "failure_to_clock_ratio",
        "narration_count",
        "ai_calls",
        "total_tokens",
        # 원가(H5)를 계산할 수 있게 하는 세 칸. `total_tokens` 하나로는
        # 계산이 성립하지 않는다 — 입력·출력 단가가 보통 4~5배 다르다.
        "prompt_tokens",
        "completion_tokens",
        "cached_prompt_tokens",
        # 사건 목록을 함께 넘겼을 때만 채워지는 세 칸. 넘기지 않으면 None이다.
        "latency",
        "friction",
        # 시계가 한 칸 돌 때마다의 누적 스냅샷 — 「무료로 주는 1~2칸이 얼마짜리인가」
        # (D20·D21의 상품 단위)를 세션 합계에서 갈라내는 유일한 칸이다.
        "episodes",
        "last_grade",
    }
)

D33_PROGRESS_INDICATOR_MS = 5_000
"""이 시간을 넘기면 화면에 진행 표시를 띄운다는 D-33의 문턱. 집계에서는
「그 문턱을 넘긴 호출이 몇 번이었나」를 세는 데 쓴다."""

D33_CHECK_FIRST_MS = 15_000
"""이 시간을 넘기면 판정 결과를 서사보다 먼저 내보낸다는 D-33의 문턱."""


def _parse_recorded_at(raw: str) -> datetime | None:
    """`utc_now_iso()`가 만든 문자열을 `datetime`으로 되돌린다. 못 읽으면 None.

    `utc_now_iso`가 형식을 한 자리에서만 정하므로(밀리초 3자리 + 'Z') 정상
    기록은 언제나 이 한 형식이다. 그래도 None을 돌려줄 여지를 두는 이유는,
    이 함수를 쓰는 계산이 **집계 전용**이라 형식이 어긋난 옛 기록 하나 때문에
    집계 명령 전체가 죽으면 안 되기 때문이다 — 읽히지 않는 기록은 조용히
    표본에서 빠지고, 표본 수(`sample_count`)가 그 사실을 드러낸다.
    """
    try:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        return None


def _summarize_ms(values: Sequence[int]) -> dict:
    """밀리초 표본 목록을 표본 수·중앙값·최대값 + D-33 두 문턱 초과 횟수로 접는다.

    평균이 아니라 **중앙값**을 쓴다 — 재시도 한 번(D-28)이나 스트림 정지
    워치독(90초)에 걸린 호출 하나가 평균을 끌고 가면 "사람이 보통 얼마나
    기다렸나"를 못 읽는다. 최대값을 따로 남기는 것은 그 꼬리를 잃지 않기
    위해서다.
    """
    if not values:
        return {
            "sample_count": 0,
            "median_ms": None,
            "max_ms": None,
            "over_5s": 0,
            "over_15s": 0,
        }
    return {
        "sample_count": len(values),
        "median_ms": int(statistics.median(values)),
        "max_ms": max(values),
        "over_5s": sum(1 for value in values if value > D33_PROGRESS_INDICATOR_MS),
        "over_15s": sum(1 for value in values if value > D33_CHECK_FIRST_MS),
    }


def _latency_summary(events: Sequence[GameEvent]) -> dict:
    """MEAS-02의 두 지점을 사건 기록에서 계산한다.

    ① **문장 입력 -> 행동 확인 표시** (목표 0.5초) = `action_classifier` 역할의
    `AiInvoked.latency_ms`. 그 호출이 끝나야 확인 화면이 뜬다.

    ② **확인 -> 서사 첫 글자** (목표 2초) = `action_confirmed`의 기록 시각과
    그 턴 첫 서사 조각(`chunk_index == 0`)의 기록 시각 차이. 이 값은 어느
    사건 칸에도 직접 들어 있지 않다 — `caused_by_seq` 사슬을 거꾸로 타고 두
    시각을 빼야 나온다. 그래서 이 계산이 여기 있다: `AiInvoked.latency_ms`
    (master_gm)는 **서사 전체**가 끝나기까지의 시간이라 D-33이 목표를 둔
    「첫 글자」와 다른 값이다. 둘을 섞으면 2초 목표를 달성했는지 아닌지
    판정할 수 없다.

    역할별 `latency_ms` 원본도 함께 남긴다(`by_agent_role`) — 어느 역할이
    느렸는지가 원가·모델 선택 판단의 입력이다.
    """
    by_role: dict[str, list[int]] = {}
    events_by_seq: dict[int, GameEvent] = {}
    for event in events:
        events_by_seq[event.seq] = event
        if event.event_type == "ai_invoked":
            by_role.setdefault(event.agent_role, []).append(event.latency_ms)

    first_narration_ms: list[int] = []
    for event in events:
        if event.event_type != "narration_appended" or event.chunk_index != 0:
            continue
        confirm = _confirm_behind_narration(event, events_by_seq)
        if confirm is None:
            continue
        started = _parse_recorded_at(confirm.recorded_at)
        finished = _parse_recorded_at(event.recorded_at)
        if started is None or finished is None:
            continue
        delta_ms = int((finished - started).total_seconds() * 1000)
        if delta_ms >= 0:
            first_narration_ms.append(delta_ms)

    return {
        "by_agent_role": {role: _summarize_ms(values) for role, values in sorted(by_role.items())},
        "confirm_to_first_narration": _summarize_ms(first_narration_ms),
    }


_MAX_CAUSAL_HOPS = 4
"""`caused_by_seq` 사슬을 거슬러 오를 최대 걸음 수.

지금 필요한 사슬은 두 걸음(서사 -> 판정 -> 확인)이고 여유를 조금 더 뒀다.
상한을 두는 이유는 순환 방어다 — 저장소가 순번을 단조 증가로만 발급하므로
실제로 순환이 생길 수는 없지만, 여기서 무한 루프가 나면 집계 명령이 멈춘다."""


def _confirm_behind_narration(
    narration: GameEvent, events_by_seq: dict[int, GameEvent]
) -> GameEvent | None:
    """서사 조각에서 시작해 사슬을 거슬러 그 턴의 `action_confirmed`를 찾는다.

    **사슬 모양이 두 가지라서 한 걸음씩 거슬러 오른다.** 지금 코드가 만드는
    기록은 서사의 `caused_by_seq`가 판정 사건을 가리키고 그 판정이 다시 확인
    사건을 가리킨다(`routes_actions.confirm`/`cli.turn_flow`가 `resolve_seq`를
    넘긴다). 그러나 Phase 1에 만들어진 기록에는 서사가 **확인 사건을 직접**
    가리키는 것도 있다. 한 형태만 가정하고 짜면 옛 기록에서 표본이 조용히
    0이 되고, 「지연이 없었다」와 「사슬 모양이 달라 못 읽었다」가 구분되지
    않는다 — 이미 쓴 기록을 고치지 않는다는 규약(D-12)의 짝은 **읽는 쪽이
    옛 모양을 알아보는 것**이다.

    못 찾으면 `None`. 그 표본은 조용히 빠지고 `sample_count`가 그 사실을 드러낸다.
    """
    current = narration
    for _hop in range(_MAX_CAUSAL_HOPS):
        if current.caused_by_seq is None:
            return None
        parent = events_by_seq.get(current.caused_by_seq)
        if parent is None:
            return None
        if parent.event_type == "action_confirmed":
            return parent
        current = parent
    return None


def _episode_breakdown(session_id: str, events: Sequence[GameEvent]) -> list[dict]:
    """시계가 한 칸 돌 때마다 그 시점까지의 누적 숫자를 스냅샷으로 남긴다.

    **왜 필요한가.** D20·D21이 확정한 상품 단위는 「첫 에피소드(시계 1~2칸)」이고
    무료로 나눠 주는 몫도 그것이다. 그런데 세션 전체 합계만 있으면 「무료로 주는
    1~2칸이 얼마짜리인가」를 계산할 수 없다 — 세션이 3칸까지 갔으면 합계에는
    무료 구간 밖의 몫이 섞여 있다. D21의 표가 이미 「1,000팀 = $2,500~6,000」을
    적어 두었는데 그 숫자의 입력값을 지금까지 아무도 낼 수 없었다.

    이 함수가 그 입력값을 낸다. `elapsed_ms`는 세션 첫 사건부터 그 칸이 돈
    사건까지의 기록 시각 차이이므로, 「1~2칸에 몇 시간 걸렸나」(D21 표의
    2~5시간 칸)를 실측으로 대체할 수 있다.

    **숫자를 여기서 새로 세지 않는다.** 리듀서(`apply_event`)에 사건을 하나씩
    먹여 가며 `clock_advanced`를 만날 때마다 그때의 `GameState`를 찍는다 —
    누적 규칙의 출처가 리듀서 하나뿐이라는 성질(`build_report`가 상태를 옮겨
    담기만 하는 것과 같은 이유)을 깨지 않기 위해서다. 이 함수가 따로 더하기를
    시작하면 세는 곳이 둘이 되고, 두 곳이 어긋나면 어느 쪽이 맞는지 알 수 없다.
    """
    if not events:
        return []

    started = _parse_recorded_at(events[0].recorded_at)
    state = initial_state(session_id)
    milestones: list[dict] = []

    for event in events:
        state = apply_event(state, event.event_type, event.model_dump())
        if event.event_type != "clock_advanced":
            continue
        reached = _parse_recorded_at(event.recorded_at)
        if started is not None and reached is not None:
            elapsed_ms: int | None = int((reached - started).total_seconds() * 1000)
        else:
            elapsed_ms = None
        milestones.append(
            {
                "segment_index": state.clock_segment,
                "trigger": event.trigger,
                "at_seq": event.seq,
                "elapsed_ms": elapsed_ms,
                "turn_count": state.turn_count,
                "check_count": state.check_count,
                "failure_count": state.failure_count,
                "prompt_tokens": state.prompt_tokens,
                "completion_tokens": state.completion_tokens,
                "cached_prompt_tokens": state.cached_prompt_tokens,
            }
        )
    return milestones


def _friction_buckets(events: Sequence[GameEvent]) -> dict:
    """D-28이 정한 마찰 3분류를 사건 기록에서 계산한다 (HYP-04).

    | 분류 | 뜻 | 이 기록에서 어떻게 알아보나 |
    |---|---|---|
    | `accepted_as_is` | 첫 제안이 맞음 (엔터 한 번) | 확인됨 + 고른 무브·능력치가 `system_suggestion`과 같다 |
    | `picked_other` | 후보에 있었음 (클릭 한 번) | 확인됨 + 고른 값이 제안과 다르다 |
    | `no_candidate` | 어디에도 없음 (직접 찾아야 함) | 확인 사건이 아예 없거나, 있는데 `player_confirmed=false`다 |

    세 번째 칸이 두 가지를 함께 받는 것이 이 계산의 핵심이다. 확인 사건이
    **없는** 경우는 분류기가 후보를 하나도 못 낸 것(`tier == "none"`)이고 —
    그때는 화면이 확인 버튼을 아예 만들지 않아 확인 사건이 남을 수 없다 —
    있는데 거절된 경우는 후보가 셋 다 틀려 「다시 쓰기」를 누른 것이다.
    D-28의 표에서 둘 다 「직접 찾아야 함」이므로 같은 칸에 넣는다.

    **한 가지 한계를 명시한다.** 플레이어가 「다시 쓰기」를 누르지 않고 그냥
    새 문장을 치면, 첫 시도가 실패했다는 사실이 기록에 남지 않는다 — 그
    선언은 확인 사건 없는 선언으로 남아 `no_candidate`로 세어지므로 방향은
    맞지만(마찰을 과소평가하지 않는다), 같은 행동을 두 번 시도한 것이
    두 표본으로 세어진다. 라벨을 사람이 다시 붙일 때 이 점을 보정한다 —
    `docs/experiment/hypothesis-scoring-rules.md`가 그 절차를 정한다.
    """
    confirms_by_declare: dict[int, GameEvent] = {}
    declares: list[GameEvent] = []
    for event in events:
        if event.event_type == "action_declared":
            declares.append(event)
        elif event.event_type == "action_confirmed" and event.caused_by_seq is not None:
            confirms_by_declare[event.caused_by_seq] = event

    accepted_as_is = 0
    picked_other = 0
    no_candidate = 0
    for declare in declares:
        confirm = confirms_by_declare.get(declare.seq)
        if confirm is None or not confirm.player_confirmed:
            no_candidate += 1
        elif (
            confirm.move == confirm.system_suggestion.get("move")
            and confirm.stat == confirm.system_suggestion.get("stat")
        ):
            accepted_as_is += 1
        else:
            picked_other += 1

    total = len(declares)
    if total:
        frictionless_ratio: float | None = (accepted_as_is + picked_other) / total
        unmatched_ratio: float | None = no_candidate / total
    else:
        frictionless_ratio = None
        unmatched_ratio = None

    return {
        "declared_total": total,
        "accepted_as_is": accepted_as_is,
        "picked_other": picked_other,
        "no_candidate": no_candidate,
        # HYP-04의 두 문턱(앞 둘 합쳐 95% 이상 / 세 번째 30% 미만)에 그대로
        # 대응하는 비율. 문턱 자체를 여기서 판정하지 않는다 — 판정은
        # 사람이 라벨을 다시 붙인 뒤 Phase 6이 한다.
        "frictionless_ratio": frictionless_ratio,
        "unmatched_ratio": unmatched_ratio,
    }


class UnsafeSessionId(Exception):
    """세션 식별자가 `SAFE_SESSION_ID`를 벗어났을 때 던진다.

    조용히 통과하면 그 식별자가 그대로 파일 경로 조립에 쓰여 의도치 않은
    경로(상위 디렉터리 탈출, 특수 문자로 인한 파일시스템 오류 등)로 쓰기가
    일어날 수 있다 — 파일을 쓰기 전에 반드시 거부되어야 한다.
    """

    def __init__(self, session_id: str) -> None:
        super().__init__(f"허용되지 않는 세션 식별자: {session_id!r}")
        self.session_id = session_id


def require_safe_session_id(session_id: str) -> str:
    """`session_id`가 `[A-Za-z0-9_-]{1,64}`를 벗어나면 `UnsafeSessionId`를 던진다.

    이 검사가 여기 있는 이유는 **여기가 실제로 파일 이름이 만들어지는
    자리**이기 때문이다 — HTTP 경계에도 같은 검사가 있을 수 있지만, 집계
    파일을 쓰는 경로가 나중에 다른 호출자(예: 스크립트)에게 열릴 수
    있으므로 쓰기 지점 자체가 스스로를 지켜야 한다(T-04-05).
    """
    if not SAFE_SESSION_ID.match(session_id):
        raise UnsafeSessionId(session_id)
    return session_id


def build_report(
    state: GameState,
    *,
    generated_at: str | None = None,
    events: Sequence[GameEvent] | None = None,
) -> dict:
    """`GameState` 하나에서 집계 사전을 만든다. `events`를 함께 주면 두 칸이 더 채워진다.

    숫자를 만드는 곳은 리듀서(`rules_core.reducer`) 하나뿐이다 — 상태에서
    오는 칸들은 그 값을 옮겨 담기만 하고 어떤 조건 분기·걸러내기도 두지 않는다.

    `failure_to_clock_ratio`는 `state.clock_advances`가 0이면 `None`이다
    (0으로 나누지 않는다) — 시계가 한 번도 안 돈 세션에서 비율이 0이나
    무한대로 잘못 읽히는 자리를 두지 않는다.

    **`events`가 왜 선택 인자인가.** `latency`(MEAS-02)·`friction`(HYP-04)·
    `episodes`(D20·D21의 상품 단위)는 상태 한 칸으로 접힐 수 없다 —
    `caused_by_seq` 사슬과 기록 시각을 사건 **쌍**으로 보거나, 중간 시점의
    상태를 되짚어야 나오는 값이라 리듀서가 사건 하나씩 접는 구조의 **최종**
    상태로는 만들 수 없다. 그런데 `SessionActor`는 사건을 하나 쓸 때마다 이
    함수를 부른다(D-44 자동 저장). 거기서 매번 사건 전체를 다시 읽으면 세션
    길이의 제곱으로 비용이 늘어난다 — 그래서 자동 저장 경로는 `events`를
    주지 않고(세 칸은 `None`), 사건을 어차피 전부 읽는 조회 경로
    (`gptrpg report`)만 준다. `None`은 「계산하지 않았다」는 뜻이며 「0이었다」와
    다르다.

    `generated_at`을 넘기지 않으면 `event_log.schema.utc_now_iso()`를 쓴다.
    호출자가 값을 직접 넘길 수 있게 열어 두는 이유는, 시험이 실행 시각과
    무관하게 항상 같은 사전을 얻을 수 있어야 하기 때문이다 — `_cmd_replay`가
    실행할 때마다 달라지는 값을 화면에 안 찍는 것과 같은 규율이다.
    """
    if state.clock_advances:
        failure_to_clock_ratio: float | None = state.failure_count / state.clock_advances
    else:
        failure_to_clock_ratio = None

    return {
        "session_id": state.session_id,
        "generated_at": generated_at if generated_at is not None else utc_now_iso(),
        "event_count": state.last_seq + 1,
        "turn_count": state.turn_count,
        "check_count": state.check_count,
        "failure_count": state.failure_count,
        "clock_segment": state.clock_segment,
        "clock_advances": state.clock_advances,
        "failure_to_clock_ratio": failure_to_clock_ratio,
        "narration_count": state.narration_count,
        "ai_calls": state.ai_calls,
        "total_tokens": state.total_tokens,
        "prompt_tokens": state.prompt_tokens,
        "completion_tokens": state.completion_tokens,
        "cached_prompt_tokens": state.cached_prompt_tokens,
        "latency": _latency_summary(events) if events is not None else None,
        "friction": _friction_buckets(events) if events is not None else None,
        "episodes": (
            _episode_breakdown(state.session_id, events) if events is not None else None
        ),
        "last_grade": state.last_grade,
    }


def write_report(
    state: GameState,
    *,
    base_dir: Path = DEFAULT_REPORTS_DIR,
    generated_at: str | None = None,
    events: Sequence[GameEvent] | None = None,
) -> Path:
    """`build_report(state)`를 UTF-8 JSON 파일로 저장하고 그 경로를 돌려준다.

    `require_safe_session_id`를 디렉터리를 만들거나 파일을 쓰기 **전에**
    먼저 부른다 — 식별자가 안전하지 않으면 어떤 파일도 만들어지지 않는다.

    같은 세션에 두 번 부르면 기존 파일을 덮어쓴다(누적 파일을 만들지
    않는다) — 언제 열어도 「지금까지의 합계」 하나만 보이는 것이 D-44가
    원한 성질이다.

    `events`는 `build_report`에 그대로 넘어간다 — 주면 `latency`/`friction`이
    채워지고, 안 주면 두 칸이 `None`으로 남는다. 액터의 자동 저장 훅은
    일부러 주지 않는다(위 `build_report` 도크스트링의 비용 설명 참조).
    """
    require_safe_session_id(state.session_id)
    report = build_report(state, generated_at=generated_at, events=events)
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / f"{state.session_id}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
