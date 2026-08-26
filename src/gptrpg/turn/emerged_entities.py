"""`scene_entity_judge`가 매 턴 만들어 놓고 버려지던 판단을 사건으로 적립한다
(D-13②, Phase 13-04).

Phase 9(`agents/scene_entity_judge.py`)부터 이 판단은 매 턴 불렸고 이미
계측까지 되고 있었다(`RecordAiCall(agent_role="scene_entity_judge", ...)`).
이 모듈이 채우는 것은 **오직 받는 쪽**이다 — **새 AI 호출은 하나도 안
늘어난다.**

**호출부가 셋이라 하나만 고치면 어긋난다** — 웹의 `confirm()`·`proceed()`,
그리고 명령줄의 판정 턴(`cli/turn_flow.py`). 대상 판단 적립은 판정 턴
**안**이라(오프닝과 달리) 세 곳 다 있어야 한다. 반복을 여기 한 자리로
모아 셋이 그대로 부른다 — `gptrpg.turn`이 `gptrpg.agents`와
`gptrpg.session_actor`를 둘 다 내려다볼 수 있는 유일한 자리이기 때문이다
(`.importlinter` contract:2, `turn/context.py`가 이미 같은 방향으로
import한다). `turn/judgments.py`는 이 모듈이 안 건드린다 — 새 헬퍼는 여기
별도 파일에 둔다.
"""

import sys

from gptrpg.rules_core.entities import Entity
from gptrpg.rules_core.reducer import EmergedEntityFold
from gptrpg.rules_core.scenario import resolve_scene_layers
from gptrpg.session_actor.actor import EntityAlreadyEmerged, RecordEmergedEntity, SessionActor
from gptrpg.turn.judgments import TurnJudgments


async def record_emerged_entities(
    actor: SessionActor,
    judgments: TurnJudgments,
    *,
    cast: tuple[Entity, ...],
    emerged: tuple[EmergedEntityFold, ...],
    caused_by_seq: int | None,
) -> None:
    """`judgments.entity.entities`(이번 턴 새로 등장한 대상 판단)를
    `scene_entity_emerged` 사건으로 적립한다.

    **1층(시나리오 캐스트)과 겹치는 이름은 제출하지 않는다** —
    `scene_entity_judge`가 이미 `existing_names`(=`ctx.scene_entities`의
    `display_name`)로 걸러 주지만, 그 대조는 정규화 없는 완전 일치다.
    제출 앞에 `resolve_scene_layers`로 한 번 더 보고 `layer != "outside"`면
    건너뛴다 — **정규화 규칙이 한 자리에만 있어야 갈라지지 않는다.**

    **`EntityAlreadyEmerged`는 성공으로 읽는다** — 같은 이름이 다시
    나오면 명부에 두 번 안 들어가는 것이 정상 동작이다.

    **그 밖의 제출 실패는 턴을 막지 않는다(D-05/ARCH-05)** — 경고
    한 줄만 남기고 계속한다. 이 함수는 이미 완성된 판정/서사 뒤에
    붙는 **덧붙임**이라, 저장소·액터 결함이 그대로 터져야 하는
    `_submit_narration_chunk`류 핵심 전달 경로와는 자리가 다르다 —
    적립 하나가 실패해도 이미 낸 판정 결과·서사는 살아 있어야 한다.
    """
    for candidate in judgments.entity.entities:
        hit = resolve_scene_layers(candidate.name, cast=cast, emerged=emerged)
        if hit.layer != "outside":
            continue
        try:
            await actor.submit(
                RecordEmergedEntity(
                    name=candidate.name,
                    kind=candidate.kind,
                    caused_by_seq=caused_by_seq,
                )
            )
        except EntityAlreadyEmerged:
            pass  # 이미 같은 이름으로 적립됐다 — 정상 동작이다.
        except Exception as exc:  # noqa: BLE001 - D-05/ARCH-05, 적립 실패가 턴을 막지 않는다
            print(
                f"경고: scene_entity_emerged 적립 실패 — {candidate.name!r}: {exc}",
                file=sys.stderr,
            )
