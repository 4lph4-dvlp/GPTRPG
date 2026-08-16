"""등록된 룰북 이름 -> 선언을 잇는 등록소. 새 룰북은 여기 등록만 하면 된다."""

from gptrpg.rules_core.entities import Entity
from gptrpg.rules_core.rulebook import (
    Rulebook,
    validate_entity_axes,
    validate_grade_bands,
    validate_move_stats,
    validate_trigger_mode,
)
from gptrpg.rulebooks.cairn import CAIRN, CAIRN_EXAMPLE_ADVENTURER, CAIRN_ID
from gptrpg.rulebooks.dungeonworld_like import (
    DUNGEONWORLD_LIKE,
    DUNGEONWORLD_LIKE_ID,
    EXAMPLE_SINGLE_STAT_FOE,
)
from gptrpg.rulebooks.openquest import OPENQUEST, OPENQUEST_ID
from gptrpg.rulebooks.openquest_creatures import OPENQUEST_CREATURES

RULEBOOKS: dict[str, Rulebook] = {
    DUNGEONWORLD_LIKE_ID: DUNGEONWORLD_LIKE,
    OPENQUEST_ID: OPENQUEST,
    CAIRN_ID: CAIRN,
}


class UnknownRulebook(Exception):
    """등록되지 않은 rulebook_id로 조회했을 때 던진다.

    기본 룰북으로 조용히 대체하면 요청한 것과 다른 규칙으로 판정이 돈다
    (T-02-04).
    """

    def __init__(self, rulebook_id: str) -> None:
        super().__init__(f"등록되지 않은 룰북: {rulebook_id!r}")
        self.rulebook_id = rulebook_id


def get_rulebook(rulebook_id: str) -> Rulebook:
    """등록된 룰북을 이름으로 찾는다. 없으면 `UnknownRulebook`."""
    rulebook = RULEBOOKS.get(rulebook_id)
    if rulebook is None:
        raise UnknownRulebook(rulebook_id)
    return rulebook


_REGISTERED_ENTITIES_FOR_AXIS_CHECK: dict[str, tuple[Entity, ...]] = {
    DUNGEONWORLD_LIKE_ID: (EXAMPLE_SINGLE_STAT_FOE,),
    OPENQUEST_ID: OPENQUEST_CREATURES,
    CAIRN_ID: (CAIRN_EXAMPLE_ADVENTURER,),
}
"""등록 시점에 축 정합성을 검사할 개체 상수 — `web/characters_data.py`의
플레이어 캐릭터 넷은 여기 없다. `rulebooks` 패키지가 `web` 패키지를
import하면 층 방향이 뒤집힌다(`.importlinter` contract 2) — 대신
`tests/test_rulebook.py`의 `test_all_player_characters_match_their_rulebook_axes`가
그 캐릭터들을 검사한다."""


def validate_registered_rulebooks() -> None:
    """`RULEBOOKS`에 등록된 각 룰북에 네 검사를 돌린다 — 등급 밴드의
    가려짐/구멍(D-15), 무브 `default_stat`이 실재하는 축인지(T-11-07),
    이 모듈이 아는 개체들의 `StatEntry`가 그 룰북 축과 맞는지(D-01), 그리고
    `check_trigger_mode`가 무브 목록 길이와 어긋나지 않는지(D-12, T-11-14).
    위반이 있으면 이 모듈이 임포트되는 순간 예외로 죽는다.

    **등록 시점 검사는 런타임 방어선을 대체하지 않는다.**
    `tests/test_session_actor.py`의 `_GAPPED_RULEBOOK`은 `RULEBOOKS`에
    실행 중 직접 꽂아 넣는 방식이라 이 함수를 지나가지 않는다 — 그 시험은
    구멍 있는 룰북이 **런타임 판정**에서도 raw traceback이 아니라
    `CommandRejected`로 잡히는지 확인하는 별개의 방어선이다. 이 함수는
    "정적으로 등록된 룰북이 처음부터 깨져 있지 않은가"를, 그 시험은
    "런타임에 깨진 룰북이 들어와도 턴이 안 죽는가"를 각각 지킨다.
    """
    from gptrpg.rulebooks.moves import MOVE_CATALOGS  # 지연 import — moves.py가
    # 이 모듈(gptrpg.rulebooks)을 최상단에서 import하므로, 여기서 최상단에
    # 두면 순환 import가 생긴다.

    for rulebook_id, rulebook in RULEBOOKS.items():
        validate_grade_bands(rulebook.grade_bands)
        moves = MOVE_CATALOGS.get(rulebook_id, ())
        default_stats = tuple(move.default_stat for move in moves)
        validate_move_stats(default_stats, rulebook)
        validate_trigger_mode(rulebook.check_trigger_mode, len(moves))
        for entity in _REGISTERED_ENTITIES_FOR_AXIS_CHECK.get(rulebook_id, ()):
            validate_entity_axes(entity, rulebook)


validate_registered_rulebooks()
