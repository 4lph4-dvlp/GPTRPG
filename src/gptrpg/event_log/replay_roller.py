"""기록에서 눈을 읽어 되먹이는 굴림 도구.

왜 씨앗이 아니라 눈 값인가: secrets 기반 난수는 예측 불가능하도록 설계된
물건이라 씨앗을 정해 두고 나중에 같은 씨앗으로 다시 굴리는 것이 원리적으로
불가능하다. 굴러 나온 눈을 그대로 남기는 것이 유일한 되감기 수단이다 (D-15).
"""

from collections.abc import Iterable, Iterator


class ReplayExhausted(Exception):
    """기록에 남은 눈을 다 쓴 뒤에도 굴림을 더 요청받았을 때 던진다.

    파이썬 기본 반복 종료 예외(StopIteration)를 그대로 새어 나가게 두면
    부르는 쪽에서 반복문 종료로 오해되어 조용히 삼켜질 수 있다.
    """

    def __init__(self, session_id: str, consumed: int) -> None:
        super().__init__(
            f"session {session_id!r}: replay roller exhausted after {consumed} roll(s)"
        )
        self.session_id = session_id
        self.consumed = consumed


class ReplayRoller:
    """눈 목록을 받아 순서대로 하나씩 돌려주는 굴림 도구.

    Roller를 상속하지 않는다 — roll_d6(self) -> int 메서드만 구조적으로
    맞으면 그대로 통과한다.
    """

    def __init__(self, recorded_rolls: Iterable[int], session_id: str = "") -> None:
        self._rolls: Iterator[int] = iter(recorded_rolls)
        self._session_id = session_id
        self._consumed = 0

    def roll_d6(self) -> int:
        return self._next_roll()

    def roll_tens(self) -> int:
        """기록된 눈에서 십의 자리 하나를 꺼낸다.

        `roll_d6`과 **같은 반복자**에서 꺼낸다 — `rolls_from_events`가 만든
        평평한 목록이 기록된 순서 그대로 되먹여져야 하므로, 판정 방식에
        따라 소비 자리를 나누지 않는다.
        """
        return self._next_roll()

    def roll_units(self) -> int:
        """기록된 눈에서 일의 자리 하나를 꺼낸다. `roll_tens`와 소비 자리를 공유한다."""
        return self._next_roll()

    def _next_roll(self) -> int:
        try:
            value = next(self._rolls)
        except StopIteration as exc:
            raise ReplayExhausted(self._session_id, self._consumed) from exc
        self._consumed += 1
        return value


def rolls_from_events(events: Iterable) -> list[int]:
    """판정 사건들을 순번 순서대로 훑어 rolls를 하나의 평평한 정수 목록으로 이어 붙인다."""
    ordered = sorted(events, key=lambda event: event.seq)
    rolls: list[int] = []
    for event in ordered:
        rolls.extend(event.rolls)
    return rolls
