"""옛 판으로 쓰인 실기록이 판 6 코드로도 예외 없이 읽히는지 못박는다
(10-01 Task 3, SAFE-01/TEST-03의 회귀 방지 그물).

**CONTEXT.md·RESEARCH.md·VALIDATION.md의 "판 5, 895건" 서술은 실제 파일과
어긋난다.** `.gptrpg/events.db`의 895건은 전부 `schema_version = 2`이고,
판 5로 기록된 것은 `.gptrpg/uat9.db`(221건, 세션 넷)다. 이 시험은 **두
파일 다** 돈다.

`tests/test_event_log.py`의 `test_real_events_db_replay_smoke_test_folds_without_exception`
(08-01 Task 3)이 이미 세운 관례 — **복제본만 열고 원본은 절대 열지 않는다**
(`shutil.copy`) — 를 그대로 따른다. 이 파일은 그 스모크를 대체하지 않고,
① `.gptrpg/uat9.db`(판 5)까지 넓히고 ② 판 6 양방향 확인(새로 쓴
`safety_flagged` 사건도 같은 경로로 접힌다)을 더한다.
"""

import shutil
import sqlite3
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from gptrpg.event_log.schema import SafetyFlagged, utc_now_iso
from gptrpg.event_log.store import EventStore
from gptrpg.session_actor.projection import rebuild_state_from_events

_REAL_EVENTS_DB = PROJECT_ROOT / ".gptrpg" / "events.db"
_REAL_UAT9_DB = PROJECT_ROOT / ".gptrpg" / "uat9.db"


def _session_ids(db_path: Path) -> list[str]:
    """복제본을 읽기 전용으로 열어 그 파일에 실제로 있는 세션 id 목록을 뽑는다.

    `EventStore`에는 세션 목록 조회가 없다(세션 하나를 안다고 가정하고
    설계된 API) — 이 시험은 어떤 세션이 몇 개 있는지 미리 모르는 채로
    "파일에 있는 전부"를 돌아야 하므로, 딱 이 목적만을 위해 sqlite3를 직접
    한 번 연다(쓰지 않는다).
    """
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT DISTINCT session_id FROM events ORDER BY session_id").fetchall()
    finally:
        conn.close()
    return [row[0] for row in rows]


# ---------------------------------------------------------------------------
# ① `.gptrpg/events.db` — 판 2 실기록 895건 (session1 하나)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _REAL_EVENTS_DB.is_file(),
    reason=".gptrpg/events.db가 이 체크아웃에 없다(gitignore 대상) — 있을 때만 스모크로 돈다",
)
def test_events_db_v2_records_fold_without_exception_under_schema_6(tmp_path):
    """`.gptrpg/events.db`의 세션1 기록(전부 `schema_version=2`, 895건)이
    판 6 코드로도 예외 없이 접힌다. 08-01 Task 3의 스모크와 같은 세션이지만
    `EVENT_SCHEMA_VERSION`이 그 사이 5->6으로 올랐으므로 이 계획이 다시
    확인한다(D-13 옛 판 해석 경로는 판이 바뀔 때마다 다시 못박아야 뜻이
    있다)."""
    copy_path = tmp_path / "events-copy.db"
    shutil.copy(_REAL_EVENTS_DB, copy_path)

    store = EventStore(copy_path)
    store.initialize()
    try:
        events = store.read_events("session1")
    finally:
        store.close()

    assert events, "복제본에 session1 기록이 있어야 이 스모크가 의미 있다"
    assert all(event.schema_version == 2 for event in events), (
        "이 파일의 실제 기록은 판 2다 — CONTEXT.md/RESEARCH.md/VALIDATION.md의 "
        "「판 5, 895건」 서술은 실제 파일과 어긋난다(10-01-PLAN.md 설계 판단 6)"
    )

    state = rebuild_state_from_events("session1", events)
    assert state.last_seq == events[-1].seq
    assert state.check_count > 0


@pytest.mark.skipif(
    not _REAL_EVENTS_DB.is_file(),
    reason=".gptrpg/events.db가 이 체크아웃에 없다(gitignore 대상) — 있을 때만 스모크로 돈다",
)
def test_events_db_has_no_safety_flagged_events_yet(tmp_path):
    """새 종류가 옛 기록엔 없으니 그냥 새 분기를 안 탈 뿐이라는 08-CONTEXT.md
    D-13의 호환 근거가 실제로 성립한다는 것을 확인한다."""
    copy_path = tmp_path / "events-copy.db"
    shutil.copy(_REAL_EVENTS_DB, copy_path)

    store = EventStore(copy_path)
    store.initialize()
    try:
        events = store.read_events("session1")
    finally:
        store.close()

    assert all(event.event_type != "safety_flagged" for event in events)


# ---------------------------------------------------------------------------
# ② `.gptrpg/uat9.db` — 판 5 실기록 221건 (세션 넷: 1·pacing5·uat9·uatweb)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _REAL_UAT9_DB.is_file(),
    reason=".gptrpg/uat9.db가 이 체크아웃에 없다(gitignore 대상) — 있을 때만 스모크로 돈다",
)
def test_uat9_db_v5_records_fold_without_exception_per_session(tmp_path):
    """`.gptrpg/uat9.db`의 판 5 기록(221건)을 세션별로 판 6 코드로 접는다.

    2026-08-13에 실제 파일을 열어 확인한 세션은 넷이다(`1`·`pacing5`·
    `uat9`·`uatweb`) — 10-01-PLAN.md는 "세션이 둘"이라 적었지만(pacing5·
    uatweb만 거론), 실제로는 그보다 많다. 이 시험은 그 서술을 믿지 않고
    **파일에 실제로 있는 세션 전부**를 `_session_ids`로 다시 뽑아 돈다.
    """
    copy_path = tmp_path / "uat9-copy.db"
    shutil.copy(_REAL_UAT9_DB, copy_path)

    session_ids = _session_ids(copy_path)
    assert session_ids, "복제본에 세션이 하나도 없으면 이 스모크가 의미 없다"

    store = EventStore(copy_path)
    store.initialize()
    try:
        total = 0
        for session_id in session_ids:
            events = store.read_events(session_id)
            assert events
            assert all(event.schema_version == 5 for event in events), session_id
            state = rebuild_state_from_events(session_id, events)
            assert state.last_seq == events[-1].seq
            total += len(events)
    finally:
        store.close()

    assert total == 221, "10-01-PLAN.md가 확인한 판 5 실기록 총량과 어긋난다"


@pytest.mark.skipif(
    not _REAL_UAT9_DB.is_file(),
    reason=".gptrpg/uat9.db가 이 체크아웃에 없다(gitignore 대상) — 있을 때만 스모크로 돈다",
)
def test_uat9_db_has_no_safety_flagged_events_yet(tmp_path):
    copy_path = tmp_path / "uat9-copy.db"
    shutil.copy(_REAL_UAT9_DB, copy_path)

    store = EventStore(copy_path)
    store.initialize()
    try:
        for session_id in _session_ids(copy_path):
            events = store.read_events(session_id)
            assert all(event.event_type != "safety_flagged" for event in events)
    finally:
        store.close()


# ---------------------------------------------------------------------------
# ③ 양방향 확인 — 판 6으로 새로 쓴 safety_flagged 사건도 같은 접기 경로가 돈다
# ---------------------------------------------------------------------------


def test_freshly_written_schema_6_safety_flagged_event_folds_without_exception(tmp_path):
    """옛 기록이 새 코드에서 읽히는 것(위)과, 새 사건 종류가 접기 경로 자체를
    깨지 않는 것(이 시험) — 두 방향을 다 확인해야 판 6 전환이 끝난다."""
    store_path = tmp_path / "fresh.db"
    store = EventStore(store_path)
    store.initialize()
    try:
        event = SafetyFlagged(
            session_id="fresh-session",
            seq=0,
            schema_version=6,
            caused_by_seq=None,
            recorded_at=utc_now_iso(),
            event_type="safety_flagged",
            source="narration",
            reason="think_block",
            disposition="blocked",
            matched_len=0,
            subject_len=12,
            chunk_index=0,
        )
        store.append(event)
        events = store.read_events("fresh-session")
    finally:
        store.close()

    assert len(events) == 1
    state = rebuild_state_from_events("fresh-session", events)
    assert state.last_seq == 0
