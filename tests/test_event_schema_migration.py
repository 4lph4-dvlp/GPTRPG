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

**⑤절(12-03-PLAN.md, TEST-04)이 이 파일 끝에 더해졌다.** ①②의 시험들은
`.gptrpg/*`가 gitignore 대상이라 CI에서 항상 건너뛰어지고, 그래서 "다음에는
CI가 잡는다"는 TEST-04의 목적이 지금까지 달성되지 않았다. ⑤절은
`tests/fixtures/session1_events.jsonl`(저장소에 커밋된 session1 895건
사본)을 읽어 건너뛰기 표시 없이 항상 도는 회귀 그물을 만든다 — ①②의 로컬 스모크는
그대로 남는다.
"""

import dataclasses
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from gptrpg.event_log.schema import (
    EVENT_SCHEMA_VERSION,
    ResourceChanged,
    SafetyFlagged,
    parse_event,
    utc_now_iso,
)
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


@pytest.mark.skipif(
    not _REAL_EVENTS_DB.is_file(),
    reason=".gptrpg/events.db가 이 체크아웃에 없다(gitignore 대상) — 있을 때만 스모크로 돈다",
)
def test_events_db_has_no_corrupted_glyph_reason_yet(tmp_path):
    """10-06이 더한 `corrupted_glyph` 사유값이 이 판 2 실기록에는 없다는 것을
    명시적으로 단언한다(10-06-PLAN.md 설계 판단 3) — 판 2에는 `safety_flagged`
    사건 자체가 없으므로(위 시험) 자명하지만, 사유값 하나를 새로 더할 때마다
    이 자명함을 다시 못박아 두는 것이 회귀를 잡는다."""
    copy_path = tmp_path / "events-copy.db"
    shutil.copy(_REAL_EVENTS_DB, copy_path)

    store = EventStore(copy_path)
    store.initialize()
    try:
        events = store.read_events("session1")
    finally:
        store.close()

    corrupted_glyph_events = [
        event
        for event in events
        if event.event_type == "safety_flagged" and event.reason == "corrupted_glyph"
    ]
    assert corrupted_glyph_events == []


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


@pytest.mark.skipif(
    not _REAL_UAT9_DB.is_file(),
    reason=".gptrpg/uat9.db가 이 체크아웃에 없다(gitignore 대상) — 있을 때만 스모크로 돈다",
)
def test_uat9_db_has_no_corrupted_glyph_reason_yet(tmp_path):
    """10-06이 더한 `corrupted_glyph` 사유값이 이 판 5 실기록 어느 세션에도
    없다는 것을 명시적으로 단언한다(10-06-PLAN.md 설계 판단 3)."""
    copy_path = tmp_path / "uat9-copy.db"
    shutil.copy(_REAL_UAT9_DB, copy_path)

    store = EventStore(copy_path)
    store.initialize()
    try:
        for session_id in _session_ids(copy_path):
            events = store.read_events(session_id)
            corrupted_glyph_events = [
                event
                for event in events
                if event.event_type == "safety_flagged" and event.reason == "corrupted_glyph"
            ]
            assert corrupted_glyph_events == [], session_id
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


def test_freshly_written_corrupted_glyph_safety_flagged_event_folds_without_exception(tmp_path):
    """새로 쓴 `corrupted_glyph` 사유값(10-06)도 판 6으로 기록되고 예외 없이
    접힌다 — 위 시험과 같은 모양이지만 `reason`·`disposition`이 다르다
    (깨진 글자는 `flagged`이지 `blocked`가 아니다, D-03)."""
    store_path = tmp_path / "fresh-corrupted.db"
    store = EventStore(store_path)
    store.initialize()
    try:
        event = SafetyFlagged(
            session_id="fresh-corrupted-session",
            seq=0,
            schema_version=6,
            caused_by_seq=None,
            recorded_at=utc_now_iso(),
            event_type="safety_flagged",
            source="narration",
            reason="corrupted_glyph",
            disposition="flagged",
            matched_len=2,
            subject_len=12,
            chunk_index=0,
        )
        store.append(event)
        events = store.read_events("fresh-corrupted-session")
    finally:
        store.close()

    assert len(events) == 1
    assert events[0].reason == "corrupted_glyph"
    assert events[0].disposition == "flagged"
    state = rebuild_state_from_events("fresh-corrupted-session", events)
    assert state.last_seq == 0


# ---------------------------------------------------------------------------
# ④ 판 못박기 — EVENT_SCHEMA_VERSION이 corrupted_glyph 하나로는 6에서 안 올랐다
# (10-06-PLAN.md 설계 판단 3). 판이 7인 것은 이후 11-06 rework가 올린 결과다.
# ---------------------------------------------------------------------------


def test_event_schema_version_was_not_bumped_for_corrupted_glyph_alone():
    """`corrupted_glyph` 사유값 하나를 더한 것(10-06) 자체는
    `EVENT_SCHEMA_VERSION`을 올리지 않았다 — `reason`은 쓰기 검증에서만
    쓰이고(`session_actor/actor.py`), `rules_core.reducer.py`의
    `safety_flagged` 분기는 `reason`을 아예 안 본다.

    **10-06 시점의 판은 6이었다.** 그 이후 두 번의 판 올리기(11-06 rework의
    `ActionClassified` -> 판 7, 12-01의 `ResourceChanged` -> 판 8)가
    `EVENT_SCHEMA_VERSION`을 여기까지 올렸다 — 이 시험은 `corrupted_glyph`
    하나로는 판이 안 올랐다는 그 시절 사실만 문서로 남긴다."""
    assert EVENT_SCHEMA_VERSION >= 7


def test_event_schema_version_is_eight():
    """판 8 못박기(Phase 12, D-05) — `ResourceChanged`가 사건 형식에 닿은
    현재 판이다. 누가 무심코 판을 또 올리거나 내리면 이 값이 바뀌어 이
    시험이 잡는다."""
    assert EVENT_SCHEMA_VERSION == 8


def _tuple_key_to_str(key: tuple) -> str:
    """튜플 딕셔너리 키를 JSON 객체 키 문자열로 바꾼다.

    **`scripts/export_session_fixture.py`의 같은 이름 함수와 반드시 같은 규칙이다**
    (`"::"`로 이어붙임) — 커밋된 `tests/fixtures/session1_expected_state.json`이
    바로 그 스크립트로 만들어졌으므로, 두 규칙이 갈리면 이 시험이 비교하는
    두 값의 키 모양 자체가 달라져 무의미해진다. import 대신 여기 다시 쓴
    이유는 `scripts/`가 설치된 패키지가 아니라 테스트 임포트 경로에 없기
    때문이다(12-03-PLAN.md Task 2 action ②가 허용한 대안).
    """
    return "::".join(str(part) for part in key)


def _json_safe(value):
    """`dataclasses.asdict()` 결과를 커밋된 JSON과 같은 모양으로 정규화한다.

    `scripts/export_session_fixture.py`의 같은 이름 함수와 동일한 규칙 —
    튜플 키를 가진 딕셔너리만 `_tuple_key_to_str`로 문자열화하고, 나머지
    구조는 그대로 보존한다.
    """
    if isinstance(value, dict):
        converted = {}
        for key, sub_value in value.items():
            if isinstance(key, tuple):
                key = _tuple_key_to_str(key)
            converted[key] = _json_safe(sub_value)
        return converted
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# ⑤ 커밋된 픽스처 — CI에서 실제로 도는 회귀 그물 (TEST-04)
#
# ①②의 시험들은 전부 `.gptrpg/*`가 gitignore 대상이라 CI에서 항상
# 건너뛰어졌고, 그래서 "다음에는 CI가 잡는다"는 TEST-04의 목적이 지금까지
# 달성되지 않았다. 이 절의 시험 넷은 `.gptrpg/events.db`가 아니라
# `tests/fixtures/session1_events.jsonl`(저장소에 커밋된 사본)을 읽으므로
# 건너뛰기 표시가 없다 — 로컬 파일 유무와 무관하게 항상 돈다(12-03-PLAN.md).
# ---------------------------------------------------------------------------

_FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
_SESSION1_EVENTS_JSONL = _FIXTURES_DIR / "session1_events.jsonl"
_SESSION1_EXPECTED_STATE_JSON = _FIXTURES_DIR / "session1_expected_state.json"


def _load_committed_session1_events() -> list:
    """커밋된 JSONL의 895줄을 순서대로 `parse_event`로 되돌린다."""
    lines = _SESSION1_EVENTS_JSONL.read_text(encoding="utf-8").splitlines()
    return [parse_event(line) for line in lines if line.strip()]


def test_committed_session1_fixture_has_895_events_all_schema_version_2():
    """커밋된 JSONL 895줄이 전부 `parse_event`로 예외 없이 사건 객체로
    되돌아온다 — 옛 판(2)으로 쓰인 895건이 지금 코드로 예외 없이 접힌다는
    확인의 첫 단계다."""
    events = _load_committed_session1_events()
    assert len(events) == 895
    assert all(event.schema_version == 2 for event in events)


def test_committed_session1_fixture_folds_to_expected_state(tmp_path):
    """커밋된 895건을 빈 `EventStore`에 새로 넣고 다시 읽어 접은 `GameState`가
    커밋된 기대 상태 JSON과 **모든 필드에서** 같다.

    이것이 이 절의 핵심 회귀 그물이다 — `.gptrpg/events.db`가 이 체크아웃에
    있든 없든, CI를 포함한 모든 환경에서 항상 실행된다(건너뛰기 표시 없음).
    """
    events = _load_committed_session1_events()

    store = EventStore(tmp_path / "session1-replay.db")
    store.initialize()
    try:
        for event in events:
            store.append(event)
        replayed_events = store.read_events("session1")
    finally:
        store.close()

    state = rebuild_state_from_events("session1", replayed_events)
    # `json.dumps`로 한 번 더 돌린다 — dict의 int 키(예: `confirm_to_declare`의
    # 순번)를 문자열로 정규화하는 것은 `json` 모듈 자체의 동작이고, 커밋된
    # 기대값 파일(`scripts/export_session_fixture.py`가 `json.dump`로 만듦)도
    # 이미 그 정규화를 거쳤다. `actual`도 같은 정규화를 거쳐야 「모든 필드에서
    # 같다」는 비교가 키 타입 차이(0 vs "0")로 인한 거짓 회귀를 만들지 않는다.
    actual = json.loads(json.dumps(_json_safe(dataclasses.asdict(state)), ensure_ascii=False))
    expected = json.loads(_SESSION1_EXPECTED_STATE_JSON.read_text(encoding="utf-8"))

    assert actual == expected, (
        "session1 895건의 재생 결과가 커밋된 기대 상태와 달라졌다 — "
        "사건 해석 규칙이 바뀌었다. 의도한 변경(계획 문서에 근거가 있는 "
        "변경)이면 tests/fixtures/README.md의 갱신 규칙을 따라 "
        "scripts/export_session_fixture.py를 다시 돌려 기대값을 갱신할 것. "
        "그렇지 않다면 이것은 회귀이므로 기대값이 아니라 코드를 고쳐야 한다."
    )


def test_committed_session1_fixture_has_no_resource_changed_events():
    """895건 안에 `resource_changed` 사건(판 8, 12-01이 신설)이 하나도
    없다는 것을 명시적으로 단언한다 — 기존
    `test_events_db_has_no_safety_flagged_events_yet`과 같은 모양이고,
    「새 종류가 늘 뿐이라 옛 기록에는 그 종류가 없다」는 하위 호환 근거를
    판 8에 대해 다시 못박는다."""
    events = _load_committed_session1_events()
    assert all(event.event_type != "resource_changed" for event in events)


def test_committed_session1_fixture_folds_deterministically_when_folded_twice():
    """같은 픽스처를 두 번 접은 결과가 같다 — `fold`가 부수효과 없는 순수
    함수라는 것을 이 픽스처로도 확인한다."""
    events = _load_committed_session1_events()

    store = EventStore(":memory:")
    store.initialize()
    try:
        for event in events:
            store.append(event)
        replayed_events = store.read_events("session1")
    finally:
        store.close()

    state_first = rebuild_state_from_events("session1", replayed_events)
    state_second = rebuild_state_from_events("session1", replayed_events)

    assert dataclasses.asdict(state_first) == dataclasses.asdict(state_second)


def test_freshly_written_schema_8_resource_changed_event_folds_without_exception(tmp_path):
    """새로 쓴 `resource_changed` 사건(판 8)이 접기 경로 자체를 깨지 않는다
    — 「옛 기록이 새 코드에서 읽힌다」와 「새 사건 종류가 접기 경로를 깨지
    않는다」 두 방향 중 후자를 확인한다(전자는 판 8 사건이 옛 실기록에 아예
    없으므로 자동으로 성립한다 — 늘어난 것이 「새 종류」일 뿐이다)."""
    store_path = tmp_path / "fresh-resource.db"
    store = EventStore(store_path)
    store.initialize()
    try:
        event = ResourceChanged(
            session_id="fresh-resource-session",
            seq=0,
            schema_version=8,
            caused_by_seq=None,
            recorded_at=utc_now_iso(),
            event_type="resource_changed",
            character_id="bram",
            changes=[
                {
                    "axis": "체력",
                    "operation": "delta",
                    "amount": -6,
                    "rolls": [],
                    "before": 20,
                    "after": 14,
                }
            ],
            category_id=None,
            source="outcome_list",
        )
        store.append(event)
        events = store.read_events("fresh-resource-session")
    finally:
        store.close()

    assert len(events) == 1
    state = rebuild_state_from_events("fresh-resource-session", events)
    assert state.last_seq == 0
    assert state.character_resource_ops[("bram", "체력")][0].amount == -6
