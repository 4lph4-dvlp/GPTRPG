"""시험 재료 — 브람·나리·선·호두 넷(옛 `web/characters_data.py`).

**이 파일은 제품 코드가 아니다.** CHAR-02(「완성된 캐릭터를 즉시 집어드는
경로를 만들지 않는다」)와 D22의 「30초 경로 폐기」가 이 상수 넷을 제품에서
지우라고 요구했다 — 그리고 지금까지 제품 코드에 있던 유일한 캐릭터 경로가
정확히 그 폐기된 경로였다(완성품 넷 중 하나를 눌러 집어드는 것이 전부였다).
예시로 보여만 주는 것도 「그걸 달라」는 요구를 만든다는 것이 D-12의 판단이다
(`.planning/phases/12.1-character-creation/12.1-CONTEXT.md` D-12).

**`src/` 아래로 되돌리면 CHAR-02가 다시 깨진다.** 이 파일을 제품 코드가
import하는 순간, 「완성된 캐릭터 목록을 돌려주는 함수」가 다시 생기고
D-12가 폐기한 경로가 부활한다. 이 파일은 `tests/` 아래에서 시험 재료로만
존재해야 한다 — `test_` 접두어가 없어 pytest가 시험 파일로 수집하지도
않는다(`tests/fixtures/`의 기존 관례, README.md·`session1_events.jsonl`과
같은 성격).

**D-49의 값 보존 규율이 여기서도 그대로 산다.** 브람·나리는 D-49에 따라
확정된 캐릭터였다(경험자 2명이 쓸 캐릭터) — 두 캐릭터의 `StatEntry` 값은
이 파일로 옮겨진 뒤에도 원래 값 그대로 유지된다. 수치를 다시 계산하거나
재배치하지 않는다.

**`Entity` 칸을 늘리지 않는다.** `PLAYER_CHARACTERS`는 적/NPC와 정확히
같은 `Entity` 그릇을 쓴다(D-20/D-21) — `Entity` 칸을 늘리면
`ENTITY_FIELD_NAMES` 고정 시험이 즉시 깨지고, 「적/NPC와 플레이어 캐릭터가
같은 그릇에 들어간다」는 성질이 무너진다.

선·호두는 원래 「세션 당일 비경험자 2명이 구두 안내로 새로 만드는 자리를
채울 자리표시자」였다(M0 실험 준비물) — 그 실험은 보류됐다(D-62). 이 파일에는
그 자리표시자 값이 그대로 남아 시험 재료로 쓰인다.
"""

from dataclasses import dataclass

from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rulebooks.openquest import OPENQUEST_ID
from gptrpg.rules_core.entities import Entity, StatEntry

NEW_CHARACTER_STAT_NAMES: tuple[str, ...] = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
"""신규 캐릭터가 쓰는 능력치 여섯 칸의 이름과 화면 표시 순서(시험 재료)."""

NEW_CHARACTER_STAT_ARRAY: tuple[int, ...] = (2, 1, 1, 0, 0, -1)
"""세션 당일 새로 만드는 사람이 여섯 자리에 배치할 값 묶음(정렬하면
`[-1, 0, 0, 1, 1, 2]`). 어느 값을 어느 능력치 자리에 놓을지는 참가자가
직접 고른다 — 이 튜플의 선언 순서가 `NEW_CHARACTER_STAT_NAMES`의 각 자리에
그대로 고정 배치되는 것은 아니다(시험 재료)."""

NEW_CHARACTER_HP_BASE = 16
NEW_CHARACTER_HP_PER_CON = 2
"""체력 = `NEW_CHARACTER_HP_BASE + CON * NEW_CHARACTER_HP_PER_CON`이고
`current`와 `max`를 같은 값으로 둔다. `depleted_effect_ref`는
`"dungeonworld_like.hp_depleted"`.

**적용 범위 — D-49:** 이 규격은 원래 세션 당일 구두 안내로 새로 만드는 두
캐릭터(선·호두 자리)에만 적용됐다. 이미 확정된 브람·나리에는 적용되지
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
                form="numeric",
                current=20,
                max=20,
                depleted_effect_ref="dungeonworld_like.hp_depleted",
            ),
            StatEntry(name="STR", form="numeric", current=2),
            StatEntry(name="DEX", form="numeric", current=0),
            StatEntry(name="CON", form="numeric", current=1),
            StatEntry(name="INT", form="numeric", current=-1),
            StatEntry(name="WIS", form="numeric", current=0),
            StatEntry(name="CHA", form="numeric", current=0),
            # bram만 갖는 일곱 번째 상태값 — 넷 중 상태값 개수가 서로 다른
            # 쌍을 최소 하나 만들어, 개수가 달라도 같은 화면으로 그려짐을
            # 시험이 확인할 수 있게 한다.
            StatEntry(name="방어구", form="numeric", current=2),
        ),
    ),
    "nari": Entity(
        entity_id="player.nari",
        display_name="나리",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(
            StatEntry(
                name="체력",
                form="numeric",
                current=16,
                max=16,
                depleted_effect_ref="dungeonworld_like.hp_depleted",
            ),
            StatEntry(name="STR", form="numeric", current=0),
            StatEntry(name="DEX", form="numeric", current=2),
            StatEntry(name="CON", form="numeric", current=0),
            StatEntry(name="INT", form="numeric", current=1),
            StatEntry(name="WIS", form="numeric", current=1),
            StatEntry(name="CHA", form="numeric", current=-1),
        ),
    ),
    "seon": Entity(
        entity_id="player.seon",
        display_name="선",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(
            # 신규 캐릭터 규격에 맞춘 자리표시자(D-49, 시험 재료).
            StatEntry(
                name="체력",
                form="numeric",
                current=16,
                max=16,
                depleted_effect_ref="dungeonworld_like.hp_depleted",
            ),
            StatEntry(name="STR", form="numeric", current=2),
            StatEntry(name="DEX", form="numeric", current=1),
            StatEntry(name="CON", form="numeric", current=0),
            StatEntry(name="INT", form="numeric", current=1),
            StatEntry(name="WIS", form="numeric", current=0),
            StatEntry(name="CHA", form="numeric", current=-1),
        ),
    ),
    "hodu": Entity(
        entity_id="player.hodu",
        display_name="호두",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(
            # 신규 캐릭터 규격에 맞춘 자리표시자(D-49, 시험 재료).
            StatEntry(
                name="체력",
                form="numeric",
                current=18,
                max=18,
                depleted_effect_ref="dungeonworld_like.hp_depleted",
            ),
            StatEntry(name="STR", form="numeric", current=0),
            StatEntry(name="DEX", form="numeric", current=1),
            StatEntry(name="CON", form="numeric", current=1),
            StatEntry(name="INT", form="numeric", current=-1),
            StatEntry(name="WIS", form="numeric", current=2),
            StatEntry(name="CHA", form="numeric", current=0),
        ),
    ),
}
"""플레이어 캐릭터 넷(시험 재료) — 선언 순서가 `list_characters()`의 순서다."""

CHARACTER_ARCHETYPES: dict[str, str] = {
    "bram": "우물 마을 순찰대에 뒤늦게 합류한 떠돌이 검객 — 몸을 던져 막아서는 데 주저함이 없다",
    "nari": "소리 없이 다가가 자물쇠와 함정을 다루는 밤그림자 — 활을 메고 우물 마을에 흘러들었다",
    "seon": "옛 노래를 기억하는 학자",
    "hodu": "말로 문을 여는 떠돌이",
}
"""캐릭터 한 줄 소개(시험 재료) — `Entity`와 분리된 딕셔너리로 남겨 층
경계를 지킨다(PROJECT.md "세 개의 층")."""


@dataclass(frozen=True)
class CharacterSummary:
    """시험 재료용 한 줄 요약 — 시트 전체가 아니라 목록에 보일 요약만 담는다."""

    character_id: str
    display_name: str
    archetype: str


def list_characters() -> tuple[CharacterSummary, ...]:
    """`PLAYER_CHARACTERS` 선언 순서 그대로 요약 튜플을 돌려준다(시험 재료).

    파이썬 3.7+ 의 딕셔너리는 삽입 순서를 보존하므로 위 선언 순서가 그대로
    이 함수의 순서가 된다.
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
    """알려진 캐릭터 식별자면 `Entity`를, 아니면 `None`을 돌려준다(시험 재료)."""
    return PLAYER_CHARACTERS.get(character_id)


OPENQUEST_CHARACTER: Entity = Entity(
    entity_id="player.hana",
    display_name="하나",
    rulebook_id=OPENQUEST_ID,
    stats=(
        StatEntry(name="STR", form="numeric", current=55),
        StatEntry(name="CON", form="numeric", current=60),
        StatEntry(name="DEX", form="numeric", current=65),
        StatEntry(name="SIZ", form="numeric", current=50),
        StatEntry(name="INT", form="numeric", current=55),
        StatEntry(name="POW", form="numeric", current=55),
        StatEntry(name="CHA", form="numeric", current=45),
        StatEntry(
            name="Hit Points",
            form="numeric",
            current=12,
            max=12,
            depleted_effect_ref="openquest.hp_depleted",
        ),
        StatEntry(name="Magic Points", form="numeric", current=11, max=11),
        StatEntry(name="Armour Points", form="numeric", current=0),
    ),
)
"""OpenQuest 룰북 캐릭터 하나(시험 재료).

**`PLAYER_CHARACTERS` 밖에 따로 둔다.** 그 사전은 「넷」이라는 개수 자체를
전제하는 시험들이 쓰고 있어, 다섯 번째를 넣으면 이 캐릭터와 무관한 시험이
깨진다. 룰북이 다른 캐릭터가 필요한 시험은 `seed_character_created(...,
entity=OPENQUEST_CHARACTER)`로 이것을 직접 넘긴다.

**왜 필요한가.** 여기 있던 캐릭터가 전부 던전월드였던 탓에, 행동 요청이
캐릭터의 룰북을 무시하고 던전월드로 굴러도 시험이 아무것도 눈치채지
못했다 — 브라우저에서 OpenQuest 캐릭터로 굴리면 능력치 이름부터 어긋나
판정이 400으로 막히는데도 그랬다. 룰북이 다른 캐릭터가 재료에 있어야
그 종류의 결함이 시험에 걸린다."""
