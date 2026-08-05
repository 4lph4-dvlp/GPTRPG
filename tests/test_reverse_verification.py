"""01-05 역방향 검증 — 가짜 세션 기록 하나만으로 여섯 숫자가 전부 나오는지 거꾸로 잡는다.

이 파일은 Phase 6이 프로젝트를 계속할지 정할 때 필요한 숫자 여섯 개를,
01-05 의 `fake_session_log` 픽스처(두 플레이어가 번갈아 입력하는 완결된 한 세션)만으로
산출할 수 있는지를 각각 별도의 단언으로 확인한다. 하나라도 안 나오면 칸이 빠진 것이다
— 단언을 느슨하게 고쳐 초록불을 만들지 않고, 빠진 칸을 가리킨다 (T-1-12).

여섯 숫자 (D-11): 1. 실제 토큰 소모량 2. 실제 턴 수 3. 문장 입력→확인 표시 시간
4. 확인→서사 첫 글자 시간 5. 판정 실패 횟수·시계 진행 횟수 6. (친 문장, 제안, 확인 여부).

참고: 시각 차이를 밀리초로 바꾸는 작은 도우미와 여섯 단언의 숫자 세기는 이 테스트 파일
안에 둔다 — 이것은 Phase 4가 만들 집계 코드의 자리이지 지금 라이브러리에 넣을 것이 아니다.
"""

from datetime import datetime

import pytest

from gptrpg.event_log.schema import (
    ActionConfirmed,
    ActionDeclared,
    AiInvoked,
    CheckResolved,
    ClockAdvanced,
    NarrationAppended,
)

# 여섯 종류의 구체 클래스 — GameEvent 는 Annotated[Union[...]] 이라 isinstance 에 못 쓴다.
_SIX_TYPES = (
    ActionDeclared,
    ActionConfirmed,
    CheckResolved,
    NarrationAppended,
    ClockAdvanced,
    AiInvoked,
)

# ---------------------------------------------------------------------------
# 시각 문자열 -> 정수 밀리초. 정수 산술만 쓴다 (부동소수/반올림 경로 부재를 증명).
# ---------------------------------------------------------------------------

_ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def _ms_diff(later_iso: str, earlier_iso: str) -> int:
    """두 ISO8601 recorded_at 문자열의 차이를 정수 밀리초로 돌려준다."""
    later = datetime.strptime(later_iso, _ISO_FORMAT)
    earlier = datetime.strptime(earlier_iso, _ISO_FORMAT)
    delta = later - earlier
    return delta.days * 86_400_000 + delta.seconds * 1000 + delta.microseconds // 1000


def _by_seq(events: list) -> dict:
    """seq -> 사건 사전. 인과 짝짓기에 쓴다."""
    return {e.seq: e for e in events}


def _find_caused_by(event, lookup: dict):
    """`event.caused_by_seq` 가 가리키는 사건을 찾는다. 못 찾으면 그 자리에서 실패한다."""
    caused = event.caused_by_seq
    if caused is None or caused not in lookup:
        pytest.fail(
            f"{event.event_type}(seq={event.seq}) 의 caused_by_seq={caused!r} 가 "
            "가리키는 사건을 찾지 못했다 — 인과 칸이 끊겼다"
        )
    return lookup[caused]


# ---------------------------------------------------------------------------
# 픽스처 자체 확인 — Task 1의 검증 명령(`-k fixture`)이 고르는 테스트.
# ---------------------------------------------------------------------------


def test_fixture_round_trips_a_complete_session_through_the_store(
    fake_session_log,
) -> None:
    """`fake_session_log` 가 여섯 종류를 전부 담고 저장소를 거쳐 돌아온다."""
    events = fake_session_log.events
    session_id = fake_session_log.session_id

    # 픽스처는 실제 저장소를 거쳤다 — 모든 사건이 같은 세션에서 읽혔고, 순번 오름차순이다.
    assert len(events) > 0
    assert all(isinstance(e, _SIX_TYPES) for e in events)
    assert all(e.session_id == session_id for e in events)
    assert [e.seq for e in events] == list(range(len(events)))

    by_type: dict[str, list] = {}
    for e in events:
        by_type.setdefault(e.event_type, []).append(e)

    # 여섯 종류가 전부 최소 한 번씩 나온다.
    assert set(by_type) == {
        "action_declared",
        "action_confirmed",
        "check_resolved",
        "narration_appended",
        "clock_advanced",
        "ai_invoked",
    }, "여섯 종류가 전부 등장해야 한다"

    # action_declared 는 3개 이상 (턴 수가 1보다 커야 개수 세기가 의미 있다).
    declared = by_type["action_declared"]
    assert len(declared) == fake_session_log.turn_count
    assert len(declared) >= 3

    # action_confirmed 는 선언마다 하나.
    assert len(by_type["action_confirmed"]) == len(declared)

    # check_resolved 는 3개 이상, 그중 등급이 실패(miss)인 것이 1개 이상.
    checks = by_type["check_resolved"]
    assert len(checks) >= 3
    assert any(c.grade == "miss" for c in checks)

    # narration_appended: chunk_index 가 0인 것과 1인 것이 각각 존재 (서사 1개가 2조각).
    narration = by_type["narration_appended"]
    assert any(n.chunk_index == 0 for n in narration)
    assert any(n.chunk_index == 1 for n in narration)

    # 재굴림이 한 번 있다 — rolls 의 길이가 4인 check_resolved 가 하나 존재.
    assert any(len(c.rolls) == 4 for c in checks)

    # seq 0~3 구간에서 두 플레이어의 사건이 번갈아 나온다.
    first_four_players = [events[i].player_id for i in range(4)]
    assert first_four_players == ["p1", "p2", "p1", "p2"], (
        "순번 0~3 은 p1·p2·p1·p2 로 번갈아야 한다 (순번 인접 짝짓기가 틀리게)"
    )

    # 실행 시각에 의존하지 않는다 — 첫 사건의 recorded_at 이 고정 기준 시각 문자열과 같다.
    assert events[0].recorded_at == "2026-01-01T00:00:00.000Z"


# ---------------------------------------------------------------------------
# ① 실제 토큰 소모량
# ---------------------------------------------------------------------------


def test_reverse_verification_token_spend(fake_session_log) -> None:
    events = fake_session_log.events
    ai_events = [e for e in events if isinstance(e, AiInvoked)]
    total = sum(e.prompt_tokens + e.completion_tokens for e in ai_events)

    assert total > 0, "① 실제 토큰 소모량이 0이다 — ai_invoked 사건에서 토큰이 안 나왔다"
    assert total == fake_session_log.token_spend, (
        f"① 실제 토큰 소모량이 픽스처 기대값과 다르다: {total} != {fake_session_log.token_spend}"
    )


# ---------------------------------------------------------------------------
# ② 실제 턴 수
# ---------------------------------------------------------------------------


def test_reverse_verification_turn_count(fake_session_log) -> None:
    events = fake_session_log.events
    declared_count = sum(1 for e in events if isinstance(e, ActionDeclared))

    assert declared_count == fake_session_log.turn_count, (
        f"② 실제 턴 수가 픽스처 기대값과 다르다: {declared_count} != {fake_session_log.turn_count}"
    )
    assert declared_count > 1, "② 실제 턴 수가 1 이하다 — 개수 세기가 의미 없다"


# ---------------------------------------------------------------------------
# ③ 문장 입력 → 행동 확인 표시 시간 (인과 칸으로만 짝짓기)
# ---------------------------------------------------------------------------


def test_reverse_verification_declare_confirm_latency_ms(fake_session_log) -> None:
    events = fake_session_log.events
    lookup = _by_seq(events)
    confirmed_events = [e for e in events if isinstance(e, ActionConfirmed)]

    computed = [
        _ms_diff(c.recorded_at, _find_caused_by(c, lookup).recorded_at)
        for c in confirmed_events
    ]

    assert computed == fake_session_log.declare_confirm_ms, (
        "③ 문장 입력→행동 확인 표시 시간이 픽스처 기대값과 다르다: "
        f"{computed} != {fake_session_log.declare_confirm_ms}"
    )


def test_causal_pairing_differs_from_adjacent_seq_pairing(fake_session_log) -> None:
    """③의 짝짓기가 인과 칸이 아니라 순번 인접이었다면 다른(틀린) 값이 나온다.

    seq 0~3 구간에서 두 플레이어의 선언·확인이 번갈아 섞여 있으므로,
    "바로 앞 순번 = 원인"이라는 가정은 이 픽스처에서 반드시 틀린 짝을 만든다 (T-1-13).
    """
    events = fake_session_log.events
    lookup = _by_seq(events)
    confirmed_events = [e for e in events if isinstance(e, ActionConfirmed)]

    causal = [
        _ms_diff(c.recorded_at, _find_caused_by(c, lookup).recorded_at)
        for c in confirmed_events
    ]
    # events[c.seq - 1] 은 "바로 앞 순번" — 인과 칸을 무시한 순번 인접 짝짓기.
    adjacent = [_ms_diff(c.recorded_at, events[c.seq - 1].recorded_at) for c in confirmed_events]

    assert causal != adjacent, (
        "③ 순번 인접 짝짓기와 인과 칸 짝짓기가 같은 결과를 냈다 — 두 플레이어가 번갈아 "
        f"입력하는 픽스처에서는 서로 달라야 인과 칸이 실제로 일을 하고 있다는 뜻이다: "
        f"causal={causal} adjacent={adjacent}"
    )


# ---------------------------------------------------------------------------
# ④ 확인 → 서사 첫 글자 시간 (chunk_index == 0 만, 인과 칸으로 짝짓기)
# ---------------------------------------------------------------------------


def test_reverse_verification_confirm_narration_latency_ms(fake_session_log) -> None:
    events = fake_session_log.events
    lookup = _by_seq(events)
    first_chunks = [
        e for e in events if isinstance(e, NarrationAppended) and e.chunk_index == 0
    ]

    computed = [
        _ms_diff(n.recorded_at, _find_caused_by(n, lookup).recorded_at) for n in first_chunks
    ]

    assert computed == fake_session_log.confirm_narration_ms, (
        "④ 확인→서사 첫 글자 시간이 픽스처 기대값과 다르다: "
        f"{computed} != {fake_session_log.confirm_narration_ms}"
    )


# ---------------------------------------------------------------------------
# ⑤ 판정 실패 횟수 / 위협 시계 진행 횟수
# ---------------------------------------------------------------------------


def test_reverse_verification_failure_and_clock_counts(fake_session_log) -> None:
    events = fake_session_log.events
    failure_count = sum(1 for e in events if isinstance(e, CheckResolved) and e.grade == "miss")
    clock_advance_count = sum(1 for e in events if isinstance(e, ClockAdvanced))

    assert failure_count == fake_session_log.failure_count, (
        f"⑤ 판정 실패 횟수가 픽스처 기대값과 다르다: {failure_count} != {fake_session_log.failure_count}"
    )
    assert clock_advance_count == fake_session_log.clock_advance_count, (
        "⑤ 위협 시계 진행 횟수가 픽스처 기대값과 다르다: "
        f"{clock_advance_count} != {fake_session_log.clock_advance_count}"
    )


# ---------------------------------------------------------------------------
# ⑥ 플레이어가 친 문장 + 시스템 제안 + 확인 여부
# ---------------------------------------------------------------------------


def test_reverse_verification_declared_suggestion_confirmation_triples(
    fake_session_log,
) -> None:
    events = fake_session_log.events
    lookup = _by_seq(events)
    declared_events = [e for e in events if isinstance(e, ActionDeclared)]
    confirmed_events = [e for e in events if isinstance(e, ActionConfirmed)]

    assert all(d.raw_text for d in declared_events), (
        "⑥ 플레이어가 친 문장(raw_text) 이 비어 있는 action_declared 사건이 있다"
    )
    assert all(c.system_suggestion for c in confirmed_events), (
        "⑥ 시스템 제안(system_suggestion) 이 비어 있는 action_confirmed 사건이 있다"
    )
    assert all(isinstance(c.player_confirmed, bool) for c in confirmed_events), (
        "⑥ 확인 여부(player_confirmed) 가 bool 이 아닌 action_confirmed 사건이 있다"
    )

    triples = [
        (
            _find_caused_by(c, lookup).raw_text,
            c.system_suggestion,
            c.player_confirmed,
        )
        for c in confirmed_events
    ]

    assert len(triples) == fake_session_log.turn_count, (
        "⑥ (친 문장, 제안, 확인 여부) 짝의 개수가 턴 수와 다르다: "
        f"{len(triples)} != {fake_session_log.turn_count}"
    )


# ---------------------------------------------------------------------------
# 마지막 — 시각 차이 계산이 정수 밀리초로만 이루어졌다.
# ---------------------------------------------------------------------------


def test_ms_diff_returns_int(fake_session_log) -> None:
    events = fake_session_log.events
    diff = _ms_diff(events[1].recorded_at, events[0].recorded_at)

    assert type(diff) is int, (
        f"시각 차이 계산 결과의 자료형이 int 가 아니다: {type(diff)!r} — 부동소수/반올림 경로가 섞여 있다"
    )
