"""서사 문장 하나가 화면에 닿기 전 마지막 관문 — 순수 텍스트 판정만 한다.

이 모듈은 `agents` 안에서 `json_parsing`만 import하는 leaf다(`.importlinter`
계약 3 — `agents`는 `gptrpg.event_log`·`gptrpg.session_actor`를 모른다). 판정에
안 닿는다는 프로젝트 규율(D14/D16)이 이 파일에도 그대로 적용된다 — 여기서
정하는 것은 "이 문장을 화면에 보낼지"이지 게임 판정 수치가 아니다.

10-01은 검사 갈래를 하나만 채운다 — **추론 모델의 생각 블록**(SAFE-01, D-02①).
원문 겹침(D-02②, 10-02)·캐릭터 이탈(D-02③, 10-04)은 이 모듈에 뒤이어 붙는다.
`inspect_sentence()`가 이미 이 세 갈래를 함께 담을 반환 모양(`GuardVerdict`)을
갖고 있는 이유가 그것이다 — 나중에 갈래가 늘어도 호출부(`master_gm.narrate`)의
소비 방식은 안 바뀐다.
"""

import re
from dataclasses import dataclass

from gptrpg.agents.json_parsing import THINK_BLOCK

NOTICE_FILTERED = "이야기 한 부분을 걸렀어요. 이어서 씁니다."
"""걸러낸 자리에 대신 나가는 고정 안내 문구(D-05/SAFE-03). 걸러낸 원문에서
어떤 부분열도 끌어오지 않는다 — 이 문구 자체가 유출 통로가 되지 않는다."""

NOTICE_GAVE_UP = "이야기를 끝까지 쓰지 못했어요."
"""두 번째 시도까지 걸렸을 때 쓸 종료 안내 문구(D-08). 이 계획(10-01)은 상수만
정의한다 — 재생성 시도(D-06/D-07)를 실제로 잇는 것은 10-03이다."""

STDERR_EXCERPT_CHARS = 40
"""운영자 표준오류에 찍을 발췌 길이 상한 — 파이썬 `str` 코드포인트 개수
기준이다(바이트 수도 자소군 수도 아니다). 사건 기록에는 이 발췌가 전혀
남지 않는다(T-10-03) — 표준오류는 운영자의 자기 터미널이고 네트워크를
안 탄다는 것이 이 상수가 안전한 이유다."""

_THINK_OPEN = re.compile(r"<think>", re.IGNORECASE)
_THINK_CLOSE = re.compile(r"</think>", re.IGNORECASE)


@dataclass(frozen=True)
class GuardVerdict:
    """문장 하나에 대한 판정 결과.

    `disposition`은 `"clean"`(그대로 내보낸다) · `"blocked"`(확실 — 자동
    차단, D-03①②) · `"flagged"`(애매 — 통과시키되 기록만, D-03③) 셋 중
    하나다. 10-01은 `"clean"`과 `"blocked"`만 실제로 만든다 — `"flagged"`는
    캐릭터 이탈 검사(10-04)가 처음 쓴다.

    `text`는 `disposition == "clean"`일 때만 뜻이 있다 — `"blocked"`면
    호출부가 이 칸을 안 쓴다(대신 `NOTICE_FILTERED`를 쓴다). `matched_len`은
    원문 겹침 갈래(10-02)가 쓸 칸이고, 생각 블록 갈래에서는 언제나 0이다.
    `subject_len`은 검사 대상 문장의 코드포인트 개수(`len(sentence)` —
    파이썬 `str`은 코드포인트 단위다). `think_open`은 다음 문장을 검사할 때
    `inspect_sentence`에 그대로 다시 넘겨야 하는 상태다 — 생각 블록의 여는
    표식이 이 문장에서 안 닫혔으면 참이다.
    """

    disposition: str
    reason: str
    text: str
    matched_len: int
    subject_len: int
    think_open: bool


def strip_think_blocks(text: str) -> str:
    """완결된 `<think>...</think>` 쌍을 지운 문자열을 돌려준다.

    `json_parsing.THINK_BLOCK`을 그대로 재사용한다 — 서사 전용으로 정규식을
    다시 발명하지 않는다. 여는 표식만 있고 이 `text` 안에서 안 닫힌 조각은
    지워지지 않고 그대로 남는다 — `inspect_sentence`가 그 잔여물로
    "안 닫혔다"를 판정한다.
    """
    return THINK_BLOCK.sub("", text)


def inspect_sentence(
    sentence: str,
    *,
    next_sentence: str | None,
    source_texts: tuple[str, ...],
    think_open: bool = False,
) -> GuardVerdict:
    """이 단계(10-01)의 검사 진입점 — 생각 블록 갈래만 채운다.

    `source_texts`(원문 겹침 대조에 쓸 "우리가 프롬프트에 실제로 넣은
    문자열")는 받아 두기만 한다 — 10-02가 이 칸을 쓴다.

    **판정 순서:**
    1. `think_open`이 참이면(이전 문장에서 연 생각 블록이 아직 안 닫혔다)
       이 문장은 통째로 그 블록 안이다 — `blocked`로 판정하고, 이 문장
       안에 닫는 표식이 있는지만 확인해 다음 호출에 넘길 `think_open`을
       갱신한다.
    2. 아니면 `strip_think_blocks`로 이 문장 안에서 완결된 쌍을 지운다.
       ① 지워진 것이 있었으면(완결된 생각 블록이 이 문장 안에 통째로
       들어 있었다) `blocked`. ② 지워지지 않았어도 남은 문자열에 여는
       표식이 있으면(이 문장에서 열렸는데 안 닫혔다) `blocked`이고
       `think_open=True`를 다음 호출에 넘긴다.
    3. 둘 다 아니면 `clean` — 문장 그대로 내보낸다.

    **`next_sentence`를 직접 들여다보지 않는 이유:** "여는 표식이 문장
    1에, 닫는 표식이 문장 2에 걸쳐 있어도 잡힌다"(D-01)는 요구는
    `think_open` 상태를 호출 사이로 실어 나르는 것만으로 이미 성립한다 —
    문장 1이 `blocked`+`think_open=True`를 돌려주면, 호출부가 문장 2를 검사할
    때 그 `think_open=True`를 그대로 넘기므로 문장 2도(닫는 표식이 있어도)
    `blocked`로 잡힌다(위 1번 갈래). `next_sentence`는 그래서 이 갈래의
    판정에는 안 쓰이지만, 시그니처에는 남겨 둔다 — `narrate()`가 항상 두
    문장을 함께 들고 있고, 10-02의 원문 겹침 검사는 실제로 `next_sentence`의
    내용을 볼 수도 있다(경계에 걸친 겹침).
    """
    subject_len = len(sentence)

    if think_open:
        still_open = _THINK_CLOSE.search(sentence) is None
        return GuardVerdict(
            disposition="blocked",
            reason="think_block",
            text="",
            matched_len=0,
            subject_len=subject_len,
            think_open=still_open,
        )

    stripped = strip_think_blocks(sentence)
    had_complete_pair = stripped != sentence
    still_has_open = _THINK_OPEN.search(stripped) is not None

    if had_complete_pair or still_has_open:
        return GuardVerdict(
            disposition="blocked",
            reason="think_block",
            text="",
            matched_len=0,
            subject_len=subject_len,
            think_open=still_has_open,
        )

    return GuardVerdict(
        disposition="clean",
        reason="",
        text=sentence,
        matched_len=0,
        subject_len=subject_len,
        think_open=False,
    )
