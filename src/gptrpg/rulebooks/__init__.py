"""등록된 룰북 이름 -> 선언을 잇는 등록소. 새 룰북은 여기 등록만 하면 된다."""

from gptrpg.rules_core.rulebook import Rulebook
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE, DUNGEONWORLD_LIKE_ID
from gptrpg.rulebooks.openquest import OPENQUEST, OPENQUEST_ID

RULEBOOKS: dict[str, Rulebook] = {
    DUNGEONWORLD_LIKE_ID: DUNGEONWORLD_LIKE,
    OPENQUEST_ID: OPENQUEST,
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
