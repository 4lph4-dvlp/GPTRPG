"""시나리오 데이터가 데이터에서 프롬프트 텍스트까지 한 경로로 통하는지 확인한다.

가짜 제공자는 필요 없다 — `build_turn_context`를 직접 불러 프롬프트 조립까지만
확인한다.

**09-02부터 이 파일은 상황판단(`build_situation_prompt`) 프롬프트에 대한
검사다.** 서술이 아니다 — 서술(`build_gm_prompt`)의 `system`에는 시나리오
원문이 없다는 **정반대** 검사는 `tests/test_narration_isolation.py`가 한다.
두 파일이 서로를 가리킨다: 여기서 시나리오 내용이 "있다"고 증명하는 자리를
찾으면 `test_narration_isolation.py`에서 "없다"는 짝을 확인할 것.
"""

from gptrpg.agents import prompt_assembly
from gptrpg.event_log.schema import (
    CheckResolved,
    ClockAdvanced,
    EVENT_SCHEMA_VERSION,
    utc_now_iso,
)
from gptrpg.event_log.store import EventStore
from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_LIKE_ID
from gptrpg.rulebooks.threat_clocks import M0_THREAT_CLOCK, THREAT_CAST
from gptrpg.session_actor.projection import rebuild_state
from gptrpg.turn.context import build_turn_context


def _advance_clock(store: EventStore, session_id: str, segment_index: int) -> None:
    """`clock_advanced` 사건 하나를 순번대로 직접 append한다 (`test_web_events.py`의
    "저장소에 직접 append해서 준비한다" 관례와 같다)."""
    store.append(
        ClockAdvanced(
            event_type="clock_advanced",
            clock_id="threat",
            segment_index=segment_index,
            trigger="fail_counter",
            session_id=session_id,
            seq=store.next_seq(session_id),
            schema_version=EVENT_SCHEMA_VERSION,
            recorded_at=utc_now_iso(),
        )
    )


def _situation_system(store: EventStore, session_id: str) -> str:
    """`build_situation_prompt`가 만드는 `system` 두 조각을 이어 붙인 문자열.

    상황판단은 시나리오 원문(정체·원하는 것·파국·칸 설명)을 볼 자격이 있는
    유일한 역할이다 — 아래 시험들이 그 사실을 실제 데이터로 증명한다.
    """
    ctx = build_turn_context(store, session_id, DUNGEONWORLD_LIKE_ID)
    system, _messages = prompt_assembly.build_situation_prompt(
        rulebook_display_name="던전월드 계열",
        ctx=ctx,
        check_summary="hack_and_slash 판정 결과 miss (목표 10)",
    )
    return "\n".join(block["text"] for block in system)


def _resolve_failing_check(store: EventStore, session_id: str) -> None:
    """`counts_as_failure=True`인 `check_resolved` 사건 하나를 직접 append한다."""
    store.append(
        CheckResolved(
            event_type="check_resolved",
            move="테스트 판정",
            rolls=[1, 1],
            modifiers=[],
            target=10,
            grade="miss",
            counts_as_failure=True,
            person_id="p1",
            character_id="bram",
            session_id=session_id,
            seq=store.next_seq(session_id),
            schema_version=EVENT_SCHEMA_VERSION,
            recorded_at=utc_now_iso(),
        )
    )


def test_scenario_name_identity_wants_appear_in_situation_system(tmp_db_path):
    """이 검사는 이제 상황판단 프롬프트에 대한 것이다 — 서술 프롬프트에 대한
    같은 검사는 `tests/test_narration_isolation.py`에서 정반대(포함하지
    않는다)를 단언한다."""
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        system = _situation_system(store, "s1")
    finally:
        store.close()

    assert M0_THREAT_CLOCK.name in system
    assert M0_THREAT_CLOCK.identity in system
    assert M0_THREAT_CLOCK.wants in system


def test_situation_system_is_byte_identical_across_two_calls_in_same_segment(tmp_db_path):
    """캐싱 안정성 — 같은 칸에서 두 번 호출해도 `system`이 바이트 단위로 같다.
    턴마다 달라지는 사실 묶음은 `messages`에만 실린다는 증거다(DP-05)."""
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        first = _situation_system(store, "s1")
        second = _situation_system(store, "s1")
    finally:
        store.close()

    assert first == second


def test_situation_system_changes_after_clock_advances_a_segment(tmp_db_path):
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        before = _situation_system(store, "s1")
        _advance_clock(store, "s1", segment_index=1)
        after = _situation_system(store, "s1")
    finally:
        store.close()

    assert before != after


def test_build_turn_context_scene_entities_is_threat_cast(tmp_db_path):
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        ctx = build_turn_context(store, "s1", DUNGEONWORLD_LIKE_ID)
    finally:
        store.close()

    assert ctx.scene_entities == THREAT_CAST


# ---------------------------------------------------------------------------
# Task 2: 시나리오 형태 단언 — 캐스트 다양성, 칸 넷, 파국
# ---------------------------------------------------------------------------


def test_cast_has_three_to_four_members_with_combat_and_non_combat():
    combat = [e for e in THREAT_CAST if e.stats]
    talk = [e for e in THREAT_CAST if not e.stats]
    assert 3 <= len(THREAT_CAST) <= 4
    assert len(combat) >= 1
    assert len(talk) >= 2


def test_all_four_segments_are_non_empty_and_reasonably_long():
    assert len(M0_THREAT_CLOCK.segment_descriptions) == 4
    assert all(desc.strip() for desc in M0_THREAT_CLOCK.segment_descriptions)
    assert all(len(desc) >= 20 for desc in M0_THREAT_CLOCK.segment_descriptions)


def test_catastrophe_is_non_empty():
    assert len(M0_THREAT_CLOCK.catastrophe) >= 10


# ---------------------------------------------------------------------------
# Task 3 ②: 관측 지표(clock_advances/fails_since_clock)가 프롬프트로 새지
# 않는다 — T-05-02, H2/MEAS-03 계측 무결성 경계.
# ---------------------------------------------------------------------------


def test_situation_system_does_not_leak_accumulated_failure_count(tmp_db_path):
    """실패가 쌓인 상태(`fails_since_clock` != 0)에서 조립해도 그 숫자가
    상황판단 `system`에 나타나지 않는다 — 같은 칸 안에서는 실패 유무와 무관하게
    byte-identical해야 한다."""
    store = EventStore(tmp_db_path)
    store.initialize()
    try:
        before = _situation_system(store, "s1")
        _resolve_failing_check(store, "s1")
        _resolve_failing_check(store, "s1")
        state = rebuild_state(store, "s1")
        after = _situation_system(store, "s1")
    finally:
        store.close()

    assert state.fails_since_clock > 0, "테스트 전제 확인: 실패가 실제로 쌓여야 한다"
    assert before == after
