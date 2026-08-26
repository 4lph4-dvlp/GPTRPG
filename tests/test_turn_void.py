"""서사 실패 자동 롤백(`turn_voided`, 판 15, D-33/MEAS-02 보완) 시험.

63aef0c(「다시 시도」 단추, 같은 판정을 재사용해 서사만 다시 쓴다)의 전제가
틀렸다는 사용자의 정정 — 「다시 시도해 주세요」는 같은 쿼리를 다시 준다는
뜻이 아니다 — 이후, 서사가 끝내 실패하면 이 턴 전체(check_resolved가
커밋한 값 + 그 판정이 직접 돌린 clock_advanced)를 자동으로 되돌리는 것이
지금 설계다.

**두 결이 나뉜다:**
- 리듀서 단위 시험(`test_turn_voided_*`) — `apply_event`/`fold`를 손으로
  만든 payload로 직접 부른다. AI도 액터도 asyncio도 쓰지 않는다
  (`tests/test_reducer_fails_since_clock.py`와 같은 결).
- 액터 단위 시험(`test_actor_*`) — `SessionActor`에 `_FixedRoller`로 고정한
  눈을 먹여 실제 명령 사슬(`DeclareAction`→`ConfirmAction`→`ResolveCheck`→
  `VoidTurn`)을 돈다. **AI 제공자를 전혀 쓰지 않는다** — 서사 실패를
  흉내내는 대신, 서사가 실패했을 때 웹/CLI가 실제로 제출하는 그 명령
  (`VoidTurn`)을 똑같이 제출한다. 이 파일의 시험이 증명하는 것은 "이
  명령이 오면 상태가 정확히 되돌아간다"이지 "실제 제공자가 언제 서사를
  실패시키는가"가 아니다 — 그 자동 트리거 배선은
  `tests/test_web_actions.py::test_narration_failure_automatically_voids_the_whole_turn`이
  `FakeProvider`로 결정적으로 증명한다(이 파일은 그 시험이 못 미치는
  「시계 진행까지 있었던 턴을 되돌리면 정확한 값으로 돌아오는가」를
  결정적 주사위로 증명한다).
"""

import pytest

from gptrpg.event_log.store import EventStore
from gptrpg.rules_core.reducer import apply_event, fold, initial_state
from gptrpg.rules_core.resolution import Modifier
from gptrpg.session_actor.actor import (
    AUTO_ADVANCE_FAILURE_THRESHOLD,
    CommandRejected,
    ConfirmAction,
    DeclareAction,
    ResolveCheck,
    SessionActor,
    TurnAlreadyVoided,
    VoidTurn,
)
from gptrpg.session_actor.projection import rebuild_state


# ---------------------------------------------------------------------------
# 리듀서 단위 시험 — payload를 손으로 만든다.
# ---------------------------------------------------------------------------


def _check_resolved(seq: int, *, caused_by_seq: int, counts_as_failure: bool) -> dict:
    return {
        "seq": seq,
        "caused_by_seq": caused_by_seq,
        "grade": "miss" if counts_as_failure else "strong_hit",
        "schema_version": 2,
        "counts_as_failure": counts_as_failure,
    }


def _clock_advanced(seq: int, *, caused_by_seq: int | None, segment_index: int, trigger: str) -> dict:
    return {
        "seq": seq,
        "caused_by_seq": caused_by_seq,
        "segment_index": segment_index,
        "trigger": trigger,
    }


def _turn_voided(
    seq: int, *, caused_by_seq: int, declare_seq: int, counts_as_failure: bool, threshold: int = 3
) -> dict:
    return {
        "seq": seq,
        "caused_by_seq": caused_by_seq,
        "declare_seq": declare_seq,
        "counts_as_failure": counts_as_failure,
        "clock_fail_threshold": threshold,
    }


def test_turn_voided_undoes_check_count_and_failure_count():
    state = apply_event(initial_state("s1"), "check_resolved", _check_resolved(0, caused_by_seq=None, counts_as_failure=True))
    assert (state.check_count, state.failure_count) == (1, 1)

    state = apply_event(
        state, "turn_voided", _turn_voided(1, caused_by_seq=0, declare_seq=99, counts_as_failure=True)
    )
    assert (state.check_count, state.failure_count, state.fails_since_clock) == (0, 0, 0)
    assert 99 in state.voided_declare_seqs


def test_turn_voided_leaves_a_non_failing_check_uncounted_correctly():
    """counts_as_failure=False였던 판정을 되돌려도 failure_count는
    음수로 내려가지 않는다 — 애초에 세지 않았던 값을 또 안 뺀다."""
    state = apply_event(
        initial_state("s1"), "check_resolved", _check_resolved(0, caused_by_seq=None, counts_as_failure=False)
    )
    state = apply_event(
        state, "turn_voided", _turn_voided(1, caused_by_seq=0, declare_seq=99, counts_as_failure=False)
    )
    assert (state.check_count, state.failure_count, state.fails_since_clock) == (0, 0, 0)


def test_turn_voided_is_idempotent_when_the_same_declare_seq_folds_twice():
    """같은 declare_seq로 두 번째 turn_voided가 접혀도(사건 중복 기록을
    포함하는 방어적 상황) 카운터가 두 번 깎이지 않는다."""
    state = apply_event(initial_state("s1"), "check_resolved", _check_resolved(0, caused_by_seq=None, counts_as_failure=True))
    state = apply_event(
        state, "turn_voided", _turn_voided(1, caused_by_seq=0, declare_seq=99, counts_as_failure=True)
    )
    state = apply_event(
        state, "turn_voided", _turn_voided(2, caused_by_seq=0, declare_seq=99, counts_as_failure=True)
    )
    assert (state.check_count, state.failure_count) == (0, 0)


def test_turn_voided_reverses_the_clock_advance_it_directly_caused():
    """이 시험의 핵심 — 세 번째 실패가 시계를 돌렸을 때, 그 세 번째를
    되돌리면 시계도 함께 되돌아간다(선언 전 값과 정확히 같다)."""
    pairs = [
        ("check_resolved", _check_resolved(0, caused_by_seq=None, counts_as_failure=True)),
        ("check_resolved", _check_resolved(1, caused_by_seq=None, counts_as_failure=True)),
    ]
    before_third = fold("s1", pairs)
    assert (before_third.check_count, before_third.failure_count, before_third.fails_since_clock) == (2, 2, 2)
    assert before_third.clock_segment == 0

    pairs += [
        ("check_resolved", _check_resolved(2, caused_by_seq=None, counts_as_failure=True)),
        (
            "clock_advanced",
            _clock_advanced(3, caused_by_seq=2, segment_index=1, trigger="fail_counter"),
        ),
    ]
    after_third = fold("s1", pairs)
    assert (after_third.check_count, after_third.failure_count, after_third.fails_since_clock) == (3, 3, 0)
    assert after_third.clock_segment == 1
    assert after_third.clock_advances == 1

    pairs += [
        (
            "turn_voided",
            _turn_voided(4, caused_by_seq=2, declare_seq=42, counts_as_failure=True, threshold=3),
        )
    ]
    after_void = fold("s1", pairs)

    # 되돌린 뒤 값이 세 번째 판정을 하기 **전** 값과 정확히 같다.
    assert after_void.check_count == before_third.check_count
    assert after_void.failure_count == before_third.failure_count
    assert after_void.fails_since_clock == before_third.fails_since_clock
    assert after_void.clock_segment == before_third.clock_segment
    assert after_void.clock_advances == before_third.clock_advances
    assert 42 in after_void.voided_declare_seqs


def test_turn_voided_does_not_touch_the_clock_when_a_later_advance_already_superseded_it():
    """이 판정이 시계를 돌렸어도, 그 뒤에 **다른** 판정이 시계를 또
    돌렸다면(다른 플레이어의 실패 등) 되돌리기가 이미 지나간 재설정을
    건드리지 않는다 — 안전하게 되돌릴 수 없으면 손대지 않는다(문서화된
    결정, "Ordering" 항목)."""
    pairs = [
        ("check_resolved", _check_resolved(0, caused_by_seq=None, counts_as_failure=True)),
        ("check_resolved", _check_resolved(1, caused_by_seq=None, counts_as_failure=True)),
        ("check_resolved", _check_resolved(2, caused_by_seq=None, counts_as_failure=True)),
        (
            "clock_advanced",
            _clock_advanced(3, caused_by_seq=2, segment_index=1, trigger="fail_counter"),
        ),
        # 다른 판정 셋이 또 시계를 돌린다(예: 다른 플레이어) — 두 번째 진행.
        ("check_resolved", _check_resolved(4, caused_by_seq=None, counts_as_failure=True)),
        ("check_resolved", _check_resolved(5, caused_by_seq=None, counts_as_failure=True)),
        ("check_resolved", _check_resolved(6, caused_by_seq=None, counts_as_failure=True)),
        (
            "clock_advanced",
            _clock_advanced(7, caused_by_seq=6, segment_index=2, trigger="fail_counter"),
        ),
    ]
    before_void = fold("s1", pairs)
    assert before_void.clock_segment == 2
    assert before_void.clock_advances == 2

    # 이제 **첫 번째** 시계 진행을 일으켰던 판정(seq=2)을 되돌린다 — 그
    # 진행은 더 이상 가장 최근 진행이 아니다(seq=7이 더 나중이다).
    pairs_void = pairs + [
        (
            "turn_voided",
            _turn_voided(8, caused_by_seq=2, declare_seq=1, counts_as_failure=True, threshold=3),
        )
    ]
    after_void = fold("s1", pairs_void)

    # check_count/failure_count는 여전히 정확히 하나 줄어든다(누적값이라
    # 순서와 무관하게 뺄 수 있다) — 하지만 시계는 손대지 않는다(이미 그
    # 다음 진행이 새 기준을 잡았다).
    assert after_void.check_count == before_void.check_count - 1
    assert after_void.failure_count == before_void.failure_count - 1
    assert after_void.clock_segment == before_void.clock_segment
    assert after_void.clock_advances == before_void.clock_advances
    assert after_void.fails_since_clock == before_void.fails_since_clock


# ---------------------------------------------------------------------------
# 액터 단위 시험 — 실제 명령 사슬을 돈다. AI 제공자는 쓰지 않는다(위 모듈
# 도크스트링 참조 — 자동 트리거 배선은 `test_web_actions.py`가 증명한다).
# ---------------------------------------------------------------------------


class _FixedRoller:
    def __init__(self, values: list[int]) -> None:
        self._values = iter(values)

    def roll_d6(self) -> int:
        return next(self._values)


_FAILING_ROLL = [1, 1]  # 합계 2 -> miss (counts_as_failure=True), 2d6 target=10


def _make_actor(tmp_db_path, values: list[int]) -> tuple[EventStore, SessionActor]:
    store = EventStore(tmp_db_path)
    store.initialize()
    actor = SessionActor(store, "s1", _FixedRoller(values))
    actor.start()
    return store, actor


async def _declare_confirm_resolve(actor: SessionActor, *, player_id: str = "p1") -> tuple[int, int]:
    """DeclareAction -> ConfirmAction -> ResolveCheck를 순서대로 돈다 —
    `VoidTurn`이 요구하는 `confirmed_declares` 짝(declare_seq/resolve_seq)이
    실제로 존재해야 하므로, `test_session_actor_auto_advance.py`처럼
    `ResolveCheck`만 단독으로 제출하지 않는다."""
    declare_seq = await actor.submit(DeclareAction(player_id=player_id, raw_text="문을 민다"))
    confirm_seq = await actor.submit(
        ConfirmAction(
            player_id=player_id,
            move="힘으로 밀어붙인다",
            stat="STR",
            system_suggestion={"move": "힘으로 밀어붙인다", "stat": "STR"},
            player_confirmed=True,
            caused_by_seq=declare_seq,
        )
    )
    resolve_seq = await actor.submit(
        ResolveCheck(
            move="힘으로 밀어붙인다",
            modifiers=(Modifier(type="flat", value=0, source="없음"),),
            person_id=player_id,
            character_id=player_id,
            caused_by_seq=confirm_seq,
        )
    )
    return declare_seq, resolve_seq


async def test_actor_voiding_the_check_that_triggered_the_clock_restores_exact_pre_declaration_state(
    tmp_db_path,
):
    """필수 시험 — 시계를 직접 돌린 판정을 되돌리면, 그 선언 전(=두 번째
    판정 직후) 상태와 정확히 같은 값으로 돌아온다. 세 값 모두 확인한다:
    failure_count·fails_since_clock·시계(clock_segment/clock_advances)."""
    store, actor = _make_actor(tmp_db_path, values=_FAILING_ROLL * 3)
    try:
        await _declare_confirm_resolve(actor)
        await _declare_confirm_resolve(actor)
        before_third = actor.state
        assert before_third.check_count == 2
        assert before_third.failure_count == 2
        assert before_third.fails_since_clock == 2
        assert before_third.clock_segment == 0
        assert before_third.clock_advances == 0

        third_declare_seq, third_resolve_seq = await _declare_confirm_resolve(actor)
        after_third_check = store.read_events("s1", from_seq=third_resolve_seq)[0]
        assert actor.state.check_count == 3
        assert actor.state.failure_count == 3
        assert actor.state.fails_since_clock == 0  # 시계가 돈 직후라 0으로 리셋됐다
        assert actor.state.clock_segment == 1
        assert actor.state.clock_advances == 1

        # 웹/CLI가 서사 실패를 감지했을 때 제출하는 것과 정확히 같은 명령.
        await actor.submit(
            VoidTurn(
                declare_seq=third_declare_seq,
                resolve_seq=third_resolve_seq,
                counts_as_failure=after_third_check.counts_as_failure,
            )
        )

        after_void = actor.state
        # 재구성(다시 접기)으로도 같은 결과 — 저장된 사건만으로 정확히 이
        # 상태가 재현된다(서버 재시작에도 살아남는다는 뜻). store가 아직
        # 열려 있는 동안(close 전에) 확인한다.
        replayed = rebuild_state(store, "s1")
    finally:
        await actor.stop()
        store.close()

    assert after_void.check_count == before_third.check_count
    assert after_void.failure_count == before_third.failure_count
    assert after_void.fails_since_clock == before_third.fails_since_clock
    assert after_void.clock_segment == before_third.clock_segment
    assert after_void.clock_advances == before_third.clock_advances
    assert third_declare_seq in after_void.voided_declare_seqs

    assert replayed.check_count == before_third.check_count
    assert replayed.failure_count == before_third.failure_count
    assert replayed.fails_since_clock == before_third.fails_since_clock
    assert replayed.clock_segment == before_third.clock_segment


async def test_actor_voiding_twice_raises_turn_already_voided_and_stays_a_no_op(tmp_db_path):
    store, actor = _make_actor(tmp_db_path, values=_FAILING_ROLL)
    try:
        declare_seq, resolve_seq = await _declare_confirm_resolve(actor)
        check_event = store.read_events("s1", from_seq=resolve_seq)[0]
        await actor.submit(
            VoidTurn(
                declare_seq=declare_seq,
                resolve_seq=resolve_seq,
                counts_as_failure=check_event.counts_as_failure,
            )
        )
        state_after_first_void = actor.state
        with pytest.raises(TurnAlreadyVoided):
            await actor.submit(
                VoidTurn(
                    declare_seq=declare_seq,
                    resolve_seq=resolve_seq,
                    counts_as_failure=check_event.counts_as_failure,
                )
            )
    finally:
        await actor.stop()
        store.close()

    assert actor.state.check_count == state_after_first_void.check_count
    assert actor.state.failure_count == state_after_first_void.failure_count


async def test_actor_rejects_a_void_whose_declare_seq_and_resolve_seq_do_not_match(tmp_db_path):
    """declare_seq/resolve_seq 짝이 실제 확인된 판정과 어긋나면
    거절한다(클라이언트가 보낸 값을 그대로 믿지 않는다, ASVS V5) —
    호출부가 넘긴 값을 그대로 믿지 않는 다른 `_prepare_*`들과 같은
    신중함."""
    store, actor = _make_actor(tmp_db_path, values=_FAILING_ROLL * 2)
    try:
        first_declare_seq, first_resolve_seq = await _declare_confirm_resolve(actor)
        _second_declare_seq, second_resolve_seq = await _declare_confirm_resolve(actor)

        with pytest.raises(CommandRejected):
            await actor.submit(
                VoidTurn(
                    declare_seq=first_declare_seq,
                    resolve_seq=second_resolve_seq,  # 다른 턴의 판정 — 짝이 안 맞는다
                    counts_as_failure=True,
                )
            )
    finally:
        await actor.stop()
        store.close()
