"""위협 시계 조건 검사의 두 판단 함수 — 관문(judge_clock_signal)과 깊은 판단
(judge_clock_condition) (DP-01, D-64).

**D14를 못박는다: 이 모듈은 참/거짓 신호와 이유 문자열만 돌려주고 칸 번호를
계산하거나 돌려주는 코드가 한 줄도 없다.** 칸 번호와 상한 검사는 전부
`turn/clock_condition.py`의 코드가 한다.

`action_classifier.py`의 구조를 그대로 복제한다 — 닫힌 결과 dataclass,
`call_with_one_retry` 감싸기, 강건 JSON 파싱. 파싱은 `json_parsing.
try_parse_json_array`를 쓰고, 배열이 비었거나 첫 원소가 dict가 아니거나
값이 닫힌 목록 밖이면 **거짓 쪽으로 떨어진다**(예외를 던지지 않는다) —
`UnknownMove`에 대응하는 예외를 만들지 않는다. 무브 이름과 달리 이 판단의
닫힌 목록은 두 값뿐이라, 목록 밖 값은 "판단 못 함"과 구분할 실익이 없다.
실패하면(두 시도 모두 실패) **예외를 던지지 않고** 거짓 신호를 돌려준다 —
"없으면 없는 대로 진행"이 정상 경로다(D-05/ARCH-05).
"""

from dataclasses import dataclass

from gptrpg.agents.context import ClockJudgeContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import CLOCK_JUDGE_TIMEOUT_S, call_with_one_retry
from gptrpg.agents.json_parsing import try_parse_json_array
from gptrpg.agents.prompt_assembly import build_clock_condition_prompt, build_clock_signal_prompt
from gptrpg.agents.providers.base import Provider


@dataclass(frozen=True)
class ClockSignal:
    """`judge_clock_signal`(관문) 결과 — 이번 턴에 조건을 들여다볼 필요가 있는가."""

    should_check: bool
    why: str
    ai: AgentResult


@dataclass(frozen=True)
class ClockConditionVerdict:
    """`judge_clock_condition`(깊은 판단) 결과 — 다음 칸 조건이 실제로 충족됐는가."""

    condition_met: bool
    why: str
    ai: AgentResult


def _first_object(raw_text: str) -> dict | None:
    """`try_parse_json_array`로 배열을 뽑고 첫 원소가 dict면 그것을, 아니면 None을 돌려준다."""
    parsed = try_parse_json_array(raw_text)
    if not parsed:
        return None
    first = parsed[0]
    if not isinstance(first, dict):
        return None
    return first


def judge_clock_signal(
    *,
    provider: Provider,
    model: str,
    ctx: ClockJudgeContext,
    rulebook_display_name: str,
) -> ClockSignal:
    """관문 — "이번 턴에 시계 조건을 들여다볼 필요가 있는가"만 값싸게 거른다.

    실패하면(두 시도 모두 실패, 또는 응답이 닫힌 목록 밖이거나 깨졌으면)
    예외를 던지지 않고 `should_check=False`를 돌려준다.
    """
    system, messages = build_clock_signal_prompt(
        rulebook_display_name=rulebook_display_name,
        ctx=ctx,
    )

    def _call_once() -> AgentResult:
        return provider.complete(
            model=model,
            system=system,
            messages=messages,
            max_tokens=1024,
            timeout_s=CLOCK_JUDGE_TIMEOUT_S,
        )

    result, _last_error_text = call_with_one_retry(_call_once, timeout_s=CLOCK_JUDGE_TIMEOUT_S)
    if not result.ok:
        return ClockSignal(should_check=False, why="", ai=result)

    obj = _first_object(str(result.value))
    if obj is None:
        return ClockSignal(should_check=False, why="", ai=result)

    signal = obj.get("signal")
    why = obj.get("why", "")
    should_check = signal == "check"
    return ClockSignal(should_check=should_check, why=str(why), ai=result)


def judge_clock_condition(
    *,
    provider: Provider,
    model: str,
    ctx: ClockJudgeContext,
    rulebook_display_name: str,
    narration_text: str,
) -> ClockConditionVerdict:
    """깊은 판단 — 다음 칸에 적힌 일이 실제로 일어났다고 볼 수 있는지 판단한다.

    실패하면(두 시도 모두 실패, 또는 응답이 닫힌 목록 밖이거나 깨졌으면)
    예외를 던지지 않고 `condition_met=False`를 돌려준다.
    """
    system, messages = build_clock_condition_prompt(
        rulebook_display_name=rulebook_display_name,
        ctx=ctx,
        narration_text=narration_text,
    )

    def _call_once() -> AgentResult:
        return provider.complete(
            model=model,
            system=system,
            messages=messages,
            max_tokens=1024,
            timeout_s=CLOCK_JUDGE_TIMEOUT_S,
        )

    result, _last_error_text = call_with_one_retry(_call_once, timeout_s=CLOCK_JUDGE_TIMEOUT_S)
    if not result.ok:
        return ClockConditionVerdict(condition_met=False, why="", ai=result)

    obj = _first_object(str(result.value))
    if obj is None:
        return ClockConditionVerdict(condition_met=False, why="", ai=result)

    verdict = obj.get("verdict")
    why = obj.get("why", "")
    condition_met = verdict == "advance"
    return ClockConditionVerdict(condition_met=condition_met, why=str(why), ai=result)
