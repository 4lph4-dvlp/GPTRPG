"""서사를 문장 단위로 흘려보낸다 — 판정 결과 뒤에 이어 붙는 서술 생성.

`chunk_sentences`는 `NarrationAppended`의 규약(chunk_index가 0부터 1씩 오름,
한 덩어리로 뭉쳐 한 번에 기록되지 않음, RIG-03)을 실제로 만족시키는 자리다.
"""

import queue
import re
import sys
import threading
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from gptrpg.agents.context import NarrationFacts
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import GM_TIMEOUT_S, MAX_ATTEMPTS
from gptrpg.agents.narration_guard import (
    NOTICE_FILTERED,
    NOTICE_GAVE_UP,
    STDERR_EXCERPT_CHARS,
    inspect_sentence,
)
from gptrpg.agents.prompt_assembly import build_gm_prompt
from gptrpg.agents.providers.base import Provider
from gptrpg.rules_core.rulebook import ResourceAxisDecl

_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+|(?<=[.!?])$")

STREAM_STALL_TIMEOUT_S = 90.0
"""스트림이 이만큼 아무 조각도 안 내보내면 포기한다 — `GM_TIMEOUT_S`(D-33)와는
다른 값이다. D-33은 "완결까지는 목표 없음"이라고 명시적으로 응답 속도
목표에서 완결 시간을 뺐다 — 이 상수는 속도 목표가 아니라 순수 안전판이다.
03-04 Task 3 라이브 검증에서 실제로 확인된 문제: `provider.stream()`에 넘긴
`timeout_s=GM_TIMEOUT_S`가 스트림 전체 소요 시간이 아니라 최초 응답까지만
재는 것으로 보였고, 스트림이 멈춘 채 ~22분 동안 터미널이 반응 없이 붙잡혀
있었다(사용자가 "중간에 끊긴 것 같아. 난 아무것도 안 했어"로 보고). 이
값은 정상적으로 느리지만 계속 진행 중인 응답을 죽이지 않으면서, 진짜로
멈춘 스트림은 확실히 끊을 만큼 넉넉하게 잡은 것 — 값 자체는 Claude's
Discretion(03-CONTEXT.md) 영역이다.

**2026-08-26(verify-13-06 결함2) 갱신 — 이 상수가 이제 실제로 발동한다.**
`GM_TIMEOUT_S`가 15초로 남아 있던 동안은 `httpx`(위 03-04 발견의 실체 —
`agents/invoke.GM_TIMEOUT_S` 도크스트링 참조)의 자체 read 타임아웃이
15 < 90이라 **항상 이 앱 계층 감시보다 먼저** 발동했다 — 즉 진짜
스톨(완전 침묵)조차 `StreamStalled`가 아니라 평범한 예외로 여기 도달하기
전에 잡혀, 아래 정상 경로의 재시도 갈래(①)를 타고 있었다. `GM_TIMEOUT_S`가
100초(90보다 크게)로 오른 뒤에야 이 상수가 설계된 역할(완전 침묵 90초 →
재시도하지 않고 깔끔하게 포기)을 실제로 수행한다."""


class StreamStalled(TimeoutError):
    """스톨 워치독이 발동했을 때 던진다 — 다른 실패와 **반드시** 구분해야 한다.

    다른 실패(연결 거절·인증 오류·모델 오류)는 재시도가 의미 있지만, 스톨은
    재시도하면 안 된다. 스톨이 났다는 것은 배경 펌프 스레드가 아직 막힌
    네트워크 읽기 안에 살아 있다는 뜻이고(파이썬에는 그것을 강제로 끊을
    수단이 없다), 그 상태에서 재시도하면 두 번째 펌프 스레드가 또 떠서
    **막힌 스레드가 둘로 늘어난다.** `TimeoutError`를 상속하는 것은 이
    예외를 따로 잡지 않는 기존 호출부(예: `call_with_one_retry`의
    종류-불문 catch)에서 동작이 달라지지 않게 하기 위해서다.
    """


_LEAKED_PUMP_THREADS = 0
"""스톨 때문에 정리하지 못하고 남긴 펌프 스레드의 누적 개수.

**진단용이다.** 이 숫자가 0이 아니면 그 프로세스에는 막힌 소켓을 문 스레드가
그만큼 남아 있다. 1회성 명령줄 실행에서는 프로세스가 곧 끝나 가려지지만,
`gptrpg.web`의 uvicorn 서버는 세션 내내 살아 있는 프로세스라 여기서 새는
것이 실제 누수다 — 03-04 시점에는 서버가 없어서 이 주석이 "미래의 서버
모드"를 가정했지만, Phase 4가 그 서버를 만들었으므로 더 이상 가정이 아니다."""


def _drain_with_stall_timeout(source: Iterable[str], *, stall_timeout_s: float) -> Iterator[str]:
    """`source`를 배경 스레드에서 소비하고, `stall_timeout_s`초 동안 새 조각이
    없으면 `StreamStalled`를 던진다.

    파이썬은 다른 스레드에서 블로킹 중인 네트워크 읽기를 강제로 끊을 방법이
    없다 — 배경 스레드는 데몬이라 프로세스 종료를 막지 않을 뿐, 그 자체가
    영영 멈춰 있을 수도 있다. 그래도 이 함수를 부른 쪽은 `stall_timeout_s`가
    지나면 더 기다리지 않고 예외를 받고 돌아간다 — "네트워크 호출 하나가
    막혀서 화면이 무한정 멈춘다"는 상황을 없애는 것이 목적이다. 이미 나온
    조각을 잃지 않는다 — 조각이 나오는 족족 큐에서 꺼내 그대로 넘긴다.

    **정리하지 못한 스레드를 조용히 남기지 않는다.** 끊고 돌아갈 때
    `_LEAKED_PUMP_THREADS`를 올리고 표준오류에 한 줄 찍는다. 누수 자체를
    없앨 수는 없지만(강제 중단 불가), 그것이 일어났다는 사실이 운영자에게
    보이지 않는 것과 보이는 것은 다르다 — 서버를 몇 시간 띄워 두는 실험에서
    이 줄이 "서버를 한 번 다시 띄울까"를 판단할 유일한 근거다.
    """
    global _LEAKED_PUMP_THREADS

    q: queue.Queue = queue.Queue()
    _done = object()

    def _pump() -> None:
        try:
            for item in source:
                q.put(item)
        except Exception as exc:  # noqa: BLE001 - 배경 스레드의 예외도 그대로 전달한다
            q.put(exc)
        else:
            q.put(_done)

    thread = threading.Thread(target=_pump, daemon=True, name="gptrpg-narration-pump")
    thread.start()

    while True:
        try:
            item = q.get(timeout=stall_timeout_s)
        except queue.Empty as exc:
            _LEAKED_PUMP_THREADS += 1
            print(
                f"경고: 서사 스트림이 {stall_timeout_s}초 동안 멈춰 있어 포기한다 — "
                f"막힌 배경 스레드 하나를 정리하지 못하고 남긴다"
                f"(이 프로세스 누적 {_LEAKED_PUMP_THREADS}개). "
                f"이 숫자가 계속 늘면 서버를 다시 띄워라.",
                file=sys.stderr,
            )
            raise StreamStalled(
                f"스트림이 {stall_timeout_s}초 동안 아무 조각도 내보내지 않았다"
            ) from exc
        if item is _done:
            return
        if isinstance(item, Exception):
            raise item
        yield item


def chunk_sentences(deltas: Iterable[str]) -> Iterator[str]:
    """조각을 문장 끝 구두점(.!?) 경계에서 잘라 하나씩 흘려보낸다.

    문장 끝 판정은 **버퍼 전체**에 대해 하지 델타 하나에 대해 하지 않는다
    — `buf += delta` 뒤에 매번 누적된 전체 버퍼를 다시 매칭하므로, 델타
    경계가 마침표 한가운데를 가르더라도(한 델타가 마침표 직전까지, 다음
    델타가 마침표부터) 문장이 정확히 하나로 합쳐진다. 문장 끝 표시가 하나도
    없는 응답은 스트림이 끝난 뒤 버퍼에 남은 전부가 마지막 조각 하나로
    나온다(0개가 아니다) — 스트림이 문장 중간에서 끊겨도 마찬가지다. 다듬은
    결과가 빈 문자열이면(공백·줄바꿈뿐인 델타만 온 경우 포함) 내보내지
    않는다(`AppendNarration`이 빈 텍스트를 거부한다). 한국어 종결(…다./…요./
    …까?)도 영어 문장과 같은 `.!?` 규칙으로 조각난다 — 언어별 형태소
    분석기를 붙이지 않는다, 구두점 경계로 충분하고 기록에 남는 것은 조각을
    이어 붙인 원문이라 조각 경계가 언어학적으로 완벽할 필요가 없다.
    """
    buf = ""
    for delta in deltas:
        buf += delta
        parts = _SENTENCE_BOUNDARY.split(buf)
        if len(parts) > 1:
            *complete, buf = parts
            for sentence in complete:
                if sentence.strip():
                    yield sentence.strip()
    if buf.strip():
        yield buf.strip()


@dataclass(frozen=True)
class NarrationChunk:
    """`narrate()`가 문장 하나씩 내보내는 반환 단위 — 걸렸는지 여부까지 함께 싣는다(10-01).

    `disposition`은 `narration_guard.GuardVerdict`와 같은 값 집합
    (`"clean"`/`"blocked"`/`"flagged"`)을 그대로 물려받는다. `text`는
    `disposition == "clean"`(또는 `"flagged"`, 10-04부터)이면 문장 원문이고,
    `"blocked"`면 `narration_guard.NOTICE_FILTERED`다 — 걸린 원문은 이 칸에
    담기지 않는다. `narrate()`는 `gptrpg.event_log`·`gptrpg.session_actor`를
    모르므로(`.importlinter` 계약 3) 사건 제출은 이 값을 보고 호출부(웹/CLI)가
    한다 — `disposition != "clean"`이면 호출부가 `RecordSafetyFlag`를 추가로
    제출한다.
    """

    text: str
    disposition: str = "clean"
    reason: str = ""
    matched_len: int = 0
    subject_len: int = 0


def _judge_sentence(
    sentence: str,
    *,
    next_sentence: str | None,
    think_open: bool,
    source_texts: tuple[str, ...],
    written_so_far: tuple[str, ...] = (),
) -> tuple[NarrationChunk, bool]:
    """보류 중이던 `sentence`를 판정해 `NarrationChunk`로 만든다.

    `inspect_sentence`의 다섯 갈래(생각 블록/원문 겹침/자기 반복/캐릭터
    이탈/깨진 글자)가 모두 채워져 있다(10-01·10-02·10-06·verify-13-06
    결함1) — `source_texts`는 `narrate()`가 넘겨주는 영구 고정 블록 텍스트
    하나이고, `written_so_far`는 이번 서사 호출에서 **이미 내보낸 문장들**
    이다(`_consume_narration_stream`이 호출 시점의 값을 그대로 넘긴다 —
    호출마다 자라는 목록이라 매번 다시 읽어야 한다). `disposition ==
    "blocked"`이면 화면에는 `NOTICE_FILTERED`를 대신 싣고, 운영자
    표준오류에 사유·겹친 글자 수·문장 길이·짧은 발췌를 한 줄 찍는다
    (T-10-03 — 사람이 읽을 발췌는 네트워크를 안 타는 표준오류에만).
    `disposition == "flagged"`(캐릭터 이탈, D-03)는 걸러내지 않고 원문
    그대로 내보낸다 — 아래 `else` 갈래가 `clean`과 `flagged` 둘 다 같은
    방식으로 처리한다(`verdict.text`가 이미 두 경우 모두 올바른 값을
    담고 있다).
    """
    verdict = inspect_sentence(
        sentence,
        next_sentence=next_sentence,
        source_texts=source_texts,
        think_open=think_open,
        written_so_far=written_so_far,
    )
    if verdict.disposition == "blocked":
        # `verdict.subject_len > len(sentence)`는 원문 겹침이 문장 경계를 넘어
        # `next_sentence`까지 뻗었다는 뜻이다(10-07, WR-02 — narration_guard의
        # `inspect_sentence`가 이 경우에만 `subject_len`을 이어 붙인 길이로
        # 잡는다). 그때는 발췌도 `sentence`가 아니라 이어 붙인 텍스트에서 떠야
        # 실제로 걸린 글자가 보인다 — 발췌는 운영자 자기 터미널에만 가고
        # 사건 기록에는 안 들어가므로(T-10-03) 다음 문장 내용이 섞여도 안전하다.
        if verdict.subject_len > len(sentence):
            excerpt_source = sentence + (next_sentence or "")
        else:
            excerpt_source = sentence
        excerpt = excerpt_source[:STDERR_EXCERPT_CHARS]
        print(
            f"경고: 서사 한 문장을 걸렀다 — 사유={verdict.reason} "
            f"겹친글자수={verdict.matched_len} 문장길이={verdict.subject_len} "
            f"발췌='{excerpt}'",
            file=sys.stderr,
        )
        chunk = NarrationChunk(
            text=NOTICE_FILTERED,
            disposition=verdict.disposition,
            reason=verdict.reason,
            matched_len=verdict.matched_len,
            subject_len=verdict.subject_len,
        )
    else:
        chunk = NarrationChunk(
            text=verdict.text,
            disposition=verdict.disposition,
            reason=verdict.reason,
            matched_len=verdict.matched_len,
            subject_len=verdict.subject_len,
        )
    return chunk, verdict.think_open


def _consume_narration_stream(
    bounded_deltas: Iterable[str],
    *,
    source_texts: tuple[str, ...],
    written_so_far: list[str],
) -> Iterator[tuple[NarrationChunk, str | None]]:
    """조각 스트림 하나를 1문장 지연 버퍼로 판정해 `(chunk, avoid_text)`
    짝으로 흘려보낸다 — 정상 경로와 재생성 경로가 이 함수 하나를
    공유한다(10-01/10-03, 로직 중복 금지).

    `written_so_far`는 **살아있는 리스트를 그대로 받는다**(고정 튜플이
    아니다) — `narrate()`의 `_drive`가 조각 하나를 소비할 때마다 이
    리스트에 이어 붙이고, 이 함수는 문장을 판정하는 **그 순간의** 값을
    `tuple(written_so_far)`로 읽어야 한다(verify-13-06 결함1, 자기 반복
    검사). 호출 시작 시점에 스냅샷을 떠 고정 튜플로 받으면, 같은 스트림
    안에서 나중에 나온 문장이 그 스트림 **앞부분**과 겹쳐도 못 잡는다 —
    실제 결함이 정확히 그 모양이었다(한 스트림 안에서 뒷부분이 앞부분을
    그대로 되풀이했다).

    `avoid_text`는 `chunk.disposition == "blocked"`일 때만 그 문장의
    **원문**(판정 전 원래 텍스트, D-07이 재생성 프롬프트에 되돌려 보낼
    값)을 담고, 아니면 `None`이다. `chunk.text` 자체는 걸렸으면 이미
    `NOTICE_FILTERED`로 바뀌어 있으므로(`_judge_sentence`) 원문이 이 칸을
    거쳐 나가지 않는다(SAFE-03) — 원문은 오직 `avoid_text`를 통해서만,
    그리고 호출한 쪽이 그 값을 모델에게만 돌려줄 때만 쓰인다(D-07).

    **차단이 일어나면 그 자리에서 스트림 소비를 멈춘다** — `avoid_text`가
    `None`이 아닌 짝을 낸 뒤 곧바로 반환한다(더 이상 `next()`를 부르지
    않는다). 걸린 문장 뒤를 계속 읽어 봤자 어차피 버릴 내용이고, 빨리
    멈춰야 재생성이 그 자리에서 이어 쓸 수 있다.

    예외(스톨·연결 끊김 등)가 나면 보류 중이던 문장을 판정·방출한 뒤 그대로
    다시 던진다 — 03-04/10-01의 "이미 나간 조각은 스톨·실패 뒤에도
    살아남는다" 보장을 여기서 지킨다. 재시도·재생성 여부는 이 함수가 정하지
    않는다 — 그 판단은 전부 이 함수를 부르는 쪽(`narrate()`)의 몫이다.
    """
    held: str | None = None
    think_open = False
    sentences = chunk_sentences(bounded_deltas)
    while True:
        try:
            sentence = next(sentences)
        except StopIteration:
            break
        except Exception:  # noqa: BLE001 - 문장 생성 도중 죽은 스트림, 재시도 판단은 호출한 쪽이 한다
            if held is not None:
                chunk, _think_open = _judge_sentence(
                    held,
                    next_sentence=None,
                    think_open=think_open,
                    source_texts=source_texts,
                    written_so_far=tuple(written_so_far),
                )
                yield chunk, (held if chunk.disposition == "blocked" else None)
                held = None
            raise
        if held is not None:
            chunk, think_open = _judge_sentence(
                held,
                next_sentence=sentence,
                think_open=think_open,
                source_texts=source_texts,
                written_so_far=tuple(written_so_far),
            )
            avoid_text = held if chunk.disposition == "blocked" else None
            held = sentence
            yield chunk, avoid_text
            if avoid_text is not None:
                return
        else:
            held = sentence
    if held is not None:
        chunk, think_open = _judge_sentence(
            held,
            next_sentence=None,
            think_open=think_open,
            source_texts=source_texts,
            written_so_far=tuple(written_so_far),
        )
        yield chunk, (held if chunk.disposition == "blocked" else None)


def _failure_envelope_preserving_tokens(provider: Provider, *, elapsed_ms: int) -> AgentResult:
    """재생성까지 간 턴의 D-08 종료용 실패 껍데기(10-03, Task 2) —
    `provider.last_result()`가 갖고 있는 토큰 값을 살려서 `ok=False`로
    되돌린다.

    재생성까지 간 턴은 실제로 토큰을 썼다 — 그 값을 0으로 지우면 원가
    계산의 입력이 조용히 틀어진다(T-10-10). `last_result()`가 예외를
    던지면(제공자가 `note_result`/`last_result` 규약을 어겼거나, 원래
    스트림이 조각을 하나도 못 얻은 채 소비를 멈춘 경우) 0으로 채운
    껍데기로 대신한다 — `web/routes_actions.py`/`cli/turn_flow.py`의
    `_last_result_or_failure_envelope`와 같은 방어 이유다: 다섯 어댑터
    모두가 이 규약을 지킨다고 가정하지 않는다.
    """
    try:
        prior = provider.last_result()
    except Exception:  # noqa: BLE001 - 제공자가 규약을 어겨도 narrate()는 죽지 않는다
        return AgentResult(
            ok=False,
            value=None,
            elapsed_ms=elapsed_ms,
            prompt_tokens=0,
            completion_tokens=0,
            cached_prompt_tokens=0,
        )
    return AgentResult(
        ok=False,
        value=None,
        elapsed_ms=elapsed_ms,
        prompt_tokens=prior.prompt_tokens,
        completion_tokens=prior.completion_tokens,
        cached_prompt_tokens=prior.cached_prompt_tokens,
    )


def narrate(
    *,
    provider: Provider,
    model: str,
    facts: NarrationFacts,
    rulebook_display_name: str,
    resource_axes: tuple[ResourceAxisDecl, ...] = (),
    stall_timeout_s: float = STREAM_STALL_TIMEOUT_S,
) -> Iterator[NarrationChunk]:
    """서사를 문장 단위로 흘려보낸다. `provider.stream` 호출을 `GM_TIMEOUT_S`로 묶는다.

    `resource_axes`(11-07)는 그대로 `build_gm_prompt`(첫 호출·재생성 호출
    둘 다)로 넘어간다 — 「안 쓴다」로 선언된 축의 처리 지침이 영구 고정
    블록에 실리는 자리다. 기본값 `()`은 그런 축이 없다는 뜻이다.

    **한 문장 지연 버퍼(D-01, 10-01).** 문장을 만드는 즉시 내보내지 않고
    보류 중인 문장을 하나 들고 있다가, 다음 문장이 나오면 그 둘을
    `narration_guard.inspect_sentence`에 함께 넘겨 판정한 뒤 내보내고 새
    문장을 보류로 옮긴다. 스트림이 끝나면(정상 종료든 스톨·실패로 중간에
    끊기든) 그 시점에 들고 있던 보류 문장도 `next_sentence=None`으로 같은
    검사를 거쳐 내보낸다 — "이미 모델에서 나온 문장은 스톨 뒤에도 살아남는다"
    는 03-04의 기존 보장을 지연 버퍼 안에서도 그대로 지킨다. 이 흐름은
    아래 재시도 세 갈래(다음 문단)와는 다른 자리에서 일어난다 — 보류 문장
    판정·방출은 문장을 만드는 안쪽 반복에서 처리하고, 재시도 여부 결정은
    바깥 `except StreamStalled`/`except Exception` 두 갈래가 지금 모양
    그대로 한다.

    **이 함수는 이제 서술만 한다 — 상황 판단은 `situation_judge`가 한다
    (D-06, 09-02).** `TurnContext`를 받을 방법 자체가 없다 — `facts`
    (`NarrationFacts`)에는 위협 시계 상태를 담는 칸이 아예 없으므로,
    이 함수를 거치는 한 진행자 지시문·규칙·시나리오 원문이 서술 호출에
    도달할 경로가 타입 차원에서 막혀 있다(ARCH-02).

    **원문 겹침 대조 소스는 영구 고정 블록 하나뿐이다(D-02②, 10-02).**
    `build_gm_prompt`가 돌려주는 `system`은 `[영구 고정, 세션 고정]` 두
    조각이다 — 이 함수는 `system[0]["text"]`(영구 고정 블록)만 새로 조립
    하지 않고 그대로 `inspect_sentence(..., source_texts=...)`에 넘긴다.
    **세션 고정 블록(`system[1]`)은 의도적으로 뺀다.** 그 블록은
    `_narration_session_block_text`가 만드는 장면 대상·캐릭터 상태이고,
    서사가 당연히 언급해야 할 정당한 이야기 맥락이다 — 이것을 대조 소스에
    넣으면 "부서진 등불이 흔들린다" 같은 정상 서사가 걸린다. 이것은
    10-RESEARCH.md 가정 A1("영구+세션 둘 다")을 좁힌 판단이다 — RESEARCH.md가
    이미 `NarrationFacts` 값(장면 요약·사실 등, `messages` 쪽)을 대조
    소스에서 빼라고 한 것과 정확히 같은 이유가 세션 블록에도 적용된다.

    스트리밍은 「호출 한 번」과 모양이 달라 재시도 의미가 애매하다 — 재시도
    규칙이 세 갈래다: ① 첫 조각 전에 실패했고 스톨이 아니면 재시도한다
    ② 이미 조각이 하나라도 나갔으면 재시도하지 않는다(이미 화면에 찍힌
    문장을 두 번 쓰게 만들지 않는다) ③ **스톨(`StreamStalled`)은 조각
    유무와 무관하게 재시도하지 않는다** — 재시도가 막힌 배경 스레드를 하나
    더 남기고 사람을 90초 더 기다리게 하는 것 외에 하는 일이 없다. 어느
    쪽이든 끝난 뒤 `provider.last_result()`가 성공/실패가 반영된 껍데기를
    돌려준다 — 정상 완주하면 제공자 자신의 `stream()` 구현이 이미 그 값을
    채워 두므로 손대지 않는다.

    재시도까지 실패했거나 조각이 나간 뒤 실패했으면, `provider.note_result()`
    (`Provider` 프로토콜의 정식 메서드)로 실패 껍데기를 남긴다. 03-06 이전에는
    이 자리가 `provider._last_result = ...`로 사적 속성을 직접 갈아 끼웠다 —
    "다섯 어댑터 전부가 `_last_result`라는 이름을 함께 써 왔다"는 내부 관례에
    기댄 범위 안 해법이었다. 그 관례는 실제로는 위임 어댑터(`NimProvider`/
    `OpenRouterProvider`) 둘에서 거짓이었다 — 위임 어댑터는 자기 `_last_result`를
    갖지 않으므로 이 대입은 아무도 읽지 않는 새 속성 하나만 만들고, 진짜
    `last_result()`는 여전히 위임 대상의 `None`을 보고 `RuntimeError`를 던졌다.
    이게 03-UAT.md G-03-3의 실제 크래시 원인이었다(사용자가 NIM을 쓰고
    있었다). `note_result()`는 위임을 통과하도록 만들어진 정식 메서드라
    이 문제가 없다.

    호출한 쪽이 이 반복자를 다 소진한 뒤 `provider.last_result()`로 토큰·
    시간을 가져간다는 것이 `Provider` 프로토콜의 규약이다.

    `provider.stream()`이 돌려주는 원문 조각은 `_drain_with_stall_timeout`을
    거친다 — `timeout_s=GM_TIMEOUT_S`가 스트림 전체 소요 시간이 아니라
    최초 응답까지만 재는 것으로 보이는 제공자가 있어(03-04 Task 3 라이브
    검증), 스트림이 실제로 멈춰도 아무 예외 없이 무한정 블로킹할 수
    있었다. `stall_timeout_s` 동안 새 조각이 하나도 안 오면 이 자리에서
    `TimeoutError`가 나고, 아래 `except Exception` 절이 다른 실패와
    똑같이 처리한다 — 새 분기 코드를 더하지 않는다.

    **재생성(D-06/D-07, 10-03)은 재시도와 다른 개념이고 다른 자리에서
    일어난다 — 아래 2절의 재생성 블록은 반복문이 아니라서 정확히 한 번만
    돈다(10-07, WR-01).** 예전에는 이 규율을 이름으로 암시하는(그러나
    실제로는 아무 데서도 읽히지 않는) 상수 하나가 있었다 — 이 계획에서
    지웠다. 그 이름이 지키던 것은 상수가 아니라 이 블록의 구조(반복문이
    아니라 `if` 하나) 자체였고, 그 구조적 사실을 강제하는 것은 이제
    `tests/test_master_gm.py`의 실제 호출 횟수를 세는 시험이다(재생성을
    나중에 반복문으로 바꾸면 그 시험이 빨간불로 막는다). 위 세 갈래 재시도
    규칙은 "호출이 실패했다"에 대한 대응이고, 재생성은 "호출은 성공했는데
    검사에 걸렸다"에 대한 대응이다 — 정상 경로(`for _attempt in
    range(MAX_ATTEMPTS)`)를 한 글자도 안 바꾼다. 문장이 걸리면(disposition
    `"blocked"`) 안내 조각(`NOTICE_FILTERED`)이 먼저 나가고, 재시도 루프를
    벗어나 `build_gm_prompt`를 `avoid_text`(걸린 문장 원문)·`written_so_far`
    (지금까지 실제로 나간 문장들)로 다시 불러 **독립된 단발 호출**을
    한다 — 이 재생성 호출은 내부 재시도가 없다(딱 한 번 부른다), 스톨이
    나도 재시도하지 않는다. `system`은 첫 호출 때 만든 것을 그대로
    재사용한다(다시 만들지 않는다) — 캐시가 유지되고, 원문 겹침 대조
    소스(`source_texts`)가 두 호출에서 바이트 단위로 같아진다. 재생성
    스트림도 끝까지 성공하면 그걸로 끝나고, 또 걸리거나 예외·스톨이 나면
    안내 조각(`NOTICE_GAVE_UP`)을 마지막으로 내보내고 실패 껍데기를
    남긴다(D-08) — 이 실패 껍데기는 성공한 스트림이 남긴 토큰 값을 살려서
    `ok=False`로 되돌린다(`_failure_envelope_preserving_tokens`, T-10-10).
    재생성 자체가 시도된 적이 없는(내용 차단이 아니라 순수 호출 실패로 끝난)
    턴은 이 안내 조각 없이 기존 실패 껍데기(토큰 0) 그대로다 — D-06/D-07/
    D-08은 "호출은 성공했는데 내용이 나빴다"에만 적용된다. 이 못박음이
    한 턴의 제공자 스트림 호출 상한을 3회(정상 경로 최대 2회 + 재생성
    1회)로 고정한다.
    """
    system, messages = build_gm_prompt(
        rulebook_display_name=rulebook_display_name, facts=facts, resource_axes=resource_axes
    )
    source_texts = (system[0]["text"],)

    start = time.monotonic()
    emitted_any = False
    written_so_far: list[str] = []

    def _drive(msgs: list[dict], *, emit_block_notice: bool = True) -> Iterator[NarrationChunk]:
        """`provider.stream()`을 한 번 불러 소비한다 — 정상 경로·재생성
        경로가 이 내부 함수 하나를 공유한다(로직 중복 금지). `yield from
        _drive(...)`로 부르면 `(avoid_text, reason, matched_len,
        subject_len)`을 돌려받는다(`return`) — `avoid_text`는 걸린 문장의
        원문(D-07이 재생성 프롬프트로 되돌려 보낼 값), 나머지 셋은 D-08
        종료 안내(`NOTICE_GAVE_UP`)가 실을 값이다. 안 걸렸으면
        `(None, "", 0, 0)`이다. 예외(스톨 포함)는 그대로 위로 던진다 —
        재시도·재생성 여부는 이 함수가 정하지 않는다, 그 판단은 전부
        `narrate()` 본문의 몫이다.

        `emit_block_notice=False`(재생성 호출 전용)이면 이 호출 **자신이**
        걸렸을 때 그 자리의 `NOTICE_FILTERED` 조각을 내보내지 않는다 —
        걸린 사실(`avoid_text`·`reason`·...)은 그대로 반환값에 담아 두고,
        화면에 내보내는 안내는 3절의 `NOTICE_GAVE_UP` 하나로 합친다. 이게
        없으면 재생성이 또 걸렸을 때 "걸렀어요" 안내와 "끝까지 못 썼어요"
        안내가 연달아 두 번 나가고, `safety_flagged` 사건도 세 건(첫 차단 +
        재생성 차단 + 종료 안내)으로 늘어난다 — D-08의 "두 건(첫 차단 + 최종
        차단)" 약속을 어긴다. 걸리지 않은 문장(clean/flagged)은 이 값과
        무관하게 항상 그대로 나간다 — 재생성이 실제로 쓴 이야기까지 숨기지
        않는다.
        """
        nonlocal emitted_any
        deltas = provider.stream(
            model=model,
            system=system,
            messages=msgs,
            max_tokens=4096,
            timeout_s=GM_TIMEOUT_S,
        )
        bounded_deltas = _drain_with_stall_timeout(deltas, stall_timeout_s=stall_timeout_s)
        blocked_avoid_text: str | None = None
        blocked_reason = ""
        blocked_matched_len = 0
        blocked_subject_len = 0
        for chunk, avoid_text in _consume_narration_stream(
            bounded_deltas, source_texts=source_texts, written_so_far=written_so_far
        ):
            if avoid_text is not None and not emit_block_notice:
                pass  # 이 호출 자신의 차단 안내는 억누른다(위 도크스트링) — 사실은 아래에서 그대로 기록한다.
            else:
                emitted_any = True
                yield chunk
            if chunk.disposition != "blocked":
                written_so_far.append(chunk.text)
            if avoid_text is not None:
                blocked_avoid_text = avoid_text
                blocked_reason = chunk.reason
                blocked_matched_len = chunk.matched_len
                blocked_subject_len = chunk.subject_len
        return blocked_avoid_text, blocked_reason, blocked_matched_len, blocked_subject_len

    # ---- 1) 정상 경로 — 기존 재시도 규칙 세 갈래를 한 글자도 안 바꾼다 ----
    blocked_avoid_text: str | None = None
    last_reason = ""
    last_matched_len = 0
    last_subject_len = 0

    for _attempt in range(MAX_ATTEMPTS):
        try:
            blocked_avoid_text, last_reason, last_matched_len, last_subject_len = (
                yield from _drive(messages)
            )
        except StreamStalled:
            # **스톨은 재시도하지 않는다.** 스톨이 났다는 것은 이 시도의 배경
            # 펌프 스레드가 아직 막힌 네트워크 읽기 안에 살아 있다는 뜻이고,
            # 파이썬에는 그것을 강제로 끊을 수단이 없다. 여기서 재시도하면
            # 두 번째 펌프 스레드가 또 떠서 막힌 스레드가 둘로 늘어나고,
            # 사람은 90초를 한 번 더(총 180초) 기다린다 — 첫 90초로 이미
            # "이 스트림은 안 온다"가 확인된 상황에서 두 번째 90초가 새로
            # 알려 주는 것은 없다. 조각이 나갔든 안 나갔든 여기서 끝낸다.
            #
            # 03-06까지는 이 갈래가 없어서 스톨도 「첫 조각 전 실패」로
            # 묶여 재시도됐다 — 그것이 서버(오래 사는 프로세스)에서 턴 하나당
            # 막힌 스레드 둘을 남기던 경로였다.
            break
        except Exception:  # noqa: BLE001 - 그 밖의 실패는 종류를 가리지 않는다(D-28)
            if emitted_any:
                # 이미 조각이 나갔다 — 재시도하지 않고 실패 껍데기를 남기고 끝낸다.
                break
            # 첫 조각 전에 실패했다(연결 거절·인증·모델 오류 등) — 다음
            # 시도로 넘어간다. 이 갈래에는 스톨이 오지 않으므로(위에서 먼저
            # 잡힌다) 재시도가 스레드를 겹쳐 남기지 않는다.
            continue
        else:
            if blocked_avoid_text is None:
                # 스트림이 끝까지 성공했고 걸린 문장이 없었다 —
                # provider.last_result()가 이미 올바른 값이다.
                return
            # 걸린 문장이 있었다 — 재시도 루프를 벗어나 재생성 한 번을
            # 시도한다(아래 2절). 이 갈래에서만 break한다 — 다음 시도로
            # 넘어가지 않는다(재생성은 재시도가 아니다).
            break

    # ---- 2) 재생성 — 걸린 문장이 있을 때만, 딱 한 번, 재시도 없이. 이 블록은
    #         반복문이 아니라서(아래 if 하나, for가 아니다) 정확히 한 번만
    #         돈다(10-07, WR-01) — 그 보증은 tests/test_master_gm.py의 호출
    #         횟수 시험이 진다. ----
    if blocked_avoid_text is not None:
        _, regen_messages = build_gm_prompt(
            rulebook_display_name=rulebook_display_name,
            facts=facts,
            resource_axes=resource_axes,
            avoid_text=blocked_avoid_text,
            written_so_far=tuple(written_so_far),
        )
        try:
            second_avoid_text, second_reason, second_matched_len, second_subject_len = (
                yield from _drive(regen_messages, emit_block_notice=False)
            )
        except Exception:  # noqa: BLE001 - 재생성은 재시도하지 않는다(D-08)
            # 재생성 자체가 실패·스톨했다 — 새 판정이 없었으므로 `last_*`는
            # 재생성을 촉발한 첫 차단의 값을 그대로 들고 아래 D-08 종료로
            # 간다("마지막 사유"가 없을 때의 자연스러운 대체값이다).
            pass
        else:
            if second_avoid_text is None:
                # 재생성이 끝까지 성공했다 — 걸린 문장이 더 없었다.
                return
            # 재생성 스트림에서도 걸렸다 — 이 판정이 "마지막 사유"가 된다.
            last_reason = second_reason
            last_matched_len = second_matched_len
            last_subject_len = second_subject_len

        # ---- 3) D-08 종료 — 두 번 다 걸렸거나 재생성 자체가 실패·스톨했다.
        #         안내 조각을 마지막으로 내보내고, 성공한 스트림의 토큰
        #         값을 살린 실패 껍데기를 남긴다(T-10-10). 이 조각이 두
        #         호출부(`_submit_narration_chunk`)에서 `AppendNarration`으로
        #         제출되는 것이 D-08의 "안내한다"다 — 새 화면 요소를 만들지
        #         않는다. ----
        yield NarrationChunk(
            text=NOTICE_GAVE_UP,
            disposition="blocked",
            reason=last_reason,
            matched_len=last_matched_len,
            subject_len=last_subject_len,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        provider.note_result(_failure_envelope_preserving_tokens(provider, elapsed_ms=elapsed_ms))
        return

    # ---- 4) 재생성 없이 그냥 실패했다 — 정상 경로가 MAX_ATTEMPTS를 다 써도
    #         조각 하나 못 얻었거나 조각이 나간 뒤 스톨·실패했다. 이건
    #         내용 차단(D-06/D-07/D-08)이 아니라 순수 호출 실패이므로
    #         재생성·안내 조각 없이 기존 실패 껍데기 그대로다(10-01 이후
    #         상태와 동일 — 이 갈래는 이 계획으로 안 바뀐다). ----
    elapsed_ms = int((time.monotonic() - start) * 1000)
    provider.note_result(
        AgentResult(
            ok=False,
            value=None,
            elapsed_ms=elapsed_ms,
            prompt_tokens=0,
            completion_tokens=0,
            cached_prompt_tokens=0,
        )
    )
