"""분류기가 고를 **닫힌 목록**을 룰북 데이터로 선언한다.

`gptrpg.rules_core`는 이 목록을 모른다 — 무브는 룰북이 정하는 표현 어휘이지
플랫폼 규칙이 아니다(층 2, PROJECT.md). `action_classifier`는 이 목록 밖의
이름을 `UnknownMove`로 거부한다(RIG-01, D-16). 세 번째 룰북의 무브 목록은
이 파일에 표를 더하는 것으로 끝나야 한다(HYP-03이 세운 성질).
"""

from dataclasses import dataclass

from gptrpg.rulebooks import UnknownRulebook
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rulebooks.openquest import OPENQUEST_ID


@dataclass(frozen=True)
class MoveDecl:
    """무브 하나의 선언 — 분류기 프롬프트에 그대로 들어간다."""

    move_id: str
    display_name: str
    default_stat: str
    trigger: str


DUNGEONWORLD_LIKE_MOVES: tuple[MoveDecl, ...] = (
    MoveDecl(
        move_id="hack_and_slash",
        display_name="근접전으로 부딪히다",
        default_stat="STR",
        trigger="적과 직접 무기를 맞대고 싸울 때",
    ),
    MoveDecl(
        move_id="volley",
        display_name="원거리로 쏘다",
        default_stat="DEX",
        trigger="거리를 두고 활·투척 무기로 공격할 때",
    ),
    MoveDecl(
        move_id="defy_danger",
        display_name="위험을 무릅쓰다",
        default_stat="상황에 맞는 능력치",
        trigger="위험한 상황에서 다치거나 나쁜 일을 피하려 할 때",
    ),
    MoveDecl(
        move_id="discern_realities",
        display_name="상황을 꿰뚫어 보다",
        default_stat="WIS",
        trigger="주의 깊게 주변을 살피거나 질문할 때",
    ),
    MoveDecl(
        move_id="parley",
        display_name="담판을 짓다",
        default_stat="CHA",
        trigger="레버리지를 걸고 NPC에게 요구할 때",
    ),
    MoveDecl(
        move_id="aid_or_interfere",
        display_name="돕거나 훼방 놓다",
        default_stat="상황에 맞는 능력치",
        trigger="다른 플레이어의 판정을 돕거나 방해할 때",
    ),
    MoveDecl(
        move_id="defend",
        display_name="지키다",
        default_stat="CON",
        trigger="누군가나 무언가를 위험으로부터 막아설 때",
    ),
    MoveDecl(
        move_id="spout_lore",
        display_name="아는 것을 풀어놓다",
        default_stat="INT",
        trigger="세계에 대한 지식을 캐물을 때",
    ),
    MoveDecl(
        move_id="tracking",
        display_name="흔적을 쫓다",
        default_stat="WIS",
        trigger="사람이나 짐승의 흔적을 추적할 때",
    ),
    MoveDecl(
        move_id="pick_lock_or_trap",
        display_name="자물쇠나 함정을 다루다",
        default_stat="DEX",
        trigger="자물쇠를 따거나 함정을 해체할 때",
    ),
)
"""던전월드 계열 룰북용 무브 열 개 (EXP-01이 적은 "판정 종류 10개 남짓" 규모)."""


OPENQUEST_MOVES: tuple[MoveDecl, ...] = (
    MoveDecl(
        move_id="close_combat",
        display_name="백병전",
        default_stat="근접 무기 기술",
        trigger="근접 무기로 직접 부딪힐 때",
    ),
    MoveDecl(
        move_id="evade",
        display_name="회피",
        default_stat="회피 기술",
        trigger="공격이나 위험을 피하려 할 때",
    ),
    MoveDecl(
        move_id="stealth",
        display_name="은신",
        default_stat="은신 기술",
        trigger="숨거나 몰래 움직일 때",
    ),
    MoveDecl(
        move_id="perception",
        display_name="지각",
        default_stat="지각 기술",
        trigger="주변을 살피거나 뭔가를 알아챌 때",
    ),
    MoveDecl(
        move_id="lore_common",
        display_name="일반 지식",
        default_stat="일반 지식 기술",
        trigger="흔한 지식을 떠올려야 할 때",
    ),
    MoveDecl(
        move_id="persuade",
        display_name="설득",
        default_stat="설득 기술",
        trigger="말로 다른 이를 움직이려 할 때",
    ),
    MoveDecl(
        move_id="devices",
        display_name="장치 다루기",
        default_stat="장치 기술",
        trigger="자물쇠·함정 같은 기계 장치를 다룰 때",
    ),
    MoveDecl(
        move_id="athletics",
        display_name="운동",
        default_stat="운동 기술",
        trigger="달리거나 오르거나 뛰어넘을 때",
    ),
    MoveDecl(
        move_id="willpower",
        display_name="의지",
        default_stat="의지 기술",
        trigger="공포·유혹·정신적 압박을 버틸 때",
    ),
    MoveDecl(
        move_id="ranged_combat",
        display_name="원거리전",
        default_stat="원거리 무기 기술",
        trigger="활 같은 원거리 무기로 공격할 때",
    ),
)
"""OpenQuest 룰북용 기술 열 개 — SRD 스킬 이름을 이 프로젝트 어휘로 옮긴 것.
숫자·판정 방식은 룰북 데이터(`rulebooks/openquest.py`)에만 있다."""


MOVE_CATALOGS: dict[str, tuple[MoveDecl, ...]] = {
    DUNGEONWORLD_LIKE_ID: DUNGEONWORLD_LIKE_MOVES,
    OPENQUEST_ID: OPENQUEST_MOVES,
}


def get_moves(rulebook_id: str) -> tuple[MoveDecl, ...]:
    """등록된 룰북의 무브 목록을 이름으로 찾는다. 없으면 `UnknownRulebook`."""
    moves = MOVE_CATALOGS.get(rulebook_id)
    if moves is None:
        raise UnknownRulebook(rulebook_id)
    return moves
