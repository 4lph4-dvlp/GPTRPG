"""M0 실험 준비물 — 캐릭터 넷.

**브람·나리는 D-49에 따라 확정된 캐릭터다**(경험자 2명이 쓸 캐릭터) — 두
캐릭터의 `StatEntry` 값은 이 파일이 처음 지어낸 그대로 유지되며, 이 계획이
바꾸는 것은 `CHARACTER_ARCHETYPES`의 한 줄 소개뿐이다. 수치를 다시 계산하거나
재배치하지 않는다.

**선·호두는 세션 당일 비경험자 2명이 구두 안내로 새로 만드는 자리를 채울
자리표시자다.** 아래 신규 캐릭터 규격(`NEW_CHARACTER_STAT_ARRAY` 등)을
만족하도록 값을 미리 정리해 두었다 — 세션 당일 손으로 교체할 절차와 필드
대응표는 `docs/experiment/character-creation-script.md`에 있다. 편집 후
`uv run pytest tests/test_web_characters.py -q`를 돌려 규격을 벗어나지
않았는지 확인한다.

`PLAYER_CHARACTERS`는 적/NPC와 정확히 같은 `Entity` 그릇을 쓴다(D-20/D-21) —
`rulebooks/dungeonworld_like.py`의 `EXAMPLE_SINGLE_STAT_FOE`, `openquest_creatures.py`가
세운 관례 그대로 `Entity`를 손으로 쓴 상수로 선언한다. `Entity` 칸을 늘리지
않는다 — `ENTITY_FIELD_NAMES` 고정 시험이 즉시 깨지고, 「적/NPC와 플레이어
캐릭터가 같은 그릇에 들어간다」는 성질이 무너진다.
"""

from dataclasses import dataclass

from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rules_core.entities import Entity, StatEntry

NEW_CHARACTER_STAT_NAMES: tuple[str, ...] = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
"""신규 캐릭터가 쓰는 능력치 여섯 칸의 이름과 화면 표시 순서."""

NEW_CHARACTER_STAT_ARRAY: tuple[int, ...] = (2, 1, 1, 0, 0, -1)
"""세션 당일 새로 만드는 사람이 여섯 자리에 배치할 값 묶음(정렬하면
`[-1, 0, 0, 1, 1, 2]`). 어느 값을 어느 능력치 자리에 놓을지는 참가자가
직접 고른다 — 이 튜플의 선언 순서가 `NEW_CHARACTER_STAT_NAMES`의 각 자리에
그대로 고정 배치되는 것은 아니다."""

NEW_CHARACTER_HP_BASE = 16
NEW_CHARACTER_HP_PER_CON = 2
"""체력 = `NEW_CHARACTER_HP_BASE + CON * NEW_CHARACTER_HP_PER_CON`이고
`current`와 `max`를 같은 값으로 둔다. `depleted_effect_ref`는
`"dungeonworld_like.hp_depleted"`. design-plan.md §6.1의 ⑦「자동 계산」에
해당하는 유일한 항목이다.

**적용 범위 — D-49:** 이 규격은 세션 당일 구두 안내로 새로 만드는 두
캐릭터(선·호두 자리)에만 적용된다. 이미 확정된 브람·나리에는 적용되지
않는다 — D-49가 경험자 2명이 쓸 두 캐릭터는 기존 수치를 그대로 유지하기로
확정했기 때문이다."""

PLAYER_CHARACTERS: dict[str, Entity] = {
    "bram": Entity(
        entity_id="player.bram",
        display_name="브람",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(
            StatEntry(
                name="체력",
                current=20,
                max=20,
                depleted_effect_ref="dungeonworld_like.hp_depleted",
            ),
            StatEntry(name="STR", current=2),
            StatEntry(name="DEX", current=0),
            StatEntry(name="CON", current=1),
            StatEntry(name="INT", current=-1),
            StatEntry(name="WIS", current=0),
            StatEntry(name="CHA", current=0),
            # bram만 갖는 일곱 번째 상태값 — 넷 중 상태값 개수가 서로 다른
            # 쌍을 최소 하나 만들어, 개수가 달라도 같은 화면으로 그려짐을
            # 시험이 확인할 수 있게 한다.
            StatEntry(name="방어구", current=2),
        ),
    ),
    "nari": Entity(
        entity_id="player.nari",
        display_name="나리",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(
            StatEntry(
                name="체력",
                current=16,
                max=16,
                depleted_effect_ref="dungeonworld_like.hp_depleted",
            ),
            StatEntry(name="STR", current=0),
            StatEntry(name="DEX", current=2),
            StatEntry(name="CON", current=0),
            StatEntry(name="INT", current=1),
            StatEntry(name="WIS", current=1),
            StatEntry(name="CHA", current=-1),
        ),
    ),
    "seon": Entity(
        entity_id="player.seon",
        display_name="선",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(
            # 신규 캐릭터 규격에 맞춘 자리표시자 — 세션 당일 통째로 교체된다(D-49).
            StatEntry(
                name="체력",
                current=16,
                max=16,
                depleted_effect_ref="dungeonworld_like.hp_depleted",
            ),
            StatEntry(name="STR", current=2),
            StatEntry(name="DEX", current=1),
            StatEntry(name="CON", current=0),
            StatEntry(name="INT", current=1),
            StatEntry(name="WIS", current=0),
            StatEntry(name="CHA", current=-1),
        ),
    ),
    "hodu": Entity(
        entity_id="player.hodu",
        display_name="호두",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(
            # 신규 캐릭터 규격에 맞춘 자리표시자 — 세션 당일 통째로 교체된다(D-49).
            StatEntry(
                name="체력",
                current=18,
                max=18,
                depleted_effect_ref="dungeonworld_like.hp_depleted",
            ),
            StatEntry(name="STR", current=0),
            StatEntry(name="DEX", current=1),
            StatEntry(name="CON", current=1),
            StatEntry(name="INT", current=-1),
            StatEntry(name="WIS", current=2),
            StatEntry(name="CHA", current=0),
        ),
    ),
}
"""플레이어 캐릭터 넷 — 선언 순서가 입장 화면의 줄 순서다(`list_characters()`가
이 순서를 그대로 유지해야 새로고침마다 순서가 흔들리지 않는다)."""

CHARACTER_ARCHETYPES: dict[str, str] = {
    "bram": "우물 마을 순찰대에 뒤늦게 합류한 떠돌이 검객 — 몸을 던져 막아서는 데 주저함이 없다",
    "nari": "소리 없이 다가가 자물쇠와 함정을 다루는 밤그림자 — 활을 메고 우물 마을에 흘러들었다",
    "seon": "옛 노래를 기억하는 학자",
    "hodu": "말로 문을 여는 떠돌이",
}
"""캐릭터 한 줄 소개 — 입장 화면 전용 화면 사정일 뿐이라 `Entity`에 넣지
않는다. D-20이 확정한 네 칸을 늘리면 룰북 고유 개념(한 줄 소개는 룰북이
정하는 것이 아니라 이 실험 화면이 붙인 캡션일 뿐)이 플랫폼 그릇으로 새어
들어간다. `Entity`와 분리된 이 딕셔너리에 남겨 두는 것이 층 경계를 지키는
방법이다(PROJECT.md "세 개의 층")."""


@dataclass(frozen=True)
class CharacterSummary:
    """입장 화면 한 줄 분량 — 시트 전체가 아니라 목록에 보일 요약만 담는다."""

    character_id: str
    display_name: str
    archetype: str


def list_characters() -> tuple[CharacterSummary, ...]:
    """`PLAYER_CHARACTERS` 선언 순서 그대로 요약 튜플을 돌려준다.

    파이썬 3.7+ 의 딕셔너리는 삽입 순서를 보존하므로 위 선언 순서가 그대로
    이 함수의 순서가 된다 — 정렬 기준을 따로 만들지 않는다.
    """
    return tuple(
        CharacterSummary(
            character_id=character_id,
            display_name=entity.display_name,
            archetype=CHARACTER_ARCHETYPES[character_id],
        )
        for character_id, entity in PLAYER_CHARACTERS.items()
    )


def get_character(character_id: str) -> Entity | None:
    """알려진 캐릭터 식별자면 `Entity`를, 아니면 `None`을 돌려준다."""
    return PLAYER_CHARACTERS.get(character_id)
