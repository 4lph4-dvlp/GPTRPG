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

from gptrpg.agents.context import TurnContext
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import GM_TIMEOUT_S, MAX_ATTEMPTS
from gptrpg.agents.prompt_assembly import build_gm_prompt
from gptrpg.agents.providers.base import Provider

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
Discretion(03-CONTEXT.md) 영역이다."""


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


def narrate(
    *,
    provider: Provider,
    model: str,
    ctx: TurnContext,
    check_summary: str,
    rulebook_display_name: str,
    stall_timeout_s: float = STREAM_STALL_TIMEOUT_S,
) -> Iterator[str]:
    """서사를 문장 단위로 흘려보낸다. `provider.stream` 호출을 `GM_TIMEOUT_S`로 묶는다.

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
    """
    system, messages = build_gm_prompt(
        rulebook_display_name=rulebook_display_name, ctx=ctx, check_summary=check_summary
    )

    start = time.monotonic()
    emitted_any = False

    for _attempt in range(MAX_ATTEMPTS):
        try:
            deltas = provider.stream(
                model=model,
                system=system,
                messages=messages,
                max_tokens=4096,
                timeout_s=GM_TIMEOUT_S,
            )
            bounded_deltas = _drain_with_stall_timeout(deltas, stall_timeout_s=stall_timeout_s)
            for sentence in chunk_sentences(bounded_deltas):
                emitted_any = True
                yield sentence
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
            # 스트림이 끝까지 성공했다 — provider.last_result()가 이미 올바른 값이다.
            return

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
