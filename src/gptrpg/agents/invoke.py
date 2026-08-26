"""호출 한 번을 감싸는 타임아웃·재시도 층 — 03-01 이 뚫어 둔 길의 실패 쪽.

D-27: `action_classifier`(경량 모델) 타임아웃은 5초. `master_gm`(최상급 모델)
타임아웃은 이미 확정되어 있던 15초(D-33, 응답 속도 결정)를 그대로 쓴다 — 이
계획은 그 값을 건드리지 않는다.

**2026-08-17 개정: `CLASSIFIER_TIMEOUT_S`가 5초 → 15초.** D-27을 뒤집은 것이
아니라 그 전제가 사라진 것이다 — D-27은 분류기가 「경량 모델」이라는 전제
위에 5초를 놓았는데, 실제로 한국어 자유 문장을 쓸 만한 품질로 분류하는
모델이 그 층에 없다는 것이 라이브 측정으로 확인됐다. 근거는
`CLASSIFIER_TIMEOUT_S` 도크스트링에 표로 남긴다. `MAX_ATTEMPTS`(D-28)와
`GM_TIMEOUT_S`(D-33)는 안 건드린다.

D-28: 타임아웃이든 모델 오류든 실패하면 정확히 한 번 더 시도하고 끝낸다.
오류 종류별 코드 구분이나 종류별 재시도 규칙은 만들지 않는다 — v1이 갖고
있던 지수 백오프·`MODEL_ERROR`/`VALIDATION_FAILED` 분기는 이번 단계가
명시적으로 잘라낸 것이다.

D-29/D-30이 「모델이 못 골랐다」와 「모델이 응답을 못 했다」를 플레이어
화면에서는 일부러 구분하지 않지만(둘 다 "무브 없음"), 그 둘을 **운영자가**
구분할 방법까지 없애면 안 된다 — 실제 예외 문자열을 표준오류로 찍는다
(03-04 Task 3 라이브 검증에서 겪은 문제: 두 번 다 실패한 호출이 빈 후보와
똑같은 화면으로 보여서, 진짜 "무브 없음"인지 제공자 호출 자체가 죽은
것인지 화면만 봐서는 구분할 수 없었다).
"""

import sys
import time
from collections.abc import Callable

from gptrpg.agents.envelope import AgentResult

CLASSIFIER_TIMEOUT_S = 30.0
"""action_classifier 호출 타임아웃 (D-27을 2026-08-17에 5초→15초로,
verify-13-06 결함2 재현 뒤 2026-08-26에 15초→30초로 올린 값).

**왜 15초까지도 부족해졌나.** 13-05가 분류기 프롬프트에 대상 지목 판단을
더했다(SCENE-04) — 같은 호출이 이제 무브·능력치·소지품에 더해 「누구를·
무엇을 상대로」까지 판단한다. 실측(verify-13-06 세션, seq 106/109 원문
재생, `.gptrpg/agents.json`의 실제 `nvidia/nemotron-3-super-120b-a12b`)
결과, 화면에 보이는 JSON은 60~90자로 짧은데도 **완결까지 8~17초가
걸렸다** — 이 모델이 눈에 보이는 답을 내기 전에 `completion_tokens`
680~1045개를 쓴다(`.content`에는 안 잡히는 내부 추론). 15초 타임아웃은
바로 그 8~17초 구간 안쪽에 있어, 느린 쪽 절반이 **완결 직전에 잘렸다**
— 그 잘린 자리가 결함2다(아래 `MAX_CLASSIFIER_TOKENS`가 같은 실측의
다른 절반을 고친다).

이전 개정(5초→15초)의 근거표는 남긴다:

| 모델 | 응답 시간(구 프롬프트) | 품질(4개 입력) |
|---|---|---|
| nvidia/nemotron-3-super-120b-a12b (현행) | 2.2~9.8s | 4/4 정답 |
| z-ai/glm-5.2 | 1.5~7.2s | 4/4 정답 |
| minimaxai/minimax-m3 | 0.4~11.4s | "판정 불필요"를 빈값으로 냄 |
| nvidia/nemotron-3.5-lightning-30b-a3b | 3.6~13.5s | 영어 사고문 유출로 파싱 실패 |
| nvidia/nemotron-3-nano-30b-a3b | ~7.7s | 프롬프트를 되풀이함 |
| meta/llama-3.3-70b, google/gemma-4-31b, mistralai/mistral-nemotron | 20s+ | 측정 불가 |

값을 30초로 둔 이유는 verify-13-06 실측 최악(17.12초)에 다시 한번 여유를
두면서, D-28의 재시도(정확히 1회)까지 겹쳐도 완전 실패까지 최악 60초로
붙잡아 두기 위해서다. `MAX_ATTEMPTS`(D-28)와 `GM_TIMEOUT_S`(D-33)는
안 건드린다.

**대가.** 진짜로 응답이 없는(제공자 장애) 상황에서 화면이 "무브 없음"을
보여주기까지의 최악 대기가 시도당 30초로 늘어난다(보통은 2~10초)."""

GM_TIMEOUT_S = 100.0
"""master_gm(최상급 모델) 호출 타임아웃 — 2026-08-26 verify-13-06 결함2
재현 뒤 15.0 → 100.0으로 올린 값. D-33("이미 확정된 응답 속도 결정")을
뒤집은 것이 아니라, 그 결정이 이 숫자 하나에 실제로 어떻게 쓰이는지에
대한 잘못된 전제가 무너진 것이다 — 아래 참조.

**이 값이 실제로 재는 것은 "완결까지"가 아니라 "다음 조각까지"다.**
`OpenAIProvider.stream()`이 이 값을 `openai` SDK의 `timeout=`으로 그대로
넘기고, 그 SDK는 내부적으로 `httpx.Timeout(timeout_s)`를 만든다 —
`httpx`의 단일 float 타임아웃은 connect/read/write/pool 넷 다에 같은
값을 걸고, `read`는 "응답 전체 소요 시간"이 아니라 **"다음 바이트가 올
때까지 기다리는 최대 시간"**이다(스트리밍 첫 바이트 포함). 03-04
Task 3 라이브 검증이 이미 이 사실을 적어 뒀다(`master_gm.py`의
`STREAM_STALL_TIMEOUT_S` 도크스트링 참조) — 그런데 그 발견 뒤에도 이
값 자체는 15초로 남아 있었다.

**15초가 실제로 무너뜨린 것.** `narrate()`의 자체 재시도(①: 조각이
하나도 안 나온 채 실패하면 다음 시도로 넘어간다, `MAX_ATTEMPTS=2`)는
있었지만, 두 시도 모두 이 15초 안에 다음 바이트를 못 받으면(제공자가
붐빌 때 첫 응답까지 실제로 몇십 초씩 걸린다 — 아래 실측 참조) 둘 다
빈 채로 실패해 화면에 "이번 턴을 처리하지 못했어요"만 남았다. 재시도
장치는 옳았다 — 그 장치가 실제로 쓸 시간을 15초짜리 창이 주지 않았을
뿐이다.

**실측(verify-13-06, `.gptrpg/agents.json`의 실제 nvidia/nemotron-3-ultra-550b-a55b`,
`nim` 제공자가 붐빌 때):**

| seq | 결과 | 소요 |
|---|---|---|
| 39 (오프닝) | 성공 | 81.691초 |
| 60 (턴1) | 성공 | 34.451초 |
| 70 (턴2, 1차 시도) | 0토큰 실패 | 44.209초 |
| 81 (턴2, 재시도) | 0토큰 실패 | 30.272초 |

성공한 두 호출(81.691초·34.451초)이 이미 옛 15초의 5~2배다 — 이
제공자가 붐빌 때는 **첫 조각이 나오기까지**가 15초를 가볍게 넘는다는
뜻이고, 15초 타임아웃은 성공할 수 있었던 호출을 조각 하나 못 얻은 채
끊어 버렸다. 실패한 두 호출의 소요(44.209초·30.272초)는 `MAX_ATTEMPTS`
두 시도 × 15초(+ 연결 오버헤드)와 거의 일치한다 — 재시도가 정확히
설계대로 두 번 돌았는데도 매번 15초 안에 첫 바이트를 못 받아 결국
0토큰으로 끝났다는 증거다.

**100초로 정한 이유.** `STREAM_STALL_TIMEOUT_S`(90초, `master_gm.py`)보다
크게 잡았다 — 그래야 `httpx`의 자체 read 타임아웃(이 값)이 매번 먼저
끊어 버려서 진짜 스톨 감지 장치가 한 번도 발동하지 못하던 문제도 함께
풀린다(아래 참조). 실측 최대(81.691초)에도 여유(약 20초)를 둔다.

**부수 효과 — `STREAM_STALL_TIMEOUT_S`가 이제 실제로 의미를 갖는다.**
옛 값(15 < 90)에서는 `httpx`의 read 타임아웃이 앱 계층의 스톨 감시
(`_drain_with_stall_timeout`, 90초)보다 항상 먼저 발동했다 — 진짜
"완전히 멈췄다"조차 스톨이 아니라 평범한 예외로 잡혀 재시도 갈래(①)를
탔다는 뜻이다. 이제(100 > 90) 90초 동안 아무 조각도 안 오면 앱 계층의
`StreamStalled`가 먼저 발동해 스톨 전용 갈래(③: 재시도하지 않는다)로
정확히 간다 — `httpx`의 100초는 그 뒤에 남는 순수 안전판이다.

D-28(`MAX_ATTEMPTS`)은 안 건드린다 — 재시도 두 번이라는 규율은 그대로고,
각 시도가 실제로 쓸 수 있는 시간만 늘었다."""

CLOCK_JUDGE_TIMEOUT_S = 5.0
"""clock_judge(시계 판단) 호출 타임아웃(09-01). 닫힌 신호 하나(참/거짓 +
이유 한 줄)만 돌려받는 경량 판단이므로 `action_classifier`와 같은 층의
값을 쓴다 — D-27이 잠근 두 값(`CLASSIFIER_TIMEOUT_S`·`GM_TIMEOUT_S`)은
건드리지 않는다."""

SITUATION_TIMEOUT_S = 15.0
"""situation_judge(상황판단) 호출 타임아웃(09-02). 상황판단은 시나리오
전체·최근 대화·판정 결과를 읽고 사실을 뽑는 깊은 추론이라 `master_gm`과
같은 층의 값이다 — 닫힌 신호 하나만 고르는 `clock_judge`/`action_classifier`
급이 아니다. 별도 상수로 두는 이유는 나중에 이 값만 따로 움직일 수 있어야
하기 때문이고, D-27이 잠근 두 값(`CLASSIFIER_TIMEOUT_S`·`GM_TIMEOUT_S`)은
여전히 건드리지 않는다."""

CREATION_GM_TIMEOUT_S = 60.0
"""creation_gm(캐릭터 만들기 진행자) 네 호출의 타임아웃 — 안내·지목·
되묻기·정리(Phase 12.3).

**예전에는 `SCENE_ENTITY_TIMEOUT_S`(5초)를 빌려 썼다. 그것이 실측과
전혀 안 맞았다**(G-12.3-15). 만들기 GM은 닫힌 목록에서 하나 고르는
경량 판단이 아니라 **가장 큰 모델로 사람에게 할 말을 짓는** 일이다.
2026-08-23 실측(nemotron-3-ultra-550b, 되묻기 4회):
12.3초 · 19.8초 · 29.3초 · 13.9초 — **네 번 다 5초를 넘는다.**

그래서 실제 시험 내내 거의 모든 호출이 시간 초과로 떨어졌고,
`judge_hooks`가 조용히 「되묻지 않음」으로 폴백해(ARCH-05) 화면에는
"진행자가 잠시 말을 잃었지만 계속합니다"만 반복해서 떴다. GM이
되묻기를 꺼린 것이 아니라 **말할 시간을 안 준 것**이다(같은 프롬프트로
제한을 풀고 재면 4회 중 3회가 되물었다).

60초는 최대 실측(29.3초)의 두 배다 — 모델이 붐빌 때의 여유까지 본다.
이 값은 D-27이 잠근 두 값(`CLASSIFIER_TIMEOUT_S`·`GM_TIMEOUT_S`)과
무관한 별도 상수라, 만들기 쪽만 따로 움직일 수 있다."""

SCENE_ENTITY_TIMEOUT_S = 5.0
"""scene_entity_judge(장면 신규 대상 판단) 호출 타임아웃(09-03). 닫힌 목록
(`kind`가 두 값뿐)에서 대상을 몇 개 뽑아 돌려주는 경량 판단이므로
`action_classifier`/`clock_judge`와 같은 층의 값을 쓴다 — D-04가 이
판단은 서술 앞에 붙는 지연이므로 **턴 안에서 끝나야 한다**고 정했고,
그래서 `SITUATION_TIMEOUT_S`(깊은 추론 급)가 아니라 이 값을 쓴다. D-27이
잠근 두 값(`CLASSIFIER_TIMEOUT_S`·`GM_TIMEOUT_S`)은 여전히 건드리지
않는다."""

MAX_ATTEMPTS = 2
"""첫 시도 + 재시도 한 번, 그것으로 끝 (D-28). 한 번의 호출 요청이 제공자를
세 번 이상 때리는 경로가 없다는 것을 이 상수가 못박는다."""


def call_with_one_retry(
    fn: Callable[[], AgentResult], *, timeout_s: float
) -> tuple[AgentResult, str | None]:
    """`fn`을 최대 `MAX_ATTEMPTS`번 부른다 — 첫 시도 + 재시도 한 번, 그것으로 끝.

    `fn`은 이미 `timeout_s`를 제공자에 넘기도록 묶인 무인자 호출이다(제공자가
    스스로 그 시간에 끊는다). 이 함수는 그 사실을 문서화하기 위해서만
    `timeout_s`를 매개변수로 받는다 — 이 함수 자체가 별도로 시계를 재서
    끊지는 않는다.

    벽시계로 시작 시각을 잰다. 성공하면 그 껍데기의 `elapsed_ms`를 지금까지
    잰 총 경과 시간으로 갈아 끼워 돌려준다 — 제공자가 잰 한 시도의 시간이
    아니라, 사람이 실제로 기다린 총 시간이 MEAS-02가 재려는 값이다.

    예외가 나면 종류를 가리지 않고 잡아 다음 시도로 넘어간다 — 오류 종류별
    코드나 종류별 재시도 규칙을 만들지 않는다(D-28이 v1에서 잘라낸 것).

    재시도 사이에 지연을 두지 않는다(즉시 재시도) — 두 타임아웃(5초·15초)이
    이미 사람이 느끼는 지연의 상한이고, 여기에 대기를 더하면 D-33의 응답
    속도 목표를 그만큼 더 밀어낸다.

    두 시도가 모두 실패하면 예외를 밖으로 던지지 않고 실패 껍데기를
    돌려준다 — 성공 칸 거짓, 값 `None`, `elapsed_ms`는 두 시도의 총 경과,
    토큰 두 칸은 0. 마지막 예외는 버리지 않고 두 번째 반환값(문자열)에
    담는다. 이 문자열에는 예외의 문자열 표현만 담기고, 자격 증명이 들어갈
    수 있는 값(요청 헤더·환경 변수)은 담기지 않는다.

    두 시도 모두 실패하면 그 예외 문자열을 표준오류(stderr)에도 한 줄
    찍는다 — `AiInvoked`/`AgentResult`(D-30) 어느 칸에도 실패 사유를 담을
    자리가 없어서, 이 줄이 없으면 운영자가 "모델이 정말 못 골랐다"와
    "호출 자체가 죽었다"를 화면만 보고 구분할 방법이 아예 없다. 사건
    기록에는 안 들어간다 — 화면·기록의 실패 모양은 D-29/D-30이 정한 대로
    그대로다.
    """
    start = time.monotonic()
    last_error_text: str | None = None

    for _attempt in range(MAX_ATTEMPTS):
        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001 - 예외 종류를 가리지 않는다(D-28)
            last_error_text = str(exc)
            continue
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return (
            AgentResult(
                ok=result.ok,
                value=result.value,
                elapsed_ms=elapsed_ms,
                prompt_tokens=result.prompt_tokens,
                completion_tokens=result.completion_tokens,
                # `elapsed_ms` 하나만 갈아 끼우고 나머지 칸은 그대로 옮긴다 —
                # 이 칸을 옮기는 것을 빠뜨리면 재시도 층을 통과한 모든 호출의
                # 캐시 실측값이 조용히 0이 되어, 원가가 캐시 없는 상한선으로만
                # 계산된다(H5 판정의 입력값이다).
                cached_prompt_tokens=result.cached_prompt_tokens,
            ),
            None,
        )

    elapsed_ms = int((time.monotonic() - start) * 1000)
    print(
        f"경고: 제공자 호출이 {MAX_ATTEMPTS}번 모두 실패했다 — {last_error_text}",
        file=sys.stderr,
    )
    failed = AgentResult(
        ok=False,
        value=None,
        elapsed_ms=elapsed_ms,
        prompt_tokens=0,
        completion_tokens=0,
    )
    return failed, last_error_text
