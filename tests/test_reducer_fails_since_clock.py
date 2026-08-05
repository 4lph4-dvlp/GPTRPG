"""초기화되는 실패 카운터(`GameState.fails_since_clock`)가 누적 실패 수
(`failure_count`)와 서로 다른 값이며 둘 다 남는다는 것을 못 박는다 (RIG-04).

`tests/test_reducer_failure_count.py`와 같은 결로 쓴다 — payload 사전을
손으로 만들고 `initial_state` + `apply_event`/`fold`를 바로 부른다. 저장소도
액터도 asyncio도 쓰지 않는다.
"""

from gptrpg.rules_core.reducer import apply_event, fold, initial_state


def _v2_check_resolved(seq: int, grade: str, counts_as_failure: bool) -> dict:
    """판 2 페이로드 — `counts_as_failure` 칸이 실제로 존재하는 새 기록."""
    return {
        "seq": seq,
        "grade": grade,
        "schema_version": 2,
        "counts_as_failure": counts_as_failure,
    }


def _v1_check_resolved(seq: int, grade: str) -> dict:
    """판 1 페이로드 — `counts_as_failure` 칸이 아예 없는 옛 기록."""
    return {"seq": seq, "grade": grade, "schema_version": 1}


def _clock_advanced(seq: int, segment_index: int, trigger: str) -> dict:
    return {"seq": seq, "segment_index": segment_index, "trigger": trigger}


def test_one_failure_increments_both_fails_since_clock_and_failure_count():
    """실패 판정 하나가 접히면 fails_since_clock과 failure_count가 함께 1 오른다."""
    state = apply_event(
        initial_state("s1"), "check_resolved", _v2_check_resolved(0, "miss", True)
    )
    assert state.fails_since_clock == 1
    assert state.failure_count == 1


def test_three_failures_both_counters_reach_three():
    """실패 세 번 뒤 fails_since_clock == 3, failure_count == 3."""
    pairs = [
        ("check_resolved", _v2_check_resolved(i, "miss", True)) for i in range(3)
    ]
    state = fold("s1", pairs)
    assert state.fails_since_clock == 3
    assert state.failure_count == 3


def test_clock_advanced_resets_fails_since_clock_but_not_failure_count():
    """시계 진행 뒤 fails_since_clock == 0이면서 동시에 failure_count == 3임을
    한 시험 안에서 함께 단언한다 — 두 값이 다른 것임을 증명한다."""
    pairs = [
        ("check_resolved", _v2_check_resolved(i, "miss", True)) for i in range(3)
    ] + [("clock_advanced", _clock_advanced(3, 1, "fail_counter"))]
    state = fold("s1", pairs)
    assert state.fails_since_clock == 0
    assert state.failure_count == 3


def test_reset_happens_regardless_of_trigger_value():
    """초기화는 trigger 값과 무관하다 — condition이나 ai_choice로 돌아도 똑같이 0이 된다."""
    for trigger in ("condition", "ai_choice"):
        pairs = [
            ("check_resolved", _v2_check_resolved(0, "miss", True)),
            ("clock_advanced", _clock_advanced(1, 1, trigger)),
        ]
        state = fold("s1", pairs)
        assert state.fails_since_clock == 0, f"trigger={trigger!r}에서 초기화되지 않았다"


def test_success_check_does_not_increment_either_counter():
    """성공 판정(counts_as_failure=False)은 두 칸 중 어느 것도 올리지 않는다."""
    state = apply_event(
        initial_state("s1"), "check_resolved", _v2_check_resolved(0, "success", False)
    )
    assert state.fails_since_clock == 0
    assert state.failure_count == 0


def test_v1_legacy_record_also_increments_fails_since_clock():
    """판 1 기록(schema_version 없음, grade == "miss")도 fails_since_clock을 올린다 —
    옛 기록 해석 경로가 두 칸에 똑같이 걸린다."""
    state = apply_event(
        initial_state("s1"), "check_resolved", _v1_check_resolved(0, "miss")
    )
    assert state.fails_since_clock == 1
    assert state.failure_count == 1

    hit_state = apply_event(
        initial_state("s1"), "check_resolved", _v1_check_resolved(0, "strong_hit")
    )
    assert hit_state.fails_since_clock == 0
    assert hit_state.failure_count == 0


def test_other_four_event_types_do_not_touch_fails_since_clock():
    """action_declared/action_confirmed/narration_appended/ai_invoked는
    fails_since_clock을 건드리지 않는다."""
    pairs = [
        ("check_resolved", _v2_check_resolved(0, "miss", True)),
        ("action_declared", {"seq": 1, "player_id": "p1", "raw_text": "문을 두드린다"}),
        ("action_confirmed", {"seq": 2}),
        ("narration_appended", {"seq": 3, "text": "문이 열린다.", "chunk_index": 0}),
        (
            "ai_invoked",
            {
                "seq": 4,
                "prompt_tokens": 10,
                "completion_tokens": 5,
            },
        ),
    ]
    state = fold("s1", pairs)
    assert state.fails_since_clock == 1
    assert state.failure_count == 1
