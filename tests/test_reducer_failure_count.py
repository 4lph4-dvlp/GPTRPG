"""실패 집계(`GameState.failure_count`)가 등급 이름이 아니라 룰북이 선언한
`counts_as_failure` 신호로 계산됨을 못 박는다.

셋째 테스트(이름은 실패인데 신호가 false)가 핵심이다 — 리듀서가 더 이상
등급 이름 문자열을 비교하지 않는다는 결정적 증거다. `apply_event`/`fold`를
직접 부르는 단위 테스트로 충분하다(저장소를 거칠 필요 없다) —
`tests/test_event_log.py`의 fold 테스트가 쓰는 (event_type, payload) 짝
만드는 방식을 따른다.
"""

from gptrpg.rules_core.reducer import apply_event, fold, initial_state
from gptrpg.rulebooks import RULEBOOKS


def _v2_check_resolved(seq: int, grade: str, counts_as_failure: bool) -> dict:
    """판 2 페이로드 — `counts_as_failure` 칸이 실제로 존재하는 새 기록."""
    return {
        "seq": seq,
        "grade": grade,
        "schema_version": 2,
        "counts_as_failure": counts_as_failure,
    }


def _v1_check_resolved(seq: int, grade: str) -> dict:
    """판 1 페이로드 — `counts_as_failure` 칸이 아예 없는 옛 기록을 실제로 재현한다.

    당시엔 룰북이 하나뿐이었으므로 등급 이름이 곧 실패 여부였다(D-12).
    """
    return {"seq": seq, "grade": grade, "schema_version": 1}


def test_v2_openquest_failure_grade_with_counts_as_failure_true_increments():
    """판 2 페이로드에 counts_as_failure=True, grade가 OpenQuest 실패 등급
    이름("failure")이면 failure_count가 1 는다."""
    state = apply_event(
        initial_state("s1"), "check_resolved", _v2_check_resolved(0, "failure", True)
    )
    assert state.failure_count == 1, "OpenQuest 실패 등급(counts_as_failure=True)인데 세어지지 않았다"


def test_v2_dungeonworld_miss_grade_with_counts_as_failure_true_increments():
    """판 2 페이로드에 counts_as_failure=True, grade가 던전월드 실패 등급
    이름("miss")이어도 1 는다."""
    state = apply_event(
        initial_state("s1"), "check_resolved", _v2_check_resolved(0, "miss", True)
    )
    assert state.failure_count == 1, "던전월드 실패 등급(counts_as_failure=True)인데 세어지지 않았다"


def test_v2_miss_grade_with_counts_as_failure_false_does_not_increment():
    """판 2 페이로드에 counts_as_failure=False, grade가 던전월드 실패 등급
    이름("miss")이면 failure_count가 늘지 않는다.

    이것이 결정적 증거다 — 리듀서가 등급 이름("miss")이 아니라 신호
    (counts_as_failure)로만 판단한다는 것을 이 테스트 하나가 증명한다.
    등급 이름 비교로 되돌아가면 이 테스트가 즉시 빨간불을 켠다.
    """
    state = apply_event(
        initial_state("s1"), "check_resolved", _v2_check_resolved(0, "miss", False)
    )
    assert state.failure_count == 0, (
        "등급 이름이 'miss'라는 이유만으로 세어졌다 — 리듀서가 다시 이름 비교로 "
        "돌아갔다는 신호다. counts_as_failure 신호만 읽어야 한다"
    )


def test_v1_payload_without_counts_as_failure_field_uses_legacy_grade_name_rule():
    """schema_version=1이고 counts_as_failure 칸이 아예 없는 페이로드를 접으면
    판 1 규칙(등급 이름 == "miss")대로 세어진다 (D-12 옛 판 해석 경로)."""
    miss_state = apply_event(
        initial_state("s1"), "check_resolved", _v1_check_resolved(0, "miss")
    )
    assert miss_state.failure_count == 1, "판 1 기록에서 'miss'가 실패로 세어지지 않았다"

    hit_state = apply_event(
        initial_state("s1"), "check_resolved", _v1_check_resolved(0, "strong_hit")
    )
    assert hit_state.failure_count == 0, "판 1 기록에서 'strong_hit'이 실패로 잘못 세어졌다"


def test_v1_and_v2_events_mixed_in_one_record_each_rule_applies_independently():
    """판 1 사건과 판 2 사건이 한 기록에 섞여 있어도 두 규칙이 각각 적용돼
    합계가 맞는다."""
    pairs = [
        ("check_resolved", _v1_check_resolved(0, "miss")),  # 판 1, 이름으로 실패 +1
        ("check_resolved", _v2_check_resolved(1, "miss", False)),  # 판 2, 신호 false -> +0
        ("check_resolved", _v2_check_resolved(2, "failure", True)),  # 판 2, 신호 true -> +1
        ("check_resolved", _v1_check_resolved(3, "strong_hit")),  # 판 1, 이름 아님 -> +0
    ]
    state = fold("s1", pairs)
    assert state.failure_count == 2, (
        f"판 1·판 2가 섞인 기록의 합계가 틀렸다: {state.failure_count} != 2"
    )
    assert state.check_count == 4


def test_all_registered_rulebooks_failure_band_count_matches_declared_counts_as_failure():
    """두 룰북의 선언된 등급 밴드 전부에 대해, counts_as_failure가 참인 밴드의
    수만큼만 failure_count가 는다 (밴드 목록을 순회하는 성질 테스트).

    세 번째 룰북이 RULEBOOKS에 들어와도 이 테스트는 코드 수정 없이 그대로
    적용된다 — 룰북마다 조건절을 하나씩 늘리는 회귀를 기계적으로 막는다.
    """
    for rulebook_id, rulebook in RULEBOOKS.items():
        pairs = [
            (
                "check_resolved",
                _v2_check_resolved(seq, band.name, band.counts_as_failure),
            )
            for seq, band in enumerate(rulebook.grade_bands)
        ]
        state = fold(f"s-{rulebook_id}", pairs)
        expected = sum(1 for band in rulebook.grade_bands if band.counts_as_failure)
        assert state.failure_count == expected, (
            f"{rulebook_id!r} 룰북: 선언된 밴드 중 counts_as_failure=True인 "
            f"밴드 수({expected})와 재구성된 failure_count({state.failure_count})가 다르다"
        )
