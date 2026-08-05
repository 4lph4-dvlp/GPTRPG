"""저장소에서 읽은 사건들을 순수 리듀서로 접는다. 읽기 전용 — 아무것도 쓰지 않는다."""

from collections.abc import Iterable

from gptrpg.event_log.schema import GameEvent
from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.reducer import GameState, fold


def rebuild_state_from_events(session_id: str, events: Iterable[GameEvent]) -> GameState:
    """이미 읽어 둔 사건 목록을 접어 상태를 만든다.

    **호출부가 사건 목록을 이미 손에 들고 있을 때 쓴다.** 그런 자리에서
    `rebuild_state`를 부르면 같은 세션의 사건 전체를 저장소에서 **한 번 더**
    읽는다 — 폴링 처리기(`web.routes_events`)와 턴 문맥 조립
    (`turn.context.build_turn_context`)이 정확히 그랬고, 요청 하나가 사건
    전체를 두 번 파싱했다. 사건 수가 세션 길이에 비례하고 브라우저 넷이
    1.5초마다 폴링하므로, 이 중복은 세션이 길어질수록 그대로 커진다.

    접는 로직 자체는 `rules_core.reducer.fold` 하나뿐이다 — 두 번째 재구성
    경로를 만드는 함수가 아니라, 같은 `fold`에 읽기를 한 번만 시키는
    입구다(`rebuild_state`도 이 함수를 통해 접는다).
    """
    pairs = ((event.event_type, event.model_dump()) for event in events)
    return fold(session_id, pairs)


def rebuild_state(store: EventStore, session_id: str) -> GameState:
    """기록을 처음부터 끝까지 읽어 상태를 재구성한다. 중간 저장을 쓰지 않는다 (D-08)."""
    return rebuild_state_from_events(session_id, store.read_events(session_id))
