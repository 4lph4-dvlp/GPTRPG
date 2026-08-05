"""OpenQuest System Resource Document(CC BY 4.0)의 크리처 두 종을 실제 수치
그대로 옮긴다 — 메인 룰북이 아니라 SRD 페이지 원문에서 옮겼다. 여기 적힌
수치는 이 단계가 지어낸 것이 하나도 없다(D-18).

출처:
- https://openquestrpg.com/srd/creatures/creatures-g/ (고블린)
- https://openquestrpg.com/srd/creatures/creatures-s/ (스켈레톤)

무기·주문·이동력·특수능력 등 나머지 항목은 담지 않는다 — 룰북 데이터의
필드 단위 상세 규격은 M0 범위 밖이다. 필수 첨부 문구와 라이선스 표기 범위는
저장소 최상위 `LICENSES.md`를 본다.
"""

from gptrpg.rulebooks.openquest import OPENQUEST_ID
from gptrpg.rules_core.entities import Entity, StatEntry

OPENQUEST_GOBLIN = Entity(
    entity_id="openquest.goblin",
    display_name="Goblin",
    rulebook_id=OPENQUEST_ID,
    stats=(
        # 능력치 일곱 — 소모되지 않으므로 max/depleted_effect_ref 없음.
        StatEntry(name="STR", current=10),
        StatEntry(name="CON", current=10),
        StatEntry(name="DEX", current=17),
        StatEntry(name="SIZ", current=7),
        StatEntry(name="INT", current=11),
        StatEntry(name="POW", current=10),
        StatEntry(name="CHA", current=7),
        # 체력/마법점 — 바닥날 수 있는 값이므로 참조 문자열을 채운다.
        # 그 참조가 가리키는 실제 연산은 M1의 D7 몫이다.
        StatEntry(
            name="Hit Points",
            current=9,
            max=9,
            depleted_effect_ref="openquest.hit_points_depleted",
        ),
        StatEntry(
            name="Magic Points",
            current=10,
            max=10,
            depleted_effect_ref="openquest.magic_points_depleted",
        ),
        # 방어점 — 능력치와 마찬가지로 소모되는 값이 아니다.
        StatEntry(name="Armour Points", current=2),
    ),
)

OPENQUEST_SKELETON = Entity(
    entity_id="openquest.skeleton",
    display_name="Skeleton",
    rulebook_id=OPENQUEST_ID,
    stats=(
        StatEntry(name="STR", current=13),
        StatEntry(name="CON", current=4),
        StatEntry(name="DEX", current=11),
        StatEntry(name="SIZ", current=11),
        # 스켈레톤은 지력·의지·매력이 없다 — 0이 정상이고 거부되지 않는다.
        StatEntry(name="INT", current=0),
        StatEntry(name="POW", current=0),
        StatEntry(name="CHA", current=0),
        StatEntry(
            name="Hit Points",
            current=8,
            max=8,
            depleted_effect_ref="openquest.hit_points_depleted",
        ),
        # 마법점 0인 언데드 — current==max==0, 정상.
        StatEntry(
            name="Magic Points",
            current=0,
            max=0,
            depleted_effect_ref="openquest.magic_points_depleted",
        ),
        StatEntry(name="Armour Points", current=2),
    ),
)

OPENQUEST_CREATURES: tuple[Entity, ...] = (OPENQUEST_GOBLIN, OPENQUEST_SKELETON)
