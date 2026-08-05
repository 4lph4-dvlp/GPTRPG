"""호출 한 번을 감싸는 타임아웃·재시도 층 — 03-01 이 뚫어 둔 길의 실패 쪽.

D-27: `action_classifier`(경량 모델) 타임아웃은 5초. `master_gm`(최상급 모델)
타임아웃은 이미 확정되어 있던 15초(D-33, 응답 속도 결정)를 그대로 쓴다 — 이
계획은 그 값을 건드리지 않는다.

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

CLASSIFIER_TIMEOUT_S = 5.0
"""action_classifier(경량 모델) 호출 타임아웃 (D-27, 이 값 자체는 이번 단계가
건드리지 않는 잠긴 결정이다).

운영자 주의(IN-01 리뷰 발견): 이 타이머는 `action_classifier.py`가 문서화한
추론형 모델(NIM의 Nemotron 계열 등, `<think>...</think>` 출력)에게는 빠듯할
수 있다 — 애매한 문장일수록(정확히 2~3개 후보가 필요한 그 순간) 모델이 더
오래 "생각"한다. NIM/Nemotron을 classifier로 쓰는 운영자는 두 번의 시도
(D-28) 모두 이 타임아웃에 걸리는 일이 애매한 입력에서 반복적으로 일어날 수
있고, 화면에는 진짜 "무브 없음"(모델이 후보를 못 찾음)과 똑같이 보인다 —
호출 자체가 타임아웃으로 죽은 것과 구분이 안 된다. 코드 결함이 아니라(값은
잠긴 결정이다) 신뢰도 있는 티어 선택 UX에 실제로 영향을 주는 운영 특성이라
여기 남긴다."""

GM_TIMEOUT_S = 15.0
"""master_gm(최상급 모델) 호출 타임아웃 — 이미 확정된 응답 속도 결정(D-33)을
그대로 쓴다. D-27이 이 값 자체는 건드리지 않는다고 명시했다."""

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
