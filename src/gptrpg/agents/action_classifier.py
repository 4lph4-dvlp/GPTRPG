"""자유 문장 하나를 룰북의 닫힌 무브 목록과 대조해 후보로 좁힌다.

모델이 뱉은 수치·판정 결과는 여기서 읽지 않는다(D14) — 후보 목록 이름
문자열로만 모델 출력을 해석한다.
"""

from dataclasses import dataclass
from typing import Literal

from gptrpg.agents.context import TurnContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import CLASSIFIER_TIMEOUT_S, call_with_one_retry
from gptrpg.agents.json_parsing import try_parse_json_array
from gptrpg.agents.prompt_assembly import build_classifier_prompt
from gptrpg.agents.providers.base import Provider
from gptrpg.rulebooks.moves import MoveDecl

ProposalTier = Literal["single", "several", "none"]
"""후보 개수가 정하는 화면 강도 세 갈래 (§4.7). 신뢰도 숫자가 아니라 오직
후보 개수만으로 정해진다 — D-16이 폐기한 임계값 개념이 되살아나지 않는다."""

MAX_CANDIDATES = 3
"""화면에 나란히 놓을 수 있는 후보 상한 (§4.7 "후보 2~3개"). `classify`가
모델 출력을 이 개수로 자른다 — 넷 이상 와도 화면은 항상 최대 셋이다."""


class UnknownMove(Exception):
    """모델이 닫힌 목록에 없는 무브 이름을 돌려줬을 때 던진다.

    조용히 통과시키면 룰북에 없는 무브가 기록에 남고 이후 어디서도
    복원되지 않는다.
    """

    def __init__(self, move_id: str) -> None:
        super().__init__(f"닫힌 목록에 없는 무브: {move_id!r}")
        self.move_id = move_id


@dataclass(frozen=True)
class MoveCandidate:
    """분류기가 제안하는 무브 후보 하나."""

    move: str
    stat: str


@dataclass(frozen=True)
class Proposal:
    """분류 결과 전체 — 후보 목록 + 그 호출의 `AgentResult`.

    신뢰도 숫자를 담는 칸이 없다 — ① 임계값 개념 자체가 폐기됐고 신뢰도는
    화면 강도로만 쓰인다(D-37) ② 모델이 스스로 보고하는 신뢰도 숫자는 잘
    맞지 않는 신호이고, 후보 개수는 세 갈래 화면을 정확히 그대로 만들어
    낸다.
    """

    candidates: tuple[MoveCandidate, ...]
    ai: AgentResult

    @property
    def tier(self) -> ProposalTier:
        """후보 개수에서 그때그때 계산한다 — 별도 저장 칸이 아니다."""
        count = len(self.candidates)
        if count == 0:
            return "none"
        if count == 1:
            return "single"
        return "several"


# `_try_parse_json_array`는 이제 `agents/json_parsing.py`가 소유한다(공유
# 유틸로 승격, 09-01 Task 1). 이 별칭은 기존 시험이 이 사적 이름을 직접
# 부르고 있어 이름이 사라지면 깨지기 때문에 남긴다 — 본문은 한 글자도
# 남지 않고 전부 옮겨졌다.
_try_parse_json_array = try_parse_json_array


def _parse_candidates(raw_text: str, known_move_ids: frozenset[str]) -> tuple[MoveCandidate, ...]:
    """모델이 돌려준 텍스트를 후보 튜플로 바꾼다.

    형식이 완전히 깨졌으면 후보 없음으로 취급한다 — 후보가 하나도 없는
    것은 정상 결과다. 목록에 없는 이름이 오면 조용히 넘어가지 않고
    `UnknownMove`를 던진다.
    """
    parsed = _try_parse_json_array(raw_text)

    candidates = []
    for item in parsed:
        if not isinstance(item, dict) or "move" not in item:
            continue  # 형식이 깨진 원소 하나 때문에 턴 전체가 죽지 않는다
        move_id = item["move"]
        if move_id not in known_move_ids:
            raise UnknownMove(move_id)
        candidates.append(MoveCandidate(move=move_id, stat=item.get("stat", "")))
    return tuple(candidates)


def classify(
    *,
    provider: Provider,
    model: str,
    ctx: TurnContext,
    raw_text: str,
    moves: tuple[MoveDecl, ...],
    rulebook_display_name: str,
) -> Proposal:
    """제공자를 불러 후보를 얻는다.

    제공자를 직접 부르지 않고 `call_with_one_retry`(D-27/D-28의 타임아웃·
    재시도 층)를 거친다. 재시도까지 실패하면 예외를 던지지 않고 후보가 빈
    `Proposal`을 돌려준다 — §4.7의 「무브 없음」 경로가 이것을 그대로
    이어받는다(D-29). 「모델이 아무 무브도 못 골랐다」와 「모델이 응답을
    못 했다」가 플레이어에게는 같은 화면(판정 없이 진행)으로 보인다는 것이
    D-29가 고른 설계다 — 새 분기 코드나 새 실패 상태를 만들지 않는다.

    무브 목록 위반(`UnknownMove`)은 다르게 다룬다 — 모델이 응답을 하긴
    했는데 룰북 목록에 없는 이름을 골랐다면 그것은 제공자 장애가 아니라
    계약 위반이다. 재시도 층이 이 예외를 잡아 다시 시도하는 일이 없도록,
    목록 대조는 `call_with_one_retry` **밖에서** — 껍데기를 돌려받은
    뒤에 — 한다.

    `max_tokens=1024`. (03-04 Task 3 라이브 검증 중 한 번 4096으로 올려
    봤다가 근거 없이 되돌렸다 — 실제 문제는 토큰 부족에 의한 잘림이
    아니라 `call_with_one_retry`가 두 시도 다 예외로 실패하는 것이었다는
    증거가 나왔고, 값을 바꿔 봐도 그 실패를 고치지 못했다. 진짜 실패
    사유는 `invoke.py`의 stderr 경고 줄로 확인해야 한다.)
    """
    system, messages = build_classifier_prompt(
        rulebook_display_name=rulebook_display_name,
        moves=moves,
        ctx=ctx,
        raw_text=raw_text,
    )

    def _call_once() -> AgentResult:
        return provider.complete(
            model=model,
            system=system,
            messages=messages,
            max_tokens=1024,
            timeout_s=CLASSIFIER_TIMEOUT_S,
        )

    result, _last_error_text = call_with_one_retry(_call_once, timeout_s=CLASSIFIER_TIMEOUT_S)
    if not result.ok:
        return Proposal(candidates=(), ai=result)

    known_move_ids = frozenset(move.move_id for move in moves)
    candidates = _parse_candidates(str(result.value), known_move_ids)[:MAX_CANDIDATES]
    return Proposal(candidates=candidates, ai=result)
