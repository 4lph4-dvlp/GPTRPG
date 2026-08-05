"""AI 호출 한 번의 결과를 담는 메모리 안 임시 그릇.

D-30이 정한 최소 규격 그대로다: 성공/실패, 값, 걸린 시간, 토큰 수.
이 그릇은 기록(event_log)에 직접 들어가지 않는다 — 호출한 쪽이 이 값을
`session_actor.RecordAiCall`의 같은 이름 칸으로 옮겨 붙인다. 유일한 이름
변환은 `elapsed_ms` -> `latency_ms`다(`RecordAiCall`이 그 이름을 쓴다) —
그 사실을 여기 적어 둔다.

pydantic 모델로 만들지 않는다: 이 그릇은 사건 기록에 직접 들어가지 않는
메모리 안 임시 그릇이다. v1의 `error_code`·`fallback_suggestion`은 만들지
않는다(D-30이 명시적으로 잘라냈다).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentResult:
    """제공자 호출 한 번의 결과 — 성공/실패 + 값 + 걸린 시간 + 토큰 수.

    `cached_prompt_tokens`는 `prompt_tokens`의 **부분집합**이다(합계가 아니다) —
    제공자가 보고한 입력 토큰 중 캐시에서 읽어 온 몫이다. 원가 계산에서
    캐시 읽기 단가가 신규 입력 단가보다 훨씬 싸므로, 이 칸이 없으면
    「캐싱 유무가 원가를 3.7배 가른다」(D19)는 전제를 실측으로 검증할 수
    없다 — 그것이 이 칸이 존재하는 유일한 이유다. 캐시 정보를 주지 않는
    제공자·표면에서는 0으로 남고, 그때의 실측값은 「캐시 적중 0% 가정」의
    원가 상한선으로 읽어야 한다.
    """

    ok: bool
    value: object | None
    elapsed_ms: int
    prompt_tokens: int
    completion_tokens: int
    cached_prompt_tokens: int = 0
