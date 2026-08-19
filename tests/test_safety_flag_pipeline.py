"""생각 블록 방어가 스트림부터 사건 기록까지 한 줄기로 관통하는지 웹·명령줄
두 경로에서 함께 확인한다 (10-01 Task 2, SAFE-01·SAFE-03·T-10-03).

가짜 제공자는 `tests/test_master_gm.py:82`의 `_TwoSentenceStreamProvider`와
`tests/test_web_actions.py`/`tests/test_turn_flow_failure.py`의 기존 가짜
제공자 패턴을 그대로 본떠 만든다 — 새 대역 스타일을 발명하지 않는다.
"""

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from conftest import FakeProvider
from conftest import select_character as _select_character
from gptrpg.agents import providers as providers_module
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.narration_guard import NOTICE_FILTERED, REPLACEMENT_CHAR
from gptrpg.cli.main import main
from gptrpg.event_log.schema import EVENT_SCHEMA_VERSION, SafetyFlagged, utc_now_iso
from gptrpg.event_log.store import EventStore
from gptrpg.session_actor.actor import CommandRejected, RecordSafetyFlag, SessionActor
from gptrpg.session_actor.projection import rebuild_state_from_events

SESSION_ID = "s1"

_CANDIDATE_JSON = json.dumps([{"move": "parley", "stat": "CHA"}])

_THINK_IN_ONE_SENTENCE = "문이 열린다. <think>몰래 이렇게 생각한다</think> 그리고 이어진다."
"""생각 블록이 한 문장 안에 통째로 들어간 스트림 — 문장 두 개(첫 문장은
깨끗, 둘째 문장이 생각 블록을 통째로 담는다)."""

_THINK_SPANS_TWO_SENTENCES = (
    "문이 열린다. <think>몰래 생각한다. 다음 문장도 생각 중이다</think> 이제 이야기로 돌아온다."
)
"""여는 표식과 닫는 표식이 서로 다른 문장에 걸친 스트림(D-01의 핵심 근거) —
문장 셋(첫 문장 깨끗, 둘째가 연다, 셋째가 닫으며 이어진다)."""

_CLEAN_STREAM = "문이 요란하게 부서진다. 안에서 서늘한 바람이 흘러나온다."

_REGEN_CLEAN_TEXT = "고요한 정적 속에서 이야기가 부드럽게 이어진다."
"""재생성(D-06, 10-03) 호출이 돌려주는 깨끗한 이어쓰기 — 첫 스트림이 걸린
뒤 `narrate()`가 자동으로 한 번 다시 부르는 자리를 흉내낸다. 걸린 원문
(`_LEAK_MARKERS`)과 겹치는 조각이 하나도 없다."""

_LEAK_MARKERS = ("<think>", "</think>", "몰래", "생각한다", "생각 중이다")
"""걸린 원문에서만 나오는 조각들 — 화면에 나간 어떤 문구에도 있으면 안 된다."""


# ---------------------------------------------------------------------------
# 웹 경로 도우미 (tests/test_web_actions.py와 같은 모양)
# ---------------------------------------------------------------------------


def _declare_body(**overrides) -> dict:
    body = {
        "player_id": "bram",
        "character_id": "bram",
        "raw_text": "경비병을 설득해 통로를 열어 보려 한다",
    }
    body.update(overrides)
    return body


def _confirm_body(declare_seq: int, **overrides) -> dict:
    # `target`/`modifiers`는 `ConfirmRequest`에서 사라졌다(D-02, 12-01
    # Task 3) — `extra="forbid"`가 이 두 칸을 거절한다.
    body = {
        "player_id": "bram",
        "move": "parley",
        "stat": "CHA",
        "suggestion_move": "parley",
        "suggestion_stat": "CHA",
        "confirmed": True,
        "declare_seq": declare_seq,
        "character_id": "bram",
    }
    body.update(overrides)
    return body


def _events(client: TestClient, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events")
    assert response.status_code == 200
    return response.json()["events"]


def _events_of_type(client: TestClient, event_type: str, session_id: str = SESSION_ID) -> list[dict]:
    return [event for event in _events(client, session_id) if event["event_type"] == event_type]


class _CallVaryingStreamProvider:
    """`stream()` 호출 횟수에 따라 다른 텍스트를 내는 대역(10-03) — 첫 호출은
    `first_text`(걸릴 수 있는 원문), 두 번째 이후는 `regen_text`(깨끗한
    이어쓰기)를 낸다. `narrate()`가 걸린 문장을 만나면 그 자리에서 재생성을
    한 번 호출하는 것을 흉내낸다 — `messages`(재생성 지시가 실린 프롬프트)
    자체는 안 들여다본다, 호출 순서만 본다. `conftest.FakeProvider`와 같은
    단어 단위 스트리밍·`note_result()` 지원 모양이다."""

    name = "fake-call-varying"

    def __init__(self, *, first_text: str, regen_text: str = _REGEN_CLEAN_TEXT) -> None:
        self._first_text = first_text
        self._regen_text = regen_text
        self._stream_call_count = 0
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        raise NotImplementedError("이 이중체는 stream()만 시험한다")

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        self._stream_call_count += 1
        text = self._first_text if self._stream_call_count == 1 else self._regen_text
        for word in text.split(" "):
            if word:
                yield word + " "
        self._last_result = AgentResult(
            ok=True, value=text, elapsed_ms=5, prompt_tokens=2, completion_tokens=2
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def _run_web_turn(web_client_with_fake_provider, *, stream_text: str | None = None, gm=None):
    """선언 -> 캐릭터 선택 -> 확인까지 실제 경로로 밀어붙여 서사를 만든다.

    `web_client_with_fake_provider` 픽스처가 만드는 `TestClient`는 `with`
    문맥이 열려 있는 동안만 유효하다 — 호출자가 그 문맥 안에서 이 함수를
    부른다. `gm`을 직접 주면(재생성이 걸리는 시나리오) 그 대역을 그대로
    쓰고, 아니면 `stream_text`로 고정 응답인 `FakeProvider`를 만든다(깨끗한
    스트림 시나리오 — 재생성 자체가 안 일어나므로 고정 응답으로 충분하다).
    """
    classifier = FakeProvider(complete_value=_CANDIDATE_JSON)
    gm_provider = gm if gm is not None else FakeProvider(stream_text=stream_text)
    client = web_client_with_fake_provider(action_classifier=classifier, master_gm=gm_provider)
    return client


def _declare_and_confirm(client: TestClient) -> dict:
    _select_character(client, SESSION_ID, "bram")
    declare_resp = client.post(
        f"/api/sessions/{SESSION_ID}/actions/declare", json=_declare_body()
    )
    assert declare_resp.status_code == 200
    declare_seq = declare_resp.json()["declare_seq"]
    confirm_resp = client.post(
        f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
    )
    assert confirm_resp.status_code == 200
    return confirm_resp.json()


# ---------------------------------------------------------------------------
# 1. 생각 블록이 한 문장 안에 통째로 들어간 스트림 — 웹 경로
# ---------------------------------------------------------------------------


def test_web_think_block_within_one_sentence_is_filtered_not_leaked(
    web_client_with_fake_provider,
) -> None:
    """10-03부터 걸린 문장은 그 자리에서 재생성을 한 번 시도한다(D-06) — 이
    대역은 재생성 호출에서 깨끗한 문장을 내므로 턴이 끝까지 이어진다."""
    gm = _CallVaryingStreamProvider(first_text=_THINK_IN_ONE_SENTENCE)
    with _run_web_turn(web_client_with_fake_provider, gm=gm) as client:
        body = _declare_and_confirm(client)
        narrations = _events_of_type(client, "narration_appended")
        flags = _events_of_type(client, "safety_flagged")

    assert body["narration_failed"] is not True
    joined = "\n".join(n["text"] for n in narrations)
    for marker in _LEAK_MARKERS:
        assert marker not in joined, f"'{marker}'가 화면에 나간 서사에 남아 있다"

    assert len(narrations) == 3
    assert narrations[0]["text"] == "문이 열린다."
    assert narrations[1]["text"] == NOTICE_FILTERED
    assert narrations[2]["text"] == _REGEN_CLEAN_TEXT
    assert gm._stream_call_count == 2

    assert len(flags) == 1
    assert flags[0]["source"] == "narration"
    assert flags[0]["reason"] == "think_block"
    assert flags[0]["disposition"] == "blocked"
    # 사건 payload를 JSON으로 되읽어도 모델이 쓴 문장의 어떤 부분열도 없다(T-10-03).
    flag_json = json.dumps(flags[0], ensure_ascii=False)
    for marker in _LEAK_MARKERS:
        assert marker not in flag_json


# ---------------------------------------------------------------------------
# 2. 여는/닫는 표식이 서로 다른 문장에 걸친 스트림 — 웹 경로 (D-01의 핵심 근거)
# ---------------------------------------------------------------------------


def test_web_think_block_spanning_two_sentences_is_filtered_not_leaked(
    web_client_with_fake_provider,
) -> None:
    """10-03부터 걸린 문장은 재생성을 한 번 시도한다(D-06) — 이 대역은
    재생성 호출에서 깨끗한 문장을 내므로 턴이 끝까지 이어진다."""
    gm = _CallVaryingStreamProvider(first_text=_THINK_SPANS_TWO_SENTENCES)
    with _run_web_turn(web_client_with_fake_provider, gm=gm) as client:
        body = _declare_and_confirm(client)
        narrations = _events_of_type(client, "narration_appended")
        flags = _events_of_type(client, "safety_flagged")

    assert body["narration_failed"] is not True
    joined = "\n".join(n["text"] for n in narrations)
    for marker in _LEAK_MARKERS:
        assert marker not in joined, f"'{marker}'가 화면에 나간 서사에 남아 있다"

    assert len(flags) >= 1
    assert all(f["reason"] == "think_block" and f["source"] == "narration" for f in flags)


# ---------------------------------------------------------------------------
# 3. 걸린 턴의 사건을 rebuild_state/폴링 경로로 다시 접어도 UnknownEventType이 안 난다
# ---------------------------------------------------------------------------


def test_web_turn_with_safety_flag_replays_without_unknown_event_type(
    web_client_with_fake_provider,
) -> None:
    gm = _CallVaryingStreamProvider(first_text=_THINK_IN_ONE_SENTENCE)
    with _run_web_turn(web_client_with_fake_provider, gm=gm) as client:
        _declare_and_confirm(client)
        # `GET /events`가 매번 rebuild_state_from_events로 다시 접는다 — 이미
        # `_events()`가 200으로 성공했다는 사실 자체가 UnknownEventType이
        # 안 났다는 증거지만, 사건 종류 하나가 실제로 있었는지까지 확인한다.
        flags = _events_of_type(client, "safety_flagged")
        state_response = client.get(f"/api/sessions/{SESSION_ID}/events")

    assert state_response.status_code == 200
    assert len(flags) == 1
    state = state_response.json()["state"]
    all_events = state_response.json()["events"]
    assert state["last_seq"] == all_events[-1]["seq"]


# ---------------------------------------------------------------------------
# 4. 깨끗한 스트림은 지금과 똑같이 흐른다(안내 사건 0건, chunk_index 순서 그대로)
# ---------------------------------------------------------------------------


def test_web_clean_stream_produces_no_safety_flag_and_keeps_chunk_order(
    web_client_with_fake_provider,
) -> None:
    with _run_web_turn(web_client_with_fake_provider, stream_text=_CLEAN_STREAM) as client:
        body = _declare_and_confirm(client)
        narrations = sorted(
            _events_of_type(client, "narration_appended"), key=lambda e: e["chunk_index"]
        )
        flags = _events_of_type(client, "safety_flagged")

    assert body["narration_chunk_count"] == 2
    assert [n["chunk_index"] for n in narrations] == [0, 1]
    assert [n["text"] for n in narrations] == [
        "문이 요란하게 부서진다.",
        "안에서 서늘한 바람이 흘러나온다.",
    ]
    assert flags == []


# ---------------------------------------------------------------------------
# 5. 깨진 글자(U+FFFD) — flagged로 기록되면서 문장도 그대로 화면에 나간다
#    (10-06, SAFE-01). 이 두 단언이 한 시험 안에 같이 있어야 「기록은
#    남았는데 화면엔 안 나갔다」는 회귀를 잡는다.
# ---------------------------------------------------------------------------

_CORRUPTED_STREAM = f"담로의 손이 {REPLACEMENT_CHAR}{REPLACEMENT_CHAR} 굳었다. 서늘한 바람이 흘러든다."


def test_web_corrupted_glyph_is_recorded_and_still_reaches_the_screen(
    web_client_with_fake_provider,
) -> None:
    with _run_web_turn(web_client_with_fake_provider, stream_text=_CORRUPTED_STREAM) as client:
        body = _declare_and_confirm(client)
        narrations = sorted(
            _events_of_type(client, "narration_appended"), key=lambda e: e["chunk_index"]
        )
        flags = _events_of_type(client, "safety_flagged")

    # 함께 단언 ① — 문장이 걸러지지 않고 원문 그대로(깨진 글자 포함) 화면에 나간다.
    assert body["narration_failed"] is not True
    assert [n["text"] for n in narrations] == [
        f"담로의 손이 {REPLACEMENT_CHAR}{REPLACEMENT_CHAR} 굳었다.",
        "서늘한 바람이 흘러든다.",
    ]

    # 함께 단언 ② — 같은 턴에서 운영자 기록이 실제로 남는다.
    assert len(flags) == 1
    assert flags[0]["source"] == "narration"
    assert flags[0]["reason"] == "corrupted_glyph"
    assert flags[0]["disposition"] == "flagged"
    assert flags[0]["matched_len"] == 2


# ---------------------------------------------------------------------------
# 명령줄 경로 (test_turn_flow_failure.py의 _install_fake_provider/_read_events와
# 같은 모양) — 웹과 짝을 이룬다(Pitfall 1: 한쪽만 고치면 회귀가 재발한다).
# ---------------------------------------------------------------------------


class _StreamTextProvider:
    """`turn_flow`가 쓰는 classify+narrate 양쪽을 결정적으로 채우는 가짜 제공자.

    `conftest.FakeProvider`와 같은 방식(단어 단위 스트리밍)이지만, CLI는
    `agents.providers.PROVIDER_FACTORIES`에 이름으로 등록해 넣는 방식이라
    이 파일 안에 따로 둔다(`tests/test_turn_flow_failure.py`의 관례와 같음).

    `regen_text`(10-03)는 두 번째 이후 `stream()` 호출에서 낸다 — `narrate()`가
    걸린 문장을 만나 재생성을 한 번 시도하는 자리를 흉내낸다. 기본값은
    `text`와 같다(재생성이 안 일어나는 시나리오는 아무 영향이 없다)."""

    name = "fake-think-stream"

    def __init__(self, *, complete_value: str, text: str, regen_text: str | None = None) -> None:
        self._complete_value = complete_value
        self._text = text
        self._regen_text = regen_text if regen_text is not None else text
        self._stream_call_count = 0
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, *, model, system, messages, max_tokens, timeout_s) -> AgentResult:
        result = AgentResult(
            ok=True,
            value=self._complete_value,
            elapsed_ms=1,
            prompt_tokens=5,
            completion_tokens=3,
        )
        self._last_result = result
        return result

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        self._stream_call_count += 1
        text = self._text if self._stream_call_count == 1 else self._regen_text
        for word in text.split(" "):
            if word:
                yield word + " "
        self._last_result = AgentResult(
            ok=True, value=text, elapsed_ms=5, prompt_tokens=2, completion_tokens=2
        )

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("complete()/stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


def _install_fake_provider(monkeypatch, fake_provider, *, name="fake", env_var="FAKE_API_KEY"):
    monkeypatch.setitem(providers_module.PROVIDER_ENV_VARS, name, env_var)
    monkeypatch.setitem(providers_module.PROVIDER_FACTORIES, name, lambda api_key: fake_provider)
    monkeypatch.setenv(env_var, "test-key")


def _read_events(db: str, session: str):
    store = EventStore(db)
    store.initialize()
    try:
        return store.read_events(session)
    finally:
        store.close()


def _run_turn(db: str, session: str, text: str, *, monkeypatch) -> int:
    monkeypatch.setattr("builtins.input", lambda *_args: "")
    return main(
        [
            "turn",
            "--db",
            db,
            "--session",
            session,
            "--player",
            "p1",
            "--text",
            text,
            "--provider",
            "fake",
            "--model",
            "fake-model",
        ]
    )


def test_cli_think_block_within_one_sentence_is_filtered_not_leaked(
    tmp_db_path, monkeypatch, capsys
) -> None:
    """10-03부터 걸린 문장은 재생성을 한 번 시도한다(D-06) — `regen_text`가
    깨끗하므로 턴이 끝까지 이어진다(exit 0)."""
    db = str(tmp_db_path)
    provider = _StreamTextProvider(
        complete_value=_CANDIDATE_JSON, text=_THINK_IN_ONE_SENTENCE, regen_text=_REGEN_CLEAN_TEXT
    )
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "cli-s1", "문을 두드린다", monkeypatch=monkeypatch)
    assert exit_code == 0

    captured = capsys.readouterr()
    for marker in _LEAK_MARKERS:
        assert marker not in captured.out, f"'{marker}'가 명령줄 화면에 남아 있다"

    events = _read_events(db, "cli-s1")
    narration_events = [e for e in events if e.event_type == "narration_appended"]
    flag_events = [e for e in events if e.event_type == "safety_flagged"]

    assert len(narration_events) == 3
    assert narration_events[0].text == "문이 열린다."
    assert narration_events[1].text == NOTICE_FILTERED
    assert narration_events[2].text == _REGEN_CLEAN_TEXT
    assert provider._stream_call_count == 2

    assert len(flag_events) == 1
    assert flag_events[0].source == "narration"
    assert flag_events[0].reason == "think_block"
    assert flag_events[0].disposition == "blocked"

    # 판 6으로 기록된 이 세션이 그대로 다시 접힌다 — UnknownEventType이 안 난다.
    state = rebuild_state_from_events("cli-s1", events)
    assert state.last_seq == events[-1].seq


def test_cli_clean_stream_produces_no_safety_flag(tmp_db_path, monkeypatch, capsys) -> None:
    db = str(tmp_db_path)
    provider = _StreamTextProvider(complete_value=_CANDIDATE_JSON, text=_CLEAN_STREAM)
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "cli-s2", "문을 두드린다", monkeypatch=monkeypatch)
    assert exit_code == 0

    events = _read_events(db, "cli-s2")
    narration_events = [e for e in events if e.event_type == "narration_appended"]
    flag_events = [e for e in events if e.event_type == "safety_flagged"]

    assert [e.text for e in narration_events] == [
        "문이 요란하게 부서진다.",
        "안에서 서늘한 바람이 흘러나온다.",
    ]
    assert flag_events == []


# ---------------------------------------------------------------------------
# 10-07 Task 2 (WR-03): source × reason 조합을 스키마와 액터 양쪽이 막는다.
#
# 실제로 쓰이는 다섯 조합(source="classifier"↔reason="unknown_move",
# source="narration"↔나머지 넷)은 통과해야 하고, 그 밖의 조합(적어도 둘)은
# 스키마 층(`SafetyFlagged._require_source_reason_pairing`)과 액터 층
# (`SessionActor._prepare_safety_flag`) 각각에서 독립적으로 거절돼야 한다 —
# 한쪽만 있으면 다른 경로로 우회된다(WR-03 Fix).
# ---------------------------------------------------------------------------


class _NoRollNeededRoller:
    """`RecordSafetyFlag`는 판정 코어를 부르지 않으므로 눈이 실제로는 안
    쓰인다 — `SessionActor` 생성자가 요구하는 자리만 채우는 자리표시자다."""

    def roll_d6(self) -> int:
        raise AssertionError("safety_flagged 경로는 굴림을 쓰지 않는다")


def _make_safety_actor(tmp_db_path) -> tuple[EventStore, SessionActor]:
    store = EventStore(tmp_db_path)
    store.initialize()
    actor = SessionActor(store, SESSION_ID, _NoRollNeededRoller())
    actor.start()
    return store, actor


def _safety_flagged_kwargs(*, source: str, reason: str, seq: int = 0) -> dict:
    return {
        "session_id": SESSION_ID,
        "seq": seq,
        "schema_version": EVENT_SCHEMA_VERSION,
        "recorded_at": utc_now_iso(),
        "event_type": "safety_flagged",
        "source": source,
        "reason": reason,
        "disposition": "blocked",
        "matched_len": 12,
        "subject_len": 12,
    }


_VALID_SOURCE_REASON_COMBINATIONS = [
    ("classifier", "unknown_move"),
    ("narration", "think_block"),
    ("narration", "source_overlap"),
    ("narration", "character_break"),
    ("narration", "corrupted_glyph"),
]
"""실제 호출부 둘(action_classifier.py/narration_guard.py 배선)이 실제로
내는 다섯 조합 그대로다 — 이 표가 실제 배선과 어긋나면 정상 배선도 스키마·
액터 층에서 거절돼야 하므로, 이 목록이 곧 회귀 방지 대상이다."""

_INVALID_SOURCE_REASON_COMBINATIONS = [
    ("classifier", "think_block"),
    ("narration", "unknown_move"),
]
"""리뷰가 명시적으로 예시로 든 말 안 되는 조합 둘(WR-03) — 분류기가 서사
사유를 내거나, 서사 검사가 분류기 사유를 내는 경우는 어느 쪽도 실제로
일어나지 않는다."""


@pytest.mark.parametrize("source,reason", _VALID_SOURCE_REASON_COMBINATIONS)
def test_schema_accepts_the_five_real_source_reason_combinations(source, reason):
    event = SafetyFlagged(**_safety_flagged_kwargs(source=source, reason=reason))
    assert event.source == source
    assert event.reason == reason


@pytest.mark.parametrize("source,reason", _INVALID_SOURCE_REASON_COMBINATIONS)
def test_schema_rejects_nonsensical_source_reason_combinations(source, reason):
    """`SafetyFlagged._require_source_reason_pairing`이 스키마 층에서
    거절한다 — 저장소를 우회해 직접 사건 객체를 만들어도 막힌다."""
    with pytest.raises(ValidationError) as exc_info:
        SafetyFlagged(**_safety_flagged_kwargs(source=source, reason=reason))
    assert "필요충분" in str(exc_info.value)


@pytest.mark.parametrize("source,reason", _VALID_SOURCE_REASON_COMBINATIONS)
async def test_actor_accepts_the_five_real_source_reason_combinations(
    tmp_db_path, source, reason
) -> None:
    store, actor = _make_safety_actor(tmp_db_path)
    try:
        seq = await actor.submit(
            RecordSafetyFlag(
                source=source, reason=reason, disposition="blocked", matched_len=12, subject_len=12
            )
        )
        events = store.read_events(SESSION_ID)
        assert len(events) == 1
        assert events[0].seq == seq
        assert events[0].source == source
        assert events[0].reason == reason
    finally:
        store.close()


@pytest.mark.parametrize("source,reason", _INVALID_SOURCE_REASON_COMBINATIONS)
async def test_actor_rejects_nonsensical_source_reason_combinations_and_appends_nothing(
    tmp_db_path, source, reason
) -> None:
    """`SessionActor._prepare_safety_flag`가 명령이 저장소에 닿기 전에
    거절한다 — 반쪽 상태 없이 사건이 하나도 안 남는다."""
    store, actor = _make_safety_actor(tmp_db_path)
    try:
        with pytest.raises(CommandRejected) as exc_info:
            await actor.submit(
                RecordSafetyFlag(
                    source=source,
                    reason=reason,
                    disposition="blocked",
                    matched_len=12,
                    subject_len=12,
                )
            )
        assert "필요충분" in str(exc_info.value)
        assert store.read_events(SESSION_ID) == []
    finally:
        store.close()
