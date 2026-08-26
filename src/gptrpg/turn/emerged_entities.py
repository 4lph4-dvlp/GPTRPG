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

from gptrpg.agents.context import TARGET_ABSENT_FACT
from gptrpg.rules_core.entities import Entity
from gptrpg.rules_core.reducer import EmergedEntityFold
from gptrpg.rules_core.scenario import ScenarioDecl, resolve_scene_layers
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


async def apply_declared_target(
    actor: SessionActor,
    *,
    scenario: ScenarioDecl,
    declare_seq: int,
    caused_by_seq: int | None,
) -> tuple[str, ...]:
    """이 `declare_seq`가 지목한 대상이 시나리오의 열림/닫힘 선언대로
    갈리게 한다(Phase 13-05, SCENE-04, D-13①②, D-14/D-15/D-16).

    **웹의 `confirm()`/`proceed()`, 명령줄의 판정 턴 — 세 자리가 공유하는
    단일 자리다** — `record_emerged_entities`(위)와 같은 이유로 이 모듈에
    둔다: `gptrpg.turn`이 `gptrpg.agents`와 `gptrpg.session_actor`를 둘 다
    내려다볼 수 있는 유일한 자리이기 때문이다(`.importlinter` contract:2).

    `actor.state.declare_targets`에서 이 `declare_seq`의 지목을 **다시
    읽는다** — 클라이언트가 보낸 값을 안 쓴다(ASVS V5,
    `VerifyProceedEligibility`가 세운 규율과 같은 이유). `declare_seq`가
    표에 없으면(판 14 미만 기록, 또는 대상 검사를 안 쓰는 시나리오)
    `NO_TARGET_FOLD`(「대상 없음」)로 읽는다.

    - `presence in ("none", "known")` → 빈 튜플. `known`은 이미 확정
      목록에 있는 것이므로 적립할 것이 없다(SCENE-04 adjacency) — 확정
      목록에 같은 것이 두 번 안 들어간다. `none`은 지목이 없었다는 뜻이다
      (SCENE-04 empty).
    - `presence == "unknown"` → 시나리오의 열림/닫힘을 본다. `kind ==
      "person"`이면 `improv_people`, `kind == "thing"`이면 `improv_things`.
      **`kind`가 `None`이면 두 값이 모두 참일 때만 허용한다** — 종류를
      모르는 채로 여는 것은 저자가 닫아 둔 축을 뚫는 일이 될 수 있으므로
      닫히는 쪽으로 떨어진다(결정론이므로 「대충 person으로 본다」 같은
      임의 선택을 하지 않는다, T-13-24).
      - **금지** → 사건을 안 남기고 `(TARGET_ABSENT_FACT(name),)`를
        돌려준다. 호출부가 이 값을 `build_narration_facts(...,
        extra_facts=...)`에 그대로 넘긴다.
      - **허용, `kind`가 있음** → `RecordEmergedEntity(name=..., kind=...)`를
        제출한다(`EntityAlreadyEmerged`는 성공으로 읽는다, D-05/ARCH-05).
        사람에게 되묻지 않는다(D-14). 빈 튜플을 돌려준다 — 사건 자체가
        다음 턴의 `scene_entities`에 이 이름을 올린다(13-04).
      - **허용, `kind`가 `None`** → 아무 것도 하지 않는다(빈 튜플). 두
        축이 모두 열려 있어 「없다」로 처리해선 안 되지만,
        `RecordEmergedEntity`는 구조적으로 `kind`가 `person`/`thing`
        중 하나여야 하므로(`EmergedEntityFold`, `_VALID_EMERGED_ENTITY_KINDS`)
        종류를 모르는 대상을 2층에 임의로 지어내 넣지 않는다 — 서사는
        자유롭게 언급할 수 있지만 명부에는 안 남는다.
    """
    target = actor.state.declare_targets.get(declare_seq)
    if target is None or target.presence in ("none", "known"):
        return ()

    if target.kind == "person":
        allowed = bool(scenario.improv_people)
    elif target.kind == "thing":
        allowed = bool(scenario.improv_things)
    else:
        allowed = bool(scenario.improv_people) and bool(scenario.improv_things)

    if not allowed:
        return (TARGET_ABSENT_FACT(target.name),)

    if target.kind is None:
        # 두 축이 모두 열려 있어 허용되지만, 종류를 몰라 2층에 넣을 수
        # 없다(위 도크스트링 참조) — 거절 사실도 안 남긴다(허용이므로
        # 「없다」가 아니다).
        return ()

    try:
        await actor.submit(
            RecordEmergedEntity(name=target.name, kind=target.kind, caused_by_seq=caused_by_seq)
        )
    except EntityAlreadyEmerged:
        pass  # 이미 확정 목록에 있다 — 정상 동작이다.
    except Exception as exc:  # noqa: BLE001 - D-05/ARCH-05, 적립 실패가 턴을 막지 않는다
        print(
            f"경고: 지목된 대상의 scene_entity_emerged 적립 실패 — {target.name!r}: {exc}",
            file=sys.stderr,
        )
    return ()
