"""2d6 판정 등급 산출 — 순수 함수."""

Grade = str
"""등급 이름. 던전월드 세 이름("strong_hit"/"weak_hit"/"miss")은 플랫폼
타입이 아니라 `gptrpg.rulebooks.dungeonworld_like`가 선언하는 한 룰북의
내용으로 격하되었다 — 다른 룰북은 다른 이름 집합을 쓸 수 있다(D32)."""

DEFAULT_TARGET = 10
WEAK_HIT_BAND = 3


def grade_for_total(total: int, target: int) -> Grade:
    """굴림 합계와 목표값에서 등급을 산출한다.

    target 이상이면 strong_hit, target - WEAK_HIT_BAND 이상이면 weak_hit,
    그 아래는 miss.
    """
    if total >= target:
        return "strong_hit"
    if total >= target - WEAK_HIT_BAND:
        return "weak_hit"
    return "miss"
