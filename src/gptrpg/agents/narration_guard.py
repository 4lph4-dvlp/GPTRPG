"""서사 문장 하나가 화면에 닿기 전 마지막 관문 — 순수 텍스트 판정만 한다.

이 모듈은 `agents` 안에서 `json_parsing`만 import하는 leaf다(`.importlinter`
계약 3 — `agents`는 `gptrpg.event_log`·`gptrpg.session_actor`를 모른다). 판정에
안 닿는다는 프로젝트 규율(D14/D16)이 이 파일에도 그대로 적용된다 — 여기서
정하는 것은 "이 문장을 화면에 보낼지"이지 게임 판정 수치가 아니다.

10-01은 검사 갈래를 하나만 채웠다 — **추론 모델의 생각 블록**(SAFE-01, D-02①).
10-02가 나머지 둘을 채운다 — **원문 겹침**(D-02②, Task 1): 우리가 프롬프트에
실제로 넣은 진행자 지시문 원문과 겹치는 문장을 결정론적으로 잡아 자동
차단한다. **캐릭터 이탈**(D-02③, Task 2): 자기 지칭·3인칭 메타 분석·시스템
화제 삼기 신호를 잡되 D-03에 따라 절대 차단하지 않고 통과시키며 기록만
남긴다. `inspect_sentence()`가 이 세 갈래를 함께 담는 반환 모양
(`GuardVerdict`)을 갖고 있는 이유가 그것이다 — 갈래가 늘어도 호출부
(`master_gm.narrate`)의 소비 방식은 안 바뀐다.

10-06이 네 번째 갈래를 더한다 — **깨진 글자**(SAFE-01, 2026-08-14 10-04
실측 중 발견). 앞의 셋은 안전 갈래(지시문·시나리오 원문 유출, 캐릭터
이탈)고, 이것만 **품질 갈래**다 — 지시문도 원문도 새지 않는다. 그래서
`blocked`가 아니라 `flagged`다: 받침 복잡한 한글 음절을 못 뱉는 모델은
한 세션 안의 거의 모든 문장에서 U+FFFD를 흘리므로, 차단했다면 10-03의
재생성·포기 경로를 타고 게임이 통째로 멈췄을 것이다. 실제로 일어난 실패는
「깨진 글자가 화면에 나온 것」이 아니라 **「아무도 모른 채 사건 기록에
영구 저장된 것」**이었다 — 이 갈래는 그 침묵만 없앤다. 탐지는 다른 세
갈래와 마찬가지로 내용 무관이다: `REPLACEMENT_CHAR`가 문장에 있는지만
본다. 문구 목록도 모델 이름 분기도 없다.
"""

import re
import unicodedata
from dataclasses import dataclass

from gptrpg.agents.json_parsing import THINK_BLOCK
from gptrpg.rules_core.scenario import OpeningDecl

MIN_OVERLAP_CHARS = 12
"""정규화 후 이 글자 수 이상 겹치면 원문 유출로 본다(D-02②, 10-02 계획 판단
2). 한국어에서 12자는 대략 대여섯 어절이라 우연히 겹칠 일이 거의 없고,
진행자 지시문 한 구절을 그대로 옮긴 유출은 거의 항상 이보다 길다."""

NOTICE_FILTERED = "이야기 한 부분을 걸렀어요. 이어서 씁니다."
"""걸러낸 자리에 대신 나가는 고정 안내 문구(D-05/SAFE-03). 걸러낸 원문에서
어떤 부분열도 끌어오지 않는다 — 이 문구 자체가 유출 통로가 되지 않는다."""

NOTICE_GAVE_UP = "이야기를 끝까지 쓰지 못했어요."
"""두 번째 시도까지 걸렸을 때 쓸 종료 안내 문구(D-08). 이 계획(10-01)은 상수만
정의한다 — 재생성 시도(D-06/D-07)를 실제로 잇는 것은 10-03이다."""

REPLACEMENT_CHAR = "�"
"""U+FFFD(대체문자) — 디코딩이 원래 바이트를 복원하지 못했다는 표식이다.
2026-08-14 10-04 실측 도중 `nvidia/nemotron-3-ultra-550b-a55b`가 받침 복잡한
한글 음절(팡·낡·꽉·꺾·찔·녘·섰)을 못 뱉어, 네트워크 원시 바이트에 이미
`EF BF BD`가 들어온 채로(비스트리밍으로 받아도 같다) 사건 기록에 영구
저장된 사고가 있었다. **이 갈래는 복구를 시도하지 않는다** — U+FFFD가
나왔다는 것은 원래 바이트가 이미 사라졌다는 뜻이라 무엇이었는지 알 방법이
없다. 추측해서 채우면 없는 사실을 지어내는 것이므로, 이 갈래가 하는 일은
「있었다는 사실을 기록하는 것」뿐이다."""

STDERR_EXCERPT_CHARS = 40
"""운영자 표준오류에 찍을 발췌 길이 상한 — 파이썬 `str` 코드포인트 개수
기준이다(바이트 수도 자소군 수도 아니다). 사건 기록에는 이 발췌가 전혀
남지 않는다(T-10-03) — 표준오류는 운영자의 자기 터미널이고 네트워크를
안 탄다는 것이 이 상수가 안전한 이유다."""

_THINK_OPEN = re.compile(r"<think>", re.IGNORECASE)
_THINK_CLOSE = re.compile(r"</think>", re.IGNORECASE)

CHARACTER_BREAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    # 자기 지칭(한국어) — 세션1에서 실제로 관찰된 실패(docs/session1-code-review.md:83,
    # "TRPG말고 원래 AI로 돌아와" 이후 AI가 "나리의 여자친구 사귀기 조언이
    # 필요하신가요?" 식으로 응답). "저는 촌장입니다" 같은 정상 대사와 가르기
    # 위해 대명사와 인공지능 명사가 근접해 함께 있을 때만 잡는다.
    re.compile(r"(저는|나는)[^.!?]{0,10}(인공지능|언어\s*모델|챗봇|어시스턴트|AI)"),
    # 자기 지칭(영어) — 같은 계열의 영어 표현.
    re.compile(
        r"\b(as an ai|i am an ai|i'm an ai|i am a language model|i'm a language model|"
        r"as a language model)\b",
        re.IGNORECASE,
    ),
    # 3인칭 메타 분석(한국어) — 플레이어/사용자의 의도를 분석하는 말투.
    re.compile(
        r"(플레이어|사용자)[는가][^.!?]{0,15}(려는\s*것\s*같|려고\s*하는\s*것\s*같|"
        r"려고\s*한다|듯\s*하다|것으로\s*보인다)"
    ),
    # 3인칭 메타 분석(영어) — 03-04 Task 3 라이브 검증에서 실제로 관찰된 오작동
    # ("The user seems to be trying multiple actions...", prompt_assembly.py
    # build_gm_prompt 도크스트링 170-176줄에 인용).
    re.compile(r"\bthe user (seems|appears|is trying|might be trying)\b", re.IGNORECASE),
    # 시스템 프롬프트·지시문 자체를 화제로 삼기 — 이야기 어휘에 없는 메타 용어라
    # 오탐 위험이 낮다.
    re.compile(r"(시스템\s*프롬프트|진행자\s*지시문|system prompt|my instructions)", re.IGNORECASE),
)
"""캐릭터 이탈로 보이는 말투를 잡는 정규식 목록(D-02③) — **절대 차단으로
승격하지 않는다**(D-03). 오탐 비용이 낮으므로(통과시키고 기록만 하면 되니까)
넓게 잡아도 된다 — 넓게 보되 좁게 자른다."""


@dataclass(frozen=True)
class GuardVerdict:
    """문장 하나에 대한 판정 결과.

    `disposition`은 `"clean"`(그대로 내보낸다) · `"blocked"`(확실 — 자동
    차단, D-03①②) · `"flagged"`(애매 — 통과시키되 기록만, D-03③) 셋 중
    하나다. 10-01은 `"clean"`과 `"blocked"`(생각 블록)만 만들었다. 10-02가
    `"blocked"`(원문 겹침, Task 1)과 `"flagged"`(캐릭터 이탈, Task 2)를
    마저 채운다.

    `text`는 `disposition`이 `"clean"` 또는 `"flagged"`일 때만 원문을
    담는다 — `"blocked"`면 호출부가 이 칸을 안 쓴다(대신 `NOTICE_FILTERED`를
    쓴다). `matched_len`은 원문 겹침 갈래에서 실제 겹친 길이, 캐릭터 이탈
    갈래에서 걸린 부분의 길이를 담고, 생각 블록 갈래에서는 언제나 0이다.

    `subject_len`은 **이 판정의 `matched_len`을 잰 대상 텍스트의 길이**다
    (10-07, WR-02 정정 — 예전에는 "검사 대상 문장의 코드포인트 개수"라고
    적혀 있었는데, 원문 겹침 갈래가 실제로 무엇을 대조하는지와 어긋났다).
    생각 블록·캐릭터 이탈·깨진 글자 세 갈래는 `sentence` 하나만 대조하므로
    `subject_len == len(sentence)` 그대로다. **원문 겹침 갈래만 다르다** —
    겹침이 `sentence`를 넘어 `next_sentence`까지 뻗었으면 대조 대상 자체가
    두 문장을 이어 붙인 텍스트이므로 `subject_len = len(sentence) +
    len(next_sentence or "")`다(넘지 않았으면 다른 세 갈래와 똑같이
    `len(sentence)`). **`matched_len`을 자르지 않는다** — 분모(`subject_len`)를
    정직하게 넓히는 쪽을 택했다(리뷰의 (b)안 거부). 유출이 실제로 얼마나
    컸는지가 14단계 심각도 분석이 쓸 정보라, 분자를 깎으면 그 정보가
    사라진다. 이 선택 때문에 `matched_len <= subject_len`이 네 갈래 모두에서
    예외 없이 성립한다. `think_open`은 다음 문장을 검사할 때
    `inspect_sentence`에 그대로 다시 넘겨야 하는 상태다 — 생각 블록의 여는
    표식이 이 문장에서 안 닫혔으면 참이다.
    """

    disposition: str
    reason: str
    text: str
    matched_len: int
    subject_len: int
    think_open: bool


def normalize_for_overlap(text: str) -> str:
    """원문 겹침 대조용 정규화(D-02② 계획 판단 3) — 이 순서 그대로 수행한다:
    NFC 정규화 → 유니코드 Cf(폭 없는 문자) 제거 → casefold → 공백·구두점
    (유니코드 카테고리 `P*`)·기호(`S*`) 제거.

    같은 뜻을 구두점만 바꿔 쓴 두 문자열(쉼표 하나 추가, 따옴표로 감싸기
    등)은 이 함수를 거치면 결과가 같아진다 — 「조금만 바꿔 쓴 유출」을
    놓치지 않기 위해서다. 빈 문자열·공백뿐인 문자열은 빈 문자열을 돌려준다.
    """
    normalized = unicodedata.normalize("NFC", text)
    no_format_chars = "".join(ch for ch in normalized if unicodedata.category(ch) != "Cf")
    folded = no_format_chars.casefold()
    return "".join(
        ch for ch in folded if not ch.isspace() and unicodedata.category(ch)[0] not in ("P", "S")
    )


def find_source_overlap(
    sentence: str, next_sentence: str | None, source_texts: tuple[str, ...]
) -> tuple[int, bool]:
    """`sentence`(다음 문장 `next_sentence`까지 이어 붙여)가 `source_texts`
    중 하나와 `MIN_OVERLAP_CHARS`자 이상 겹치는지 결정론적으로 대조한다.

    `(matched_len, hit)` 짝을 돌려준다 — `hit`이 참이면 `matched_len`은
    실제로 겹친 최대 길이(코드포인트 개수)다. `source_texts`가 비어 있으면
    검사를 건너뛴다(`(0, False)`, 10-01 상태와의 호환).

    절차: `h = normalize_for_overlap(sentence)`, `n =
    normalize_for_overlap(next_sentence or "")`, `j = h + n`. 소스도 각각
    정규화해 둔다. 시작 위치가 `0`부터 `len(h) - 1`까지인 길이
    `MIN_OVERLAP_CHARS` 창을 `j` 위에서 밀며, 그 창이 정규화된 소스 중
    하나의 부분열이면 적중이다 — **시작 위치가 `len(h)` 안에 있어야만**
    적중으로 치므로, 다음 문장 쪽에만 있는 겹침으로 이번 문장을 자르지
    않는다. 적중한 창은 오른쪽으로 더 늘려 실제 최대 겹침 길이를 구한다.
    `h`가 비어 있거나(빈 문장·공백뿐) `MIN_OVERLAP_CHARS`보다 짧으면서
    `next_sentence`가 없으면(또는 짧으면) 어떤 시작 위치도 12자 창을 채울
    수 없어 자동으로 clean이 된다 — 별도 분기가 필요 없다.
    """
    if not source_texts:
        return 0, False

    h = normalize_for_overlap(sentence)
    n = normalize_for_overlap(next_sentence or "")
    joined = h + n
    normalized_sources = tuple(normalize_for_overlap(src) for src in source_texts)

    max_matched = 0
    for start in range(len(h)):
        end = start + MIN_OVERLAP_CHARS
        if end > len(joined):
            continue
        window = joined[start:end]
        if not any(window in src for src in normalized_sources):
            continue
        while end < len(joined) and any(joined[start : end + 1] in src for src in normalized_sources):
            end += 1
        max_matched = max(max_matched, end - start)

    if max_matched > 0:
        return max_matched, True
    return 0, False


def strip_think_blocks(text: str) -> str:
    """완결된 `<think>...</think>` 쌍을 지운 문자열을 돌려준다.

    `json_parsing.THINK_BLOCK`을 그대로 재사용한다 — 서사 전용으로 정규식을
    다시 발명하지 않는다. 여는 표식만 있고 이 `text` 안에서 안 닫힌 조각은
    지워지지 않고 그대로 남는다 — `inspect_sentence`가 그 잔여물로
    "안 닫혔다"를 판정한다.
    """
    return THINK_BLOCK.sub("", text)


def count_corrupted_glyphs(text: str) -> int:
    """`text` 안의 `REPLACEMENT_CHAR` 개수를 센다 — 함수로 빼는 이유는
    시험이 이 성질(내용 무관, 개수만 본다)을 `inspect_sentence` 전체를
    거치지 않고 직접 겨눌 수 있게 하기 위해서다."""
    return text.count(REPLACEMENT_CHAR)


def inspect_sentence(
    sentence: str,
    *,
    next_sentence: str | None,
    source_texts: tuple[str, ...],
    think_open: bool = False,
) -> GuardVerdict:
    """서사 검사 진입점 — 네 갈래(생각 블록/원문 겹침/캐릭터 이탈/깨진 글자)를
    모두 채운다(10-02·10-06).

    `source_texts`는 "우리가 프롬프트에 실제로 넣은 문자열"이다 —
    `find_source_overlap`이 이 값을 원문 겹침 대조 소스로 그대로 쓴다.

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
    3. 생각 블록이 없으면 `find_source_overlap(sentence, next_sentence,
       source_texts)`로 원문 겹침을 대조한다(D-02②) — 적중하면 `blocked`,
       `reason="source_overlap"`, `matched_len`에 실제 겹친 길이를 담는다.
       `text`는 빈 문자열이다 — 걸린 원문을 이 칸에 담지 않는다. **`subject_len`도
       이 갈래에서만 다르게 잡는다**(10-07, WR-02) — 겹침이 `sentence`를 넘어
       `next_sentence`까지 뻗었으면 `subject_len = len(sentence) +
       len(next_sentence or "")`(대조 대상이 두 문장을 이어 붙인 텍스트이기
       때문이다), 안 넘었으면 다른 갈래와 같이 `len(sentence)`다. `matched_len`은
       절대 자르지 않는다 — `GuardVerdict` 도크스트링 참조.
    4. 원문 겹침도 없으면 `CHARACTER_BREAK_PATTERNS`를 순회한다(D-02③) —
       하나라도 걸리면 `flagged`, `reason="character_break"`, `text`는
       **원문 그대로**(호출부가 이 문장을 그대로 내보낸다), `matched_len`은
       걸린 부분의 길이다. **이 갈래는 절대 `blocked`를 돌려주지 않는다**
       (D-03) — 오탐이어도 통과시키는 편의 비용이 멀쩡한 서사를 잘못 자르는
       비용보다 낮다.
    5. 캐릭터 이탈도 없으면 `count_corrupted_glyphs(sentence)`를 본다
       (10-06, SAFE-01) — 하나라도 있으면 `flagged`, `reason="corrupted_glyph"`,
       `text`는 **원문 그대로**, `matched_len`은 깨진 글자 개수다. 이 갈래도
       **절대 `blocked`를 돌려주지 않는다** — 깨진 글자는 안전 유출이 아니라
       품질 결함이다(모듈 도크스트링 참조). 캐릭터 이탈이 앞선 갈래이므로
       두 사유가 동시에 걸리는 문장은 `character_break`가 이긴다(먼저 온
       갈래가 이긴다) — 두 사유를 합치는 칸을 새로 만들지 않는다.
    6. 다섯 다 아니면 `clean` — 문장 그대로 내보낸다.

    **`next_sentence`를 직접 들여다보지 않는 이유(생각 블록 갈래):** "여는
    표식이 문장 1에, 닫는 표식이 문장 2에 걸쳐 있어도 잡힌다"(D-01)는
    요구는 `think_open` 상태를 호출 사이로 실어 나르는 것만으로 이미
    성립한다 — 문장 1이 `blocked`+`think_open=True`를 돌려주면, 호출부가
    문장 2를 검사할 때 그 `think_open=True`를 그대로 넘기므로 문장 2도
    (닫는 표식이 있어도) `blocked`로 잡힌다(위 1번 갈래). **원문 겹침
    갈래는 반대로 `next_sentence`를 실제로 쓴다** — 문장 경계에 걸쳐
    이어지는 겹침(앞 문장 끝 몇 자 + 뒷 문장 앞 몇 자가 이어져 소스와
    일치)을 잡으려면 두 문장을 이어 붙여 봐야 하기 때문이다.
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

    matched_len, overlap_hit = find_source_overlap(sentence, next_sentence, source_texts)
    if overlap_hit:
        # `subject_len`을 바로잡는다(10-07, WR-02) — 겹침이 `sentence`를 넘어
        # `next_sentence`까지 뻗었으면 대조 대상 자체가 두 문장을 이어 붙인
        # 텍스트이므로 분모도 이어 붙인 길이여야 한다. 넘었는지는 "next_sentence
        # 없이 `sentence` 혼자 대조했을 때의 최대 겹침 길이"와 비교해 판정한다
        # — 혼자서는 못 미쳤는데(next_sentence 없이는 이 길이가 안 나오는데)
        # next_sentence를 더했더니 늘었다면, 그 늘어난 몫은 반드시
        # `len(sentence)`를 넘어선 자리에서 나온 것이다(순수하게 `sentence`
        # 안쪽 창만으로는 `find_source_overlap(sentence, None, ...)`가 이미
        # 그 최대값을 찾아냈을 것이므로). `matched_len`은 자르지 않는다 —
        # 값을 자르는 대신 분모를 정직하게 넓히는 것이 이 판단의 핵심이다.
        if next_sentence:
            matched_len_within_sentence, _ = find_source_overlap(sentence, None, source_texts)
        else:
            matched_len_within_sentence = matched_len
        if matched_len > matched_len_within_sentence:
            overlap_subject_len = len(sentence) + len(next_sentence or "")
        else:
            overlap_subject_len = len(sentence)
        return GuardVerdict(
            disposition="blocked",
            reason="source_overlap",
            text="",
            matched_len=matched_len,
            subject_len=overlap_subject_len,
            think_open=False,
        )

    for pattern in CHARACTER_BREAK_PATTERNS:
        match = pattern.search(sentence)
        if match:
            return GuardVerdict(
                disposition="flagged",
                reason="character_break",
                text=sentence,
                matched_len=len(match.group(0)),
                subject_len=subject_len,
                think_open=False,
            )

    corrupted_count = count_corrupted_glyphs(sentence)
    if corrupted_count > 0:
        return GuardVerdict(
            disposition="flagged",
            reason="corrupted_glyph",
            text=sentence,
            matched_len=corrupted_count,
            subject_len=subject_len,
            think_open=False,
        )

    return GuardVerdict(
        disposition="clean",
        reason="",
        text=sentence,
        matched_len=0,
        subject_len=subject_len,
        think_open=False,
    )


def _normalize_for_hook_match(text: str) -> str:
    """NFC 정규화 + 공백 제거 — 오프닝 완결성 검사(`inspect_opening_completeness`)
    전용 정규화다. 같은 한글이 조합형/분해형으로 오거나 공백이 다르게
    들어가도 같은 낱말로 인식되게 한다.

    `normalize_for_overlap`(원문 겹침 대조용)과는 다른 목적이라 casefold·
    구두점 제거는 하지 않는다 — `hook_terms` 대조는 원문 유출 검사가
    아니라 "이 낱말이 텍스트 안에 있는가"만 보는 것이다."""
    return "".join(unicodedata.normalize("NFC", text).split())


def inspect_opening_completeness(text: str, opening: OpeningDecl) -> tuple[str, ...]:
    """생성된 오프닝이 D-07 다섯 요소를 실제로 담았는지 최소한으로
    대조한다(D-08, 13-03 Task 1 체크포인트에서 사장님이 확정한 ⓐ안).
    위반 사유 튜플을 돌려준다 — **빈 튜플이 통과다.**

    **`inspect_sentence`와 다른 자리에 있는 이유.** 위 갈래들은 전부
    `sentence: str, next_sentence: str | None`을 받는 **한 문장** 판정
    함수다(생각 블록·원문 겹침·캐릭터 이탈·깨진 글자 넷 다). 반면 D-07의
    다섯 요소(내가 누구인지/보이고 들리는 것/왜 중요한지/실마리/열린
    초대)는 **오프닝 전체의 완결성**이라 문장 하나로는 판단할 수 없다 —
    "실마리가 있는가"는 오프닝 전체를 봐야 안다. D-08의 문언("서사가 이미
    거치는 네 갈래 검사에 한 갈래를 더한다")과 이 구현(별도 문서 단위
    함수)의 차이는 13-RESEARCH.md가 A2로 명시적으로 flag했고, 13-03 Task 1
    체크포인트에서 사장님이 확인·승인했다(SUMMARY 기록).

    **이 함수가 실제로 보는 것은 딱 둘뿐이고, 그 이상을 주장하지 않는다:**
    ① `text`가 `strip()` 뒤 비어 있으면 위반. ② `opening.hook_terms` 중
    어느 것도 `text` 안에 없으면 위반 — 대조는 NFC 정규화 + 공백 제거 뒤
    부분 문자열 포함으로 한다. **"왜 중요한지" 등 나머지 요소는 이 검사가
    못 잡는다** — 사장님이 명시적으로 받아들인 한계다(등록 시점 구조
    검사가 다섯 칸이 채워졌음을 보장하고, 이 검사는 생성물이 실마리를
    통째로 빠뜨리는 가장 흔한 실패만 잡는다).

    **길이 검사를 넣지 않는다.** 상한을 두지 않기로 확정됐다(2026-08-24).
    나중에 넣더라도 **코드 포인트**(또는 토큰)로 재고 바이트로 재지
    않는다 — 한글 한 글자가 UTF-8 3바이트라는 사실이 어떤 상한에도 새어
    들어가면 안 된다(SCENE-02 encoding).
    """
    if not text.strip():
        return ("empty",)

    normalized_text = _normalize_for_hook_match(text)
    if not any(
        _normalize_for_hook_match(hook_term) in normalized_text
        for hook_term in opening.hook_terms
    ):
        return ("missing_hook_term",)

    return ()
