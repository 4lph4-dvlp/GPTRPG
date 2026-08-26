"""장면 신규 대상 판단 — 이번 판정 결과가 장면에 새 인물·사물을 등장시키는가(D-03 (a)).

**DP-09를 못박는다: 이 판단의 결과는 서술에 넘길 사실로만 쓰인다.** 모델이
돌려준 이름을 사건으로 기록하거나 `Entity` 목록에 밀어 넣는 경로를 이
모듈은 만들지 않는다 — Phase 13이 이 결과를 받아 사건으로 적립한다
(D-13②, `turn.emerged_entities`) — 그 경로는 여전히 이 모듈 밖에 있다.
이 판단이 하는 일은 `NarrationFacts.new_entities`를 채워 서술이 그
인물·사물을 자연스럽게 언급할 수 있게 하는 것까지다.

`clock_judge.py`/`situation_judge.py`와 같은 모양이다: 닫힌 결과
dataclass + `call_with_one_retry` + 강건 JSON 파싱, 실패하면(두 시도 모두
실패, 또는 응답이 깨졌으면) 예외를 던지지 않고 빈 판단으로 떨어진다
(D-05/ARCH-05).

**`UnknownMove`에 해당하는 예외를 만들지 않는 이유:** 무브 이름은 룰북이
정한 닫힌 목록과 대조할 수 있지만, 여기의 `name`은 모델이 그때그때 짓는
자유 문자열이다 — 대조할 목록 자체가 없다. `kind`만 닫힌 두 값과 대조하고,
`name`이 없거나 `kind`가 목록 밖이면 그 원소만 조용히 건너뛴다(원소 하나
때문에 턴 전체가 죽지 않는다).
"""

from dataclasses import dataclass

from gptrpg.agents.context import EntityJudgeContext, NEW_ENTITY_LIMIT
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.invoke import SCENE_ENTITY_TIMEOUT_S, call_with_one_retry
from gptrpg.agents.json_parsing import try_parse_json_array
from gptrpg.agents.prompt_assembly import build_scene_entity_prompt
from gptrpg.agents.providers.base import Provider

_KNOWN_KINDS = frozenset({"person", "thing"})


@dataclass(frozen=True)
class NewEntity:
    """장면 신규 대상 판단이 돌려주는 대상 하나 — 표시 이름과 종류."""

    name: str
    kind: str


@dataclass(frozen=True)
class EntityJudgment:
    """장면 신규 대상 판단 결과 — 대상 목록 + 그 호출의 `AgentResult`."""

    entities: tuple[NewEntity, ...]
    ai: AgentResult


def _parse_entities(raw_text: str) -> tuple[NewEntity, ...]:
    """모델이 돌려준 텍스트를 `NewEntity` 튜플로 바꾼다.

    원소가 dict가 아니거나 `name`이 없거나 `kind`가 닫힌 두 값 밖이면 그
    원소만 건너뛴다 — 형식이 깨진 원소 하나 때문에 턴 전체가 죽지 않는다
    (`action_classifier._parse_candidates`의 규율과 같다).
    """
    parsed = try_parse_json_array(raw_text)
    entities: list[NewEntity] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        kind = item.get("kind")
        if not isinstance(name, str) or not name.strip():
            continue
        if kind not in _KNOWN_KINDS:
            continue
        entities.append(NewEntity(name=name, kind=kind))
    return tuple(entities)


def judge_new_entity(
    *,
    provider: Provider,
    model: str,
    ctx: EntityJudgeContext,
    rulebook_display_name: str,
) -> EntityJudgment:
    """제공자를 불러 이번 턴 장면에 새로 등장한 대상을 얻는다.

    `call_with_one_retry`(D-27/D-28)를 거친다. 재시도까지 실패하면 예외를
    던지지 않고 `entities=()`인 빈 판단을 돌려준다(D-05).

    이미 장면에 있는 대상(`ctx.scene_entities`의 `display_name`)과 이름이
    겹치는 원소는 결과에서 뺀다 — "새" 대상만 남긴다. 그 뒤 앞에서부터
    `NEW_ENTITY_LIMIT`개로 자른다 — 자르는 책임은 여기에 있다
    (`NarrationFacts`는 넘치면 예외를 던지는 마지막 방어선이지, 정상적으로
    자르는 자리가 아니다).

    `max_tokens=1024`, `timeout_s=SCENE_ENTITY_TIMEOUT_S`.
    """
    system, messages = build_scene_entity_prompt(
        rulebook_display_name=rulebook_display_name,
        ctx=ctx,
    )

    def _call_once() -> AgentResult:
        return provider.complete(
            model=model,
            system=system,
            messages=messages,
            max_tokens=1024,
            timeout_s=SCENE_ENTITY_TIMEOUT_S,
        )

    result, _last_error_text = call_with_one_retry(_call_once, timeout_s=SCENE_ENTITY_TIMEOUT_S)
    if not result.ok:
        return EntityJudgment(entities=(), ai=result)

    parsed_entities = _parse_entities(str(result.value))

    existing_names = frozenset(entity.display_name for entity in ctx.scene_entities)
    new_entities = tuple(
        entity for entity in parsed_entities if entity.name not in existing_names
    )[:NEW_ENTITY_LIMIT]

    return EntityJudgment(entities=new_entities, ai=result)
