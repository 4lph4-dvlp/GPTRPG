"""자유 문장 하나를 룰북의 닫힌 무브 목록과 대조해 후보로 좁힌다.

모델이 뱉은 수치·판정 결과는 여기서 읽지 않는다(D14) — 후보 목록 이름
문자열로만 모델 출력을 해석한다.
"""

import sys
from dataclasses import dataclass
from typing import Literal

from gptrpg.agents.context import TurnContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import CLASSIFIER_TIMEOUT_S, call_with_one_retry
from gptrpg.agents.json_parsing import try_parse_json_array
from gptrpg.agents.prompt_assembly import build_classifier_prompt
from gptrpg.agents.providers.base import Provider
from gptrpg.rulebooks.moves import MoveDecl

ProposalTier = Literal["single", "several", "no_check", "unclear"]
"""화면 강도 네 갈래 (D-11, 11-05).

옛 `"none"` 값을 폐기하고 대체한 것이 아니라 **개명하며 뜻을 좁혔다** —
`"none"`이 뭉뚱그리던 두 상황("굴릴 필요 없음"과 "AI가 못 알아들었음")을
`"no_check"`와 `"unclear"`로 갈랐다. `"single"`/`"several"`은 후보
개수만으로 정해지고(D-16이 폐기한 신뢰도 임계값 개념은 되살아나지 않는다),
`"no_check"`/`"unclear"`는 후보가 0개일 때 모델이 낸 `no_check` 신호
유무로 갈린다(아래 `Proposal.tier` 참조)."""

MAX_CANDIDATES = 3
"""화면에 나란히 놓을 수 있는 후보 상한 (§4.7 "후보 2~3개"). `classify`가
모델 출력을 이 개수로 자른다 — 넷 이상 와도 화면은 항상 최대 셋이다."""

NO_CHECK_SIGNAL = "no_check"
"""모델이 "이 행동은 판정이 필요 없다"를 표시하는 예약 키(RULE-15).

JSON 배열 안에 `{"no_check": true}` 원소 하나로 이 신호를 낸다 —
`_parse_candidates`가 이 키를 가진 원소를 후보가 아니라 신호로 읽는다.
지시문(`prompt_assembly.build_classifier_prompt`)도 이 상수에서 문자열을
가져와 지시문과 파서가 다른 문자열을 쓰는 사고를 코드로 막는다."""


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
    unknown_move: str | None = None
    """모델이 닫힌 목록 밖 이름을 골라서 이 응답 전체를 흡수했다는
    표시(SAFE-07, D-12, 10-05). 값이 있으면 계약 위반이 있었다는 뜻이고,
    `None`이면 그냥 아무 무브도 안 골랐다는 뜻이다 — 「못 골랐다」와 「목록
    밖 이름을 냈다」가 이 칸으로 구분된다. 목록 밖 이름이 여러 개 왔어도 이
    칸에는 처음 만난 것 하나만 담긴다(부분 신뢰 금지, `_parse_candidates`가
    첫 번째 위반에서 곧바로 예외를 던지므로 이후 이름은 애초에 안 보인다)."""
    no_check: bool = False
    """모델이 `NO_CHECK_SIGNAL`로 "이 행동은 판정이 필요 없다"를 명시적으로
    표시했다는 뜻이다(D-11, 11-05) — `unknown_move`가 「못 골랐다」와 「목록
    밖 이름을 냈다」를 가르는 것과 같은 성격의 칸으로, 「못 골랐다」와 「판정이
    필요 없다」를 가른다. 후보를 하나도 못 골랐다는 뜻이 아니다 — 오히려
    반대로, 모델이 후보 목록 자체가 필요 없다고 적극적으로 판단했다는
    뜻이다. 기본값 `False`는 제공자 실패 경로(`classify()`의
    `if not result.ok` 분기)가 이 칸을 건드리지 않고도 자동으로
    `tier == "unclear"`가 되게 한다 — 응답이 없는 상황이 "판정 없이
    진행해도 됨"으로 새지 않는다(T-11-17)."""

    @property
    def tier(self) -> ProposalTier:
        """네 값을 이 순서 그대로 계산한다 — 순서 자체가 우선순위다(D-11).

        ① `unknown_move`가 채워졌으면(목록 밖 이름 흡수) 무조건 `unclear`다
        — 이 계약 위반은 절대 ②로 새지 않는다(SAFE-07/10-05 흡수 계약,
        T-11-16). `no_check` 신호가 함께 왔어도 마찬가지다 — 계약 위반이
        신호보다 우선한다.

        ② 후보가 있으면 개수로 `single`/`several`을 정한다 — `no_check`
        신호와 후보가 동시에 와도 **후보가 이긴다**(RULE-15 adjacency).
        모델이 무브를 하나라도 골랐다는 것은 "판정이 필요 없다"는 자기
        신호보다 구체적인 근거이기 때문이다.

        ③ 후보가 0개이고 `no_check`가 참이면 `no_check`다 — 여기까지
        왔다는 것은 ①(계약 위반 없음)과 ②(후보 없음)를 이미 통과했다는
        뜻이므로 이 신호를 그대로 믿는다.

        ④ 나머지 전부(후보 0개 + 신호 없음, 또는 제공자 실패로 `no_check`가
        기본값 `False`인 경우)는 `unclear`다 — "AI가 못 알아들었다"와
        "모델이 응답을 못 했다"가 여기서 합쳐진다(D-29 유산). `no_check`
        기본값이 `False`이므로 응답이 없는 상황이 저절로 이 갈래로
        떨어진다(T-11-17).
        """
        count = len(self.candidates)
        if self.unknown_move is not None:
            return "unclear"
        if count == 1:
            return "single"
        if count >= 2:
            return "several"
        if self.no_check:
            return "no_check"
        return "unclear"


# `_try_parse_json_array`는 이제 `agents/json_parsing.py`가 소유한다(공유
# 유틸로 승격, 09-01 Task 1). 이 별칭은 기존 시험이 이 사적 이름을 직접
# 부르고 있어 이름이 사라지면 깨지기 때문에 남긴다 — 본문은 한 글자도
# 남지 않고 전부 옮겨졌다.
_try_parse_json_array = try_parse_json_array


def _parse_candidates(
    raw_text: str, known_move_ids: frozenset[str]
) -> tuple[tuple[MoveCandidate, ...], bool]:
    """모델이 돌려준 텍스트를 `(후보 튜플, no_check 신호)` 짝으로 바꾼다.

    형식이 완전히 깨졌으면 후보 없음으로 취급한다 — 후보가 하나도 없는
    것은 정상 결과다. 목록에 없는 이름이 오면 조용히 넘어가지 않고
    `UnknownMove`를 던진다. `no_check` 키를 가진 원소는 `move` 키가 없어도
    되므로, "`move` 키가 없는 원소는 건너뛴다"는 판정보다 **먼저** 신호
    원소를 본다 — 그 판정이 먼저였다면 신호 원소도 조용히 버려졌을
    것이다(11-05).
    """
    parsed = _try_parse_json_array(raw_text)

    candidates = []
    no_check = False
    for item in parsed:
        if not isinstance(item, dict):
            continue  # 형식이 깨진 원소 하나 때문에 턴 전체가 죽지 않는다
        if item.get(NO_CHECK_SIGNAL) is True:
            no_check = True
            continue
        if "move" not in item:
            continue  # 형식이 깨진 원소 하나 때문에 턴 전체가 죽지 않는다
        move_id = item["move"]
        if move_id not in known_move_ids:
            raise UnknownMove(move_id)
        candidates.append(MoveCandidate(move=move_id, stat=item.get("stat", "")))
    return tuple(candidates), no_check


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
    `Proposal`을 돌려준다(`no_check`는 기본값 `False`이므로 자동으로
    `tier == "unclear"`가 된다). 「모델이 아무 무브도 못 골랐다」와
    「모델이 응답을 못 했다」가 이제 둘 다 `unclear`로 간다는 점은 D-29가
    고른 설계 그대로다 — 새 분기 코드나 새 실패 상태를 만들지 않는다.
    D-11이 새로 가른 것은 그 둘과 「판정이 필요 없다」(`no_check`)의
    구분이다 — 응답이 없는 상황이 "판정 없이 진행해도 됨"으로 읽히지
    않는다(T-11-17).

    무브 목록 위반(`UnknownMove`)은 다르게 다룬다 — 모델이 응답을 하긴
    했는데 룰북 목록에 없는 이름을 골랐다면 그것은 제공자 장애가 아니라
    계약 위반이다. 재시도 층이 이 예외를 잡아 다시 시도하는 일이 없도록,
    목록 대조는 `call_with_one_retry` **밖에서** — 껍데기를 돌려받은
    뒤에 — 한다.

    2026-08-12 Phase 9 UAT에서 이 위반이 실제로 관찰됐다(`'track'`)
    — 그때는 이 예외가 그대로 호출부까지 올라가 명령줄은 exit 1, 웹은
    HTTP 400으로 턴 전체가 죽었다(SAFE-07). 10-05부터는 `classify()`
    함수 경계 **안에서** 이 예외를 흡수한다 — `_parse_candidates`
    자체는 여전히 예외를 던진다(계약 위반을 조용히 통과시키지 않는다는
    존재 이유는 안 바뀐다). `classify()`가 그 예외를 잡아 표준오류에
    한 줄을 남기고, 후보가 빈 `Proposal`에 `unknown_move`를 채워 돌려준다
    — `tier` 계산 ①에 걸려 반드시 `unclear`가 된다(T-11-16, `no_check`
    신호가 함께 왔어도 마찬가지다). **이것은 목록 밖 이름을 받아들이는
    것이 아니다** — 거부한 뒤 이미 있는 부드러운 경로에 태우는 것이다.
    D-16(닫힌 목록 분류)과 RIG-01은 그대로 지켜진다.

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
    try:
        candidates, no_check = _parse_candidates(str(result.value), known_move_ids)
        candidates = candidates[:MAX_CANDIDATES]
    except UnknownMove as exc:
        # 재시도 층(`call_with_one_retry`) 밖에서 잡는다 — 계약 위반을
        # 다시 시도해 봐야 같은 위반이 다시 온다(도크스트링 116~127줄).
        # `exc.move_id`는 모델이 지어낸 짧은 식별자이지 우리 지시문
        # 원문이 아니므로 그대로 표준오류에 찍어도 SAFE-03의 원문 재유출
        # 금지와 부딪히지 않는다. `no_check`를 채우지 않는다 — 이 자리는
        # tier 계산 ①에 걸려 반드시 `unclear`가 된다(T-11-16).
        print(
            f"경고: 분류기가 닫힌 목록 밖 이름을 냈다 — {exc.move_id!r}. "
            "무브 없음으로 흡수한다.",
            file=sys.stderr,
        )
        return Proposal(candidates=(), ai=result, unknown_move=exc.move_id)
    return Proposal(candidates=candidates, ai=result, no_check=no_check)
