"""캐릭터 만들기 진행 상태 계산 — `routes_creation.py`와 `routes_events.py`가
**같은 함수를** 부르는 자리다(D-04, Phase 12.3).

이 모듈이 따로 있는 이유는 `routes_events.py`가 `routes_creation.py`의
비공개 도우미(`_unfinished_candidates`/`_required_steps_filled`)를 찔러 쓰지
않게 하려는 것이다 — 판단이 두 곳에 생기면(한 라우터가 계산을 복제하면)
언젠가 어긋난다(Phase 12.2가 방금 고친 사고). 두 라우터가 같은 함수를
부르면 그 어긋남이 구조적으로 불가능하다.

**`session_actor/actor.py`의 `_unfinished_creation_candidates`가 여전히
따로 있는 이유:** 층 계약(`.importlinter` contract:2, `gptrpg.web`이
`gptrpg.session_actor`보다 위층)상 `session_actor`가 `gptrpg.web`을 import할
수 없다 — 액터도 같은 계산이 필요하므로(동의·명단 잠금 전제 검사) 이 모듈을
가져다 쓰지 못하고 같은 계산을 자기 층에서 다시 한다. 세 번째 사본을 만들지
않는다는 규율은 지키되, 층 경계를 넘는 import는 만들지 않는다.

`_transcript_for`는 이 모듈로 옮기지 않는다 — GM 프롬프트 조립 전용이고
폴링 화면 상태와 무관하다.
"""

import time

from gptrpg.rules_core.reducer import GameState
from gptrpg.rules_core.rulebook import Rulebook

HOST_IDLE_S = 30.0
"""방장이 유휴로 판정되는 문턱(초, D-11). 화면이 15초마다 자기를 알리는
재실 신호(`POST /creation/host`)를 보내는 것을 전제로 잡은 값이다 —
두 배를 두는 이유는 한 번의 폴링 지연이나 네트워크 요동만으로 방장을
잃지 않으려면 최소 두 번은 놓쳐야 하기 때문이다."""

_browser_last_seen: dict[tuple[str, str], float] = {}
"""(session_id, browser_id) -> 마지막으로 재실 신호를 받은 시각
(`time.monotonic()` 기준, 벽시계가 아니다 — 이 저장소가 경과 시간을 잴 때
이미 쓰는 관례, `agents/invoke.py` 등).

**이 표가 사건이 아니라 프로세스 메모리인 이유:** 「누가 지금 창을 열어
두고 있나」는 기록할 사실이 아니라 지금 이 순간의 관측값이다 — 사건으로
남기면 15초마다 참가자 수만큼 사건이 쌓인다. 판단은 여전히 서버 한
자리에서만 나지만(D-04와 같은 규율), 그 판단의 재료(재실 여부)까지 전부
사건일 필요는 없다.

**한계 — 단일 프로세스 전제다.** 서버를 재시작하면 이 표가 빈다. 그
직후 `browser_last_seen()`이 `None`을 돌려주면 호출부(`routes_creation.py`)가
그것을 「방금 봤다」로 취급해야 한다 — 그래야 재시작 직후 멀쩡한 방장이
유휴로 오판돼 승계당하지 않는다(T-12.3-13). 배경에서 혼자 도는 정리
장치는 두지 않는다(D-12 경계) — 이 표는 요청이 올 때만 늘고, 세션이
끝나도 스스로 줄지 않는다(T-12.3-12, DoS 위험 accept — 이 서버가 링크를
아는 소수만 쓰는 단일 프로세스 개발 서버라는 전제 위에서만 유효한
판단이다. 배포를 진지하게 다루는 단계가 오면 상한을 다시 볼 것)."""


def mark_browser_seen(session_id: str, browser_id: str) -> None:
    """브라우저가 지금 살아 있다고 표시한다 — `POST /creation/host` 호출
    자체가 곧 재실 신호다."""
    _browser_last_seen[(session_id, browser_id)] = time.monotonic()


def browser_last_seen(session_id: str, browser_id: str) -> float | None:
    """마지막으로 재실 신호를 받은 시각(`time.monotonic()` 기준) — 이
    프로세스에서 한 번도 못 봤으면(재시작 직후 포함) `None`이다."""
    return _browser_last_seen.get((session_id, browser_id))


def alive_browsers(session_id: str) -> tuple[str, ...]:
    """이 세션에서 `HOST_IDLE_S` 안에 재실 신호를 보낸 브라우저들 —
    처음 본 순서를 보존한다(딕셔너리 삽입 순서)."""
    now = time.monotonic()
    return tuple(
        browser_id
        for (sid, browser_id), seen_at in _browser_last_seen.items()
        if sid == session_id and now - seen_at <= HOST_IDLE_S
    )


def unfinished_candidates(state: GameState) -> tuple[str, ...]:
    """진행 중인데 아직 완성되지 않은 사람의 닫힌 목록.

    **대화의 상태 기계는 코드가 돌린다**(12.1-03-PLAN.md § 결정한 열린
    지점 ①) — 에이전트에게 묻지 않는다. `state.creation_step_values`의
    키에서 `character_id`를 뽑고 `state.created_characters`에 아직 없는
    사람만 남긴다. 순서는 그 사람이 만들기 항목을 처음 제출한 순서를
    보존한다(딕셔너리 삽입 순서 = 사건 순번 오름차순).

    아직 항목을 하나도 제출하지 않은 사람은 이 목록에 못 들어간다 —
    플랫폼이 아는 유일한 참가자 식별 통로가 `CompleteCreationStep`의
    `character_id`이기 때문이다(방을 여는 사람이 정한 인원수와 실제
    참가자 식별자는 다른 정보다).
    """
    seen: list[str] = []
    for character_id, _step_id in state.creation_step_values:
        if character_id not in state.created_characters and character_id not in seen:
            seen.append(character_id)
    return tuple(seen)


def required_steps_filled(state: GameState, rulebook: Rulebook, character_id: str) -> bool:
    """룰북 최소선(`required=True`)이 채워졌는지 코드가 직접 본다(D-05
    아래층) — GM 재량(위층, `judge_hooks`)과는 다른 층의 판단이다."""
    for step in rulebook.creation_steps:
        if step.required and (character_id, step.step_id) not in state.creation_step_values:
            return False
    return True
