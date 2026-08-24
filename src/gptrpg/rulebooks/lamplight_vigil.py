"""낭독문형 시나리오 한 편 — 「우물 아래의 것」(`threat_clocks.py`)과 무관한
새 이야기다(D-21). 이 시나리오는 어떤 룰북·저작물의 원문도 아니다 —
`threat_clocks.py`가 세운 관례(D-46)를 그대로 따른다. 판정 방식은 "던전월드
계열" 룰북을 참고하지만, 이야기 내용 자체는 이 모듈이 처음부터 새로 지었다.

D-06(낭독문 그대로 띄우기)과 D-07(등록 시점 검사)이 실제로 동작하는지 보이는
최소 분량이다 — 완결편을 쓰는 것이 아니라, 시나리오 선언 형식이 낭독문형과
메모형 두 종류를 다 받는다는 것을 실제 데이터로 증명하는 것이 이 파일의
목적이다(D-21 assumption-delta, "일차가 된 이름"이 `scenario_id`로 격상되며
「우물 아래의 것」이 이 등록소의 한 항목으로 격하될 13-03의 전 단계).
"""

from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rules_core.entities import Entity
from gptrpg.rules_core.scenario import OpeningDecl, ScenarioDecl, ThreatClockContent

LAMPLIGHT_VIGIL_ID = "lamplight_vigil"

LAMPLIGHT_VIGIL = ScenarioDecl(
    scenario_id=LAMPLIGHT_VIGIL_ID,
    display_name="등대의 야경",
    opening_kind="scripted",
    opening=OpeningDecl(
        who_you_are=(
            "당신들은 오늘 밤 이 낡은 등대를 지키기로 한 사람들이다. 정식"
            " 등대지기는 사흘 전 배를 타고 나간 뒤 아직 돌아오지 않았다."
        ),
        what_you_sense=(
            "차가운 바닷바람이 창을 두드리고, 아래층 기름 램프가 이유 없이"
            " 깜빡인다. 파도 소리 사이로 낯선 리듬의 종소리가 섞여 들려온다."
        ),
        why_it_matters=(
            "이 불빛이 꺼지면 오늘 밤 항구로 들어오는 배들이 앞바다의 암초를"
            " 볼 수 없다 — 그리고 저 종소리는 어느 배에서도 나는 소리가 아니다."
        ),
        hooks=(
            "탑 아래 나선 계단에 아직 마르지 않은 젖은 발자국이 찍혀 있다"
            " — 밖에서 안으로 들어온 방향이다.",
            "등대지기의 책상 위에 쓰다 만 항해 일지가 펼쳐져 있고, 마지막"
            " 줄이 문장 중간에서 끊겨 있다.",
        ),
        invitation="당신들은 지금 무엇을 하시겠습니까?",
    ),
    improv_people=False,
    improv_things=True,
    cast=(
        Entity(
            entity_id="scenario.absent_keeper",
            display_name="등대지기 하란",
            rulebook_id=DUNGEONWORLD_LIKE_ID,
            stats=(),
        ),
    ),
    threat_clock=ThreatClockContent(
        clock_id="tide",
        name="차오르는 종소리",
        identity=(
            "등대 불빛에 이끌려 물 밑에서 떠오른, 이름 없는 조류의 무리."
            " 빛을 따라다니는 습성이 있을 뿐 딱히 악의는 없다."
        ),
        wants="더 밝고 더 오래 켜진 불빛 쪽으로 계속 모여든다.",
        segment_descriptions=(
            "먼바다에서 낮은 종소리가 한 번 울리고, 잔잔하던 파도가 불규칙"
            "하게 부서지기 시작한다.",
            "등대 계단 창밖으로 물비린내가 스며들고, 유리창에 물기 어린"
            " 손자국 같은 얼룩이 남는다.",
            "종소리가 두 겹, 세 겹으로 겹쳐 들리고, 램프 불빛이 이유 없이"
            " 푸르스름하게 흔들린다.",
            "등대 아래 바위에 부딪히는 파도가 잠시 완전히 멈췄다가, 한꺼번"
            "에 탑 벽을 때린다.",
        ),
        catastrophe=(
            "등대 불빛이 물속에서부터 삼켜지듯 꺼지고, 어둠 속에서 종소리"
            "만 탑을 완전히 둘러싼다."
        ),
    ),
    imagery_setting="a stone lighthouse tower at night, storm clouds, lantern light, sea mist",
)
