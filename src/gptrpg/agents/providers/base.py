"""제공자 하나가 갖춰야 할 최소 모양. 어떤 SDK도 import하지 않는다."""

from collections.abc import Iterator
from typing import Protocol, runtime_checkable

from gptrpg.agents.envelope import AgentResult


@runtime_checkable
class Provider(Protocol):
    """다섯 제공자가 공통으로 구현하는 좁은 프로토콜.

    스트리밍은 토큰 수를 마지막에야 알 수 있다 — `stream`을 반복자로 다
    소진한 뒤 `last_result()`로 토큰·시간을 가져간다는 것이 이 프로토콜의
    규약이다.
    """

    name: str

    def list_models(self) -> list[str]:
        """이 제공자가 지금 제공하는 모델 이름의 실시간 목록."""
        ...

    def complete(
        self,
        *,
        model: str,
        system: list[dict],
        messages: list[dict],
        max_tokens: int,
        timeout_s: float,
    ) -> AgentResult:
        """한 번 부르고 결과를 즉시 돌려준다(비스트리밍)."""
        ...

    def stream(
        self,
        *,
        model: str,
        system: list[dict],
        messages: list[dict],
        max_tokens: int,
        timeout_s: float,
    ) -> Iterator[str]:
        """텍스트 조각을 스트리밍으로 흘려보낸다. 다 소진한 뒤 `last_result()`를 부른다."""
        ...

    def last_result(self) -> AgentResult:
        """가장 최근 `stream()` 호출이 끝난 뒤의 토큰·시간을 돌려준다."""
        ...

    def note_result(self, result: AgentResult) -> None:
        """스트림이 **비정상 종료**했을 때 실패 껍데기를 남기는 유일한 공개 경로.

        정상 완주는 어댑터 자신의 `stream()`/`complete()`가 이미 `last_result()`를
        채우므로 이 메서드를 부를 필요가 없다 — 호출한 쪽(`master_gm.narrate()`의
        실패 경로)이 재시도까지 실패했거나 조각이 나간 뒤 끊겼을 때만 이 메서드로
        실패 껍데기를 넘긴다.

        **위임 어댑터(`NimProvider`/`OpenRouterProvider`)는 이 값이 반드시 위임
        대상까지 도달하게 만들어야 한다.** 위임 어댑터는 자기 `_last_result`를
        갖지 않으므로, 바깥에서 이 메서드가 아니라 사적 속성에 직접 대입하면
        아무도 읽지 않는 새 속성 하나만 만들고 값이 조용히 사라진다 — 이것이
        03-UAT.md G-03-3의 실제 크래시 원인이었다.
        """
        ...
