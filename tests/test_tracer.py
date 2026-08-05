"""명령줄부터 사건 기록까지, 다시 사건 기록부터 명령줄까지 한 경로를 끝까지 도는 통합 테스트.

이 파일이 통과하면 규칙 코어·사건 기록·세션 액터·CLI 네 층이 실제로 맞물린다는
증거가 된다 (01-02 Task 2, tracer).
"""

from gptrpg.cli.main import main
from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.grading import grade_for_total
from gptrpg.rules_core.resolution import Modifier, resolve_2d6


class _FixedRoller:
    """테스트용 고정 눈 도구. rules_core는 Protocol만 알므로 즉석 객체가 그대로 통과한다."""

    def __init__(self, values: list[int]) -> None:
        self._values = iter(values)

    def roll_d6(self) -> int:
        return next(self._values)


def test_submit_twice_appends_two_events_with_sequential_seq(tmp_db_path):
    db = str(tmp_db_path)
    exit_code_1 = main(
        ["submit", "--db", db, "--session", "s1", "roll", "--move", "문을 부순다"]
    )
    exit_code_2 = main(
        ["submit", "--db", db, "--session", "s1", "roll", "--move", "문을 부순다"]
    )
    assert exit_code_1 == 0
    assert exit_code_2 == 0

    store = EventStore(db)
    store.initialize()
    try:
        events = store.read_events("s1")
    finally:
        store.close()

    assert len(events) == 2
    assert [event.seq for event in events] == [0, 1]
    assert all(event.event_type == "check_resolved" for event in events)


def test_replay_shows_check_count_and_last_grade(tmp_db_path, capsys):
    db = str(tmp_db_path)
    main(["submit", "--db", db, "--session", "s1", "roll", "--move", "문을 부순다"])
    capsys.readouterr()  # submit 단계의 출력은 버린다

    exit_code = main(["replay", "--db", db, "--session", "s1"])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "판정 수" in output
    assert "1" in output
    assert "마지막 판정 등급" in output


def test_replay_output_is_identical_across_two_runs(tmp_db_path, capsys):
    db = str(tmp_db_path)
    main(["submit", "--db", db, "--session", "s1", "roll", "--move", "문을 부순다"])
    main(["submit", "--db", db, "--session", "s1", "roll", "--move", "위협에 맞선다"])
    capsys.readouterr()

    main(["replay", "--db", db, "--session", "s1"])
    first_output = capsys.readouterr().out
    main(["replay", "--db", db, "--session", "s1"])
    second_output = capsys.readouterr().out

    assert first_output == second_output


def test_stored_check_event_has_full_calculation_detail(tmp_db_path):
    db = str(tmp_db_path)
    main(
        [
            "submit",
            "--db",
            db,
            "--session",
            "s1",
            "roll",
            "--move",
            "문을 부순다",
            "--modifier",
            "flat:2:힘",
        ]
    )

    store = EventStore(db)
    store.initialize()
    try:
        events = store.read_events("s1")
    finally:
        store.close()

    assert len(events) == 1
    event = events[0]
    assert len(event.rolls) == 2
    assert all(1 <= roll <= 6 for roll in event.rolls)
    assert event.target is not None
    assert event.grade in ("strong_hit", "weak_hit", "miss")
    assert len(event.modifiers) == 1
    assert event.modifiers[0].type == "flat"
    assert event.modifiers[0].value == 2
    assert event.modifiers[0].source == "힘"


def test_resolve_2d6_total_and_grade_are_internally_consistent():
    roller = _FixedRoller([4, 5])
    modifiers = [Modifier(type="flat", value=1, source="테스트")]
    target = 10

    outcome = resolve_2d6(roller, "문을 부순다", modifiers, target)

    assert outcome.total == sum(outcome.rolls) + 1
    assert outcome.grade == grade_for_total(outcome.total, target)
