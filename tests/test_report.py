"""`session_actor.report`의 `build_report`/`write_report`/`require_safe_session_id`를
`<behavior>` 여덟 항목(Task 1)과 CLI `gptrpg report` 하위 명령(Task 2)으로 못 박는다.

픽스처 값이 있는 것(`fake_session_log`)은 그 값을 그대로 단언하고, 경계
(시계 0회 / 실패 0회)는 `initial_state` + `apply_event`로 작은 상태를 직접
만든다 (`tests/test_reducer_failure_count.py`의 순수 함수 시험 방식을 따른다).
파일 쓰기 시험은 `tmp_path`에 쓴다.
"""

import json

import pytest

from gptrpg.cli.main import main
from gptrpg.event_log.schema import EVENT_SCHEMA_VERSION, ActionDeclared, CheckResolved, utc_now_iso
from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.reducer import fold, initial_state
from gptrpg.session_actor.report import (
    REPORT_FIELD_NAMES,
    UnsafeSessionId,
    build_report,
    require_safe_session_id,
    write_report,
)


def _rebuild_fake_state(fake_session_log):
    """`fake_session_log`가 저장소에서 다시 읽어 온 사건들을 리듀서로 접는다.

    `session_actor.projection.rebuild_state`가 하는 것과 정확히 같은 변환
    (`event.event_type`, `event.model_dump()` 짝)을 시험 안에서 직접 한다 —
    이 시험은 `EventStore`를 새로 열지 않고 픽스처가 이미 읽어 온 사건
    목록만 쓴다.
    """
    pairs = ((event.event_type, event.model_dump()) for event in fake_session_log.events)
    return fold(fake_session_log.session_id, pairs)


# ---------------------------------------------------------------------------
# behavior 1~2: fake_session_log 기준 정확한 숫자 (MEAS-01 / MEAS-03)
# ---------------------------------------------------------------------------


def test_build_report_matches_fake_session_log_counts(fake_session_log):
    state = _rebuild_fake_state(fake_session_log)
    report = build_report(state)

    assert report["total_tokens"] == 330
    assert report["turn_count"] == 3
    assert report["failure_count"] == 2
    assert report["clock_advances"] == 1
    assert report["event_count"] == 14


def test_build_report_failure_to_clock_ratio_matches_fake_session_log(fake_session_log):
    state = _rebuild_fake_state(fake_session_log)
    report = build_report(state)

    assert report["failure_to_clock_ratio"] == 2.0


# ---------------------------------------------------------------------------
# behavior 3~4: 0으로 나누는 자리가 없다 (경계값, 직접 접은 작은 상태)
# ---------------------------------------------------------------------------


def _check_resolved(seq: int, counts_as_failure: bool) -> dict:
    return {
        "seq": seq,
        "grade": "miss" if counts_as_failure else "strong_hit",
        "schema_version": 2,
        "counts_as_failure": counts_as_failure,
    }


def _clock_advanced(seq: int, segment_index: int) -> dict:
    return {"seq": seq, "segment_index": segment_index}


def test_failure_to_clock_ratio_is_none_when_clock_never_advanced():
    """시계 진행이 0회이면 실패가 있어도 비율은 None이다 (0이나 무한대가 아니다)."""
    pairs = [
        ("check_resolved", _check_resolved(0, True)),
        ("check_resolved", _check_resolved(1, True)),
    ]
    state = fold("s-no-clock", pairs)
    report = build_report(state)

    assert state.clock_advances == 0
    assert report["failure_to_clock_ratio"] is None


def test_failure_to_clock_ratio_is_zero_when_no_failures_but_clock_advanced():
    """실패가 0회이고 시계가 2번 돈 상태에서도 비율은 0.0으로 정상 계산된다."""
    pairs = [
        ("clock_advanced", _clock_advanced(0, 1)),
        ("clock_advanced", _clock_advanced(1, 2)),
    ]
    state = fold("s-no-failure", pairs)
    report = build_report(state)

    assert report["failure_to_clock_ratio"] == 0.0


# ---------------------------------------------------------------------------
# behavior 5: 열쇠 집합이 REPORT_FIELD_NAMES와 정확히 같다
# ---------------------------------------------------------------------------


def test_build_report_keys_match_report_field_names(fake_session_log):
    state = _rebuild_fake_state(fake_session_log)
    report = build_report(state)

    assert set(report.keys()) == REPORT_FIELD_NAMES


# ---------------------------------------------------------------------------
# behavior 6: generated_at을 직접 넘기면 그대로 들어가고 재현 가능하다
# ---------------------------------------------------------------------------


def test_build_report_generated_at_is_reproducible_when_passed_explicitly(fake_session_log):
    state = _rebuild_fake_state(fake_session_log)

    report_1 = build_report(state, generated_at="2026-01-01T00:00:00.000Z")
    report_2 = build_report(state, generated_at="2026-01-01T00:00:00.000Z")

    assert report_1["generated_at"] == "2026-01-01T00:00:00.000Z"
    assert report_1 == report_2


# ---------------------------------------------------------------------------
# behavior 7: write_report가 만든 파일은 한글이 이스케이프되지 않는다
# ---------------------------------------------------------------------------


def test_write_report_file_is_utf8_and_korean_not_escaped(tmp_path, fake_session_log):
    state = _rebuild_fake_state(fake_session_log)

    path = write_report(state, base_dir=tmp_path, generated_at="한글 이스케이프 확인용 시각")

    raw_text = path.read_text(encoding="utf-8")
    assert "한글 이스케이프 확인용 시각" in raw_text
    assert "\\u" not in raw_text

    loaded = json.loads(raw_text)
    assert loaded["generated_at"] == "한글 이스케이프 확인용 시각"
    assert loaded["total_tokens"] == 330


# ---------------------------------------------------------------------------
# behavior 8: 허용 범위를 벗어난 세션 식별자는 파일을 쓰기 전에 거절된다
# ---------------------------------------------------------------------------


def test_write_report_rejects_unsafe_session_id_before_writing_any_file(tmp_path):
    state = initial_state("bad/session id!")
    out_dir = tmp_path / "reports"

    with pytest.raises(UnsafeSessionId):
        write_report(state, base_dir=out_dir)

    assert not out_dir.exists()


def test_require_safe_session_id_accepts_allowed_characters():
    assert require_safe_session_id("fake-session-01") == "fake-session-01"


def test_require_safe_session_id_rejects_disallowed_characters():
    with pytest.raises(UnsafeSessionId):
        require_safe_session_id("bad/id")


# ---------------------------------------------------------------------------
# Task 2: `gptrpg report` — 조회와 저장이 한 번에 일어난다 (D-44)
# ---------------------------------------------------------------------------


def test_cli_report_prints_totals_and_ratio(tmp_db_path, fake_session_log, tmp_path, capsys):
    out_dir = tmp_path / "reports"

    exit_code = main(
        [
            "report",
            "--db",
            str(tmp_db_path),
            "--session",
            fake_session_log.session_id,
            "--out-dir",
            str(out_dir),
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "토큰 합계: 330" in captured.out
    assert "실패 대비 시계 진행 비율: 2.0" in captured.out


def test_cli_report_writes_json_file_with_matching_total_tokens(
    tmp_db_path, fake_session_log, tmp_path
):
    out_dir = tmp_path / "reports"

    exit_code = main(
        [
            "report",
            "--db",
            str(tmp_db_path),
            "--session",
            fake_session_log.session_id,
            "--out-dir",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    report_path = out_dir / f"{fake_session_log.session_id}.json"
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["total_tokens"] == 330


def test_cli_report_prints_placeholder_when_clock_never_advanced(tmp_db_path, tmp_path, capsys):
    session_id = "no-clock-session"
    store = EventStore(tmp_db_path)
    store.initialize()
    store.append(
        ActionDeclared(
            event_type="action_declared",
            player_id="p1",
            raw_text="문을 두드린다",
            session_id=session_id,
            seq=0,
            schema_version=EVENT_SCHEMA_VERSION,
            recorded_at=utc_now_iso(),
            caused_by_seq=None,
        )
    )
    store.append(
        CheckResolved(
            event_type="check_resolved",
            move="knock",
            rolls=[2, 3],
            modifiers=[],
            target=10,
            grade="miss",
            counts_as_failure=True,
            session_id=session_id,
            seq=1,
            schema_version=EVENT_SCHEMA_VERSION,
            recorded_at=utc_now_iso(),
            caused_by_seq=0,
        )
    )
    store.close()

    out_dir = tmp_path / "reports"
    exit_code = main(
        ["report", "--db", str(tmp_db_path), "--session", session_id, "--out-dir", str(out_dir)]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "시계가 한 번도 진행되지 않음" in captured.out


def test_cli_report_rejects_unsafe_session_id(tmp_db_path, tmp_path, capsys):
    out_dir = tmp_path / "reports"
    exit_code = main(
        ["report", "--db", str(tmp_db_path), "--session", "bad/id!", "--out-dir", str(out_dir)]
    )

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "오류" in captured.err
