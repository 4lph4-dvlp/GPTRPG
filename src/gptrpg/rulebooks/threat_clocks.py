"""M0 킬 크리테리아 실험에 쓸 위협 시계 한 편 — Claude가 새로 지은 시나리오다.

이 시나리오는 어떤 룰북·저작물의 원문도 아니다. 판정 방식은 "던전월드
계열" 룰북을 참고하지만, 이야기 내용 자체는 이 모듈이 처음부터 새로 지었다
(D-46) — 던전월드나 다른 저작물의 고유명사·설정·원문을 옮기지 않는다.

D21이 적은 위협 시계 데이터 구조 중 "진행 조건"과 "상태(대기/진행됨/
무효화됨)"는 일부러 담지 않는다 — 진행 시점은 `SessionActor`의 실패
카운터가, 현재 상태는 `GameState.clock_segment`가 이미 유일한 출처다. 이
모듈이 담는 것은 그 진행이 「무슨 이야기인가」뿐이다.

관련 결정: D-46(자체 창작·다양성), D-47(칸 4개·코드 상한선 없음),
D-48(캐스트는 시나리오 캐스트 전체, 국면별 필터링 없음), D21(위협 시계
데이터 구조).
"""

from dataclasses import dataclass

from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rules_core.entities import Entity, StatEntry

THREAT_CLOCK_SEGMENT_COUNT = 4
"""EXP-01이 요구한 칸 수 — D21의 4~6칸 범위 안 값."""


@dataclass(frozen=True)
class ThreatClockContent:
    """위협 시계 하나의 이야기 내용 — 이름 / 정체 / 원하는 것 / 칸 설명 / 파국.

    진행 조건과 상태는 담지 않는다(D21) — 코드가 이미 그 두 가지의 유일한
    출처다.
    """

    clock_id: str
    name: str
    identity: str
    wants: str
    segment_descriptions: tuple[str, ...]
    catastrophe: str


# 진지하게도, 우습게도, 슬프게도 풀릴 수 있게 톤을 하나로 좁히지 않는다.
# 전투(곽서리를 통해)·대화(담녹·이슬·나울)·탐색(우물 주변 흔적)·설득(이슬을
# 믿게 하기, 나울을 달래기) 네 접근이 전부 말이 되는 해법이어야 한다는
# D-46 다양성 요건을 캐스트 구성으로 만족시킨다.
M0_THREAT_CLOCK = ThreatClockContent(
    clock_id="threat",
    name="우물 아래의 것",
    identity=(
        "마을 우물 밑바닥에서 수백 년간 잠들어 있던 낡은 존재. 원래는 땅의 "
        "균형을 지키는 수호자였으나, 오랜 고립과 굶주림으로 뒤틀렸다."
    ),
    wants=(
        "다시 사람들과 이어지고 싶어 한다. 그 유일한 방법이 우물물을 통해 "
        "사람 몸에 스며들어 자신의 일부로 삼는 것뿐이라고 믿는다."
    ),
    segment_descriptions=(
        # 각 줄은 ①무슨 일이 일어나는가 ②그 뒤로 세상에 남는 흔적을 함께
        # 담는다 — 최근 대화가 10턴만 유지되므로 이 흔적이 사실상 유일한
        # 장기 기억 장치다(D21).
        (
            "우물물이 탁하게 흐려지고 비린내가 돈다. 그 물을 마신 염소 두 "
            "마리가 밤사이 사라지고, 우리 안에는 마른 진흙 발자국만 원을 "
            "그리며 남는다."
        ),
        (
            "우물지기 이슬이 밤마다 물 밑에서 자신을 부르는 목소리를 듣는다고 "
            "털어놓지만 아무도 믿지 않는다. 그 사이 마을 아이 나울이 홀린 "
            "듯 우물가를 서성이다 발견된다."
        ),
        (
            "나울이 다시 우물로 걸어가려다 저지당하자 낯선 언어로 웅얼거리기 "
            "시작한다. 순찰대장 곽서리가 보낸 정찰병 한 명이 그날 밤 "
            "돌아오지 않는다."
        ),
        (
            "우물 둘레의 돌이 안쪽부터 금이 가며 축축한 냉기를 뿜는다. 마을 "
            "회관 문이 저절로 안에서 잠기고, 그 안에 있던 사람들의 그림자가 "
            "하나로 뭉쳐 흔들린다."
        ),
    ),
    catastrophe=(
        "우물이 한꺼번에 넘쳐 그 물이 닿은 모든 이의 감각이 그것 하나로 "
        "이어진다 — 마을 전체가 서로 다른 목소리가 아니라 하나의 부름에 "
        "응답하는 합창이 된다."
    ),
)

THREAT_CAST: tuple[Entity, ...] = (
    Entity(
        # 원하는 것: 우물의 비밀(선대의 봉인 약속)을 지켜 마을이 공황에
        # 빠지지 않게 막는 것. 감추는 것: 그 봉인 약속을 맺은 장본인이라는
        # 사실 — 죄책감 때문에 먼저 나서서 말하지 못한다.
        entity_id="scenario.village_elder",
        display_name="촌장 담녹",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(),
    ),
    Entity(
        # 원하는 것: 누군가 자신의 말을 믿어 주는 것. 감추는 것: 몇 주 전부터
        # 우물 밑에서 목소리를 듣고 있고, 스스로도 미쳐 가는 게 아닌가 겁내고
        # 있지만 사실은 가장 먼저 이상을 알아챈 사람이다.
        entity_id="scenario.well_keeper",
        display_name="우물지기 이슬",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(),
    ),
    Entity(
        # 원하는 것: 마을을 무력으로라도 지키는 것. 감추는 것: 이미 정찰병
        # 한 명을 우물의 영향으로 잃었고, 공황을 막으려 그 사실을 숨기고
        # 있다.
        entity_id="scenario.militia_captain",
        display_name="순찰대장 곽서리",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(
            StatEntry(
                name="체력",
                current=12,
                max=12,
                depleted_effect_ref="dungeonworld_like.hp_depleted",
            ),
            StatEntry(name="방어구", current=1),
        ),
    ),
    Entity(
        # 원하는 것: "따뜻하고 다 함께 있는" 우물로 돌아가는 것 — 본인은 이게
        # 위험하다고 느끼지 않는다. 감추는 것: 우물의 영향을 가장 먼저,
        # 가장 깊이 받은 존재라 말을 걸면 조각난 형태로나마 그 정체의 단서를
        # 무심코 흘린다.
        entity_id="scenario.entranced_child",
        display_name="홀린 아이 나울",
        rulebook_id=DUNGEONWORLD_LIKE_ID,
        stats=(),
    ),
)
