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

from gptrpg.rules_core.reducer import GameState
from gptrpg.rules_core.rulebook import Rulebook


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
