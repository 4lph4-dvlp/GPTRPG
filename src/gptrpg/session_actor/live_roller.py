"""실제로 굴리는 도구 (암호학적 난수). rules_core 밖 — 여기서만 secrets를 쓴다."""

import secrets


class LiveRoller:
    """secrets 기반 실제 Roller/PercentileRoller 구현체.

    상속 선언 없이 두 프로토콜을 동시에 만족한다(PEP 544 구조적 타이핑).
    """

    def roll_d6(self) -> int:
        # secrets.randbelow(6)의 범위는 [0, 6)이다. +1을 빠뜨리면 눈에 0이 나온다.
        return secrets.randbelow(6) + 1

    def roll_tens(self) -> int:
        # secrets.randbelow(10)의 범위는 [0, 9]이다. 여기서는 0~9가 맞으므로
        # roll_d6과 달리 +1을 하지 않는다.
        return secrets.randbelow(10)

    def roll_units(self) -> int:
        # roll_tens와 동일 — 0~9가 맞으므로 +1을 하지 않는다.
        return secrets.randbelow(10)
