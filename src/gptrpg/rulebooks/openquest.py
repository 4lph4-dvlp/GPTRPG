"""OpenQuest System Resource Document (CC BY 4.0)의 스킬 판정 규칙 선언.

출처: https://openquestrpg.com/srd/skills/skill-rules/ — 굴림이 기술값
이하면 성공, 초과면 실패, 두 주사위 눈이 같으면서 성공이면 크리티컬, 두 눈이
같으면서 실패면 펌블. 라이선스 첨부 문구와 표기 범위는 저장소 최상위
`LICENSES.md`를 본다(D-18: CC 라이선스가 있는 실제 룰북 자료).
"""

from gptrpg.rules_core.resolution import Modifier
from gptrpg.rules_core.resolution_d100 import TARGET_SHIFT
from gptrpg.rules_core.rulebook import (
    D100_ROLL_UNDER,
    DifficultyLevelDecl,
    GradeBand,
    OutcomeList,
    ResourceAxisDecl,
    Rulebook,
    require_difficulty,
)

OPENQUEST_ID = "openquest"

OPENQUEST_GRADE_BANDS: tuple[GradeBand, ...] = (
    # OpenQuest SRD는 PbtA류 부분 성공 사다리를 갖지 않는다 — 굴림이
    # 기술값 이하면 성공/초과면 실패로만 갈리고, doubles가 그 위에
    # 크리티컬/펌블을 얹을 뿐이다(이 파일 상단 도크스트링, 출처 인용).
    # 그래서 네 등급 전부 costs=False다: "성공했지만 뭔가 잃는다"는
    # 결과 카테고리 선택이 이 판정 방식 자체에는 없다(그런 결과를 쓰고
    # 싶은 룰북 콘텐츠는 outcome_list로 별도 표현한다 — Task 2/3).
    # succeeded는 counts_as_failure의 반대다 — 이 룰북은 "성공했지만
    # 시계는 돈다" 같은 어긋남이 SRD에 없다.
    GradeBand(
        name="critical",
        counts_as_failure=False,
        succeeded=True,
        costs=False,
        margin_at_least=0,
        requires_doubles=True,
    ),
    GradeBand(
        name="success",
        counts_as_failure=False,
        succeeded=True,
        costs=False,
        margin_at_least=0,
    ),
    GradeBand(
        name="fumble",
        counts_as_failure=True,
        succeeded=False,
        costs=False,
        margin_at_most=-1,
        requires_doubles=True,
    ),
    GradeBand(name="failure", counts_as_failure=True, succeeded=False, costs=False),
)

OPENQUEST_RESOURCE_AXES: tuple[ResourceAxisDecl, ...] = (
    # 크리처가 실제로 갖고 있는 열 축 — 이 단계는 numeric 형태 하나만
    # 관통시킨다(11-01). 능력치 일곱(STR~CHA)에는 12-01 Task 3이
    # `stat_usage="use_as_target"`을 더한다(D-01 Assumption A5 — 이
    # 저장소의 웹 캐릭터 로스터(`characters_data.PLAYER_CHARACTERS`)가
    # 아직 던전월드류뿐이라 실제 OpenQuest 판정 캐릭터가 없다. 이 값은
    # OpenQuest가 d100 롤언더 판정 방식(`use_as_target`)에 능력치 축을
    # 실제로 연결한다는 실증이고, 진짜 기술값(근접 무기 기술 등)이 판정에
    # 쓰이는 것은 OpenQuest 플레이어 캐릭터가 생기는 다음 마일스톤이다).
    ResourceAxisDecl(name="STR", form="numeric", stat_usage="use_as_target"),
    ResourceAxisDecl(name="CON", form="numeric", stat_usage="use_as_target"),
    ResourceAxisDecl(name="DEX", form="numeric", stat_usage="use_as_target"),
    ResourceAxisDecl(name="SIZ", form="numeric", stat_usage="use_as_target"),
    ResourceAxisDecl(name="INT", form="numeric", stat_usage="use_as_target"),
    ResourceAxisDecl(name="POW", form="numeric", stat_usage="use_as_target"),
    ResourceAxisDecl(name="CHA", form="numeric", stat_usage="use_as_target"),
    ResourceAxisDecl(name="Hit Points", form="numeric"),
    ResourceAxisDecl(name="Magic Points", form="numeric"),
    ResourceAxisDecl(name="Armour Points", form="numeric"),
    # 아래 열 축은 `rulebooks/moves.py`의 `OPENQUEST_MOVES`가 이미 쓰고
    # 있던 기술 이름을 그대로 옮긴 것이다(11-02) — 새로 지어내지 않았다.
    # 지금 등록된 크리처(고블린·스켈레톤)는 이 축들의 `StatEntry`를 갖지
    # 않는데, 그것은 위반이 아니다(D-04) — 개체가 룰북 선언 축을 전부 가질
    # 필요는 없다. 이 선언이 없으면 `validate_move_stats`가 무브의
    # `default_stat`을 대조할 축 자체가 없어 등록이 통째로 막힌다(T-11-07).
    ResourceAxisDecl(name="근접 무기 기술", form="numeric"),
    ResourceAxisDecl(name="회피 기술", form="numeric"),
    ResourceAxisDecl(name="은신 기술", form="numeric"),
    ResourceAxisDecl(name="지각 기술", form="numeric"),
    ResourceAxisDecl(name="일반 지식 기술", form="numeric"),
    ResourceAxisDecl(name="설득 기술", form="numeric"),
    ResourceAxisDecl(name="장치 기술", form="numeric"),
    ResourceAxisDecl(name="운동 기술", form="numeric"),
    ResourceAxisDecl(name="의지 기술", form="numeric"),
    ResourceAxisDecl(name="원거리 무기 기술", form="numeric"),
)

OPENQUEST_DIFFICULTY: dict[str, int] = {
    "easy": 50,
    "simple": 20,
    "normal": 0,
    "difficult": -20,
    "hard": -50,
}
"""OpenQuest SRD 난이도 다섯 단계 — 기술값에 가산할 목표값 변경 폭.
출처: https://openquestrpg.com/srd/skills/difficulty/ (`[CITED]`). 값의
권위는 이 사전에 남아 있다 — `OPENQUEST_DIFFICULTY_LEVELS`가 이 사전을
그대로 옮겨 담은 선언 형식이다(D-02, 12-01 Task 3)."""

OPENQUEST_DIFFICULTY_LEVELS: tuple[DifficultyLevelDecl, ...] = tuple(
    DifficultyLevelDecl(name=name, modifier_type=TARGET_SHIFT, value=value)
    for name, value in OPENQUEST_DIFFICULTY.items()
)
"""D-02가 요구하는 닫힌 이름 목록 — 바깥(브라우저·CLI)이 판정에 실을 수
있는 난이도 이름은 이 목록에 있는 다섯 개뿐이다. `require_difficulty`가
이 목록에서 이름으로 찾는다."""

OPENQUEST_OUTCOME_LIST = OutcomeList(categories=())
"""빈 목록이다 — SRD가 실패/펌블에 절차적 결과 카테고리(던전월드 GM 대응
목록 같은 것)를 정하지 않는다. 이 파일이 인용하는 SRD 범위(스킬 판정
규칙, 이 파일 상단 도크스트링)는 성공/실패/크리티컬/펌블 등급 산출까지만
다루고, 그 뒤에 "무슨 일이 일어나는가"는 절차가 아니라 서술이다 — 지어내
넣지 않는 것이 이 파일의 기존 규율이다(`OPENQUEST_RESOURCE_AXES`의
"필드 단위 상세 규격은 M0 범위 밖" 관례와 같은 판단). 빈 목록은 미완성이
아니라 정상값이고, OpenQuest의 판정 결과는 전부 재량 판정(12-06)으로
간다(RULE-13, D-07의 귀결)."""

OPENQUEST = Rulebook(
    rulebook_id=OPENQUEST_ID,
    display_name="OpenQuest",
    resolution_method=D100_ROLL_UNDER,
    grade_bands=OPENQUEST_GRADE_BANDS,
    resource_axes=OPENQUEST_RESOURCE_AXES,
    check_trigger_mode="declared_list",
    difficulty_levels=OPENQUEST_DIFFICULTY_LEVELS,
    outcome_list=OPENQUEST_OUTCOME_LIST,
)


def difficulty_modifier(name: str) -> Modifier:
    """난이도 이름 하나를 `TARGET_SHIFT` 수정치로 바꾼다.

    SRD 원문은 "판정 하나에 난이도 수정치는 하나만 쓴다"고 정하지만, 그것은
    룰북의 운용 규칙이지 플랫폼의 계산 제약이 아니다 — 플랫폼은 여러 개를
    합산할 수 있어야 한다(다른 룰북은 여러 개를 허용한다). 이 함수는 하나만
    돌려주고, 여러 개를 합칠지는 호출부(룰북 운용 규칙)가 정한다.

    이제 새 선언(`OPENQUEST_DIFFICULTY_LEVELS`)을 `require_difficulty`로
    조회한다(D-02, 12-01 Task 3) — 기존 호출부·시험은 그대로 통과한다
    (값과 예외 상황이 `OPENQUEST_DIFFICULTY` 사전과 동일하다).
    """
    level = require_difficulty(OPENQUEST, name)
    return Modifier(
        type=level.modifier_type,
        value=level.value,
        source=f"openquest:difficulty:{name}",
    )
