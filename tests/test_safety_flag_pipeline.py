"""생각 블록 방어가 스트림부터 사건 기록까지 한 줄기로 관통하는지 웹·명령줄
두 경로에서 함께 확인한다 (10-01 Task 2, SAFE-01·SAFE-03·T-10-03).

가짜 제공자는 `tests/test_master_gm.py:82`의 `_TwoSentenceStreamProvider`와
`tests/test_web_actions.py`/`tests/test_turn_flow_failure.py`의 기존 가짜
제공자 패턴을 그대로 본떠 만든다 — 새 대역 스타일을 발명하지 않는다.
"""

import json

from fastapi.testclient import TestClient

from conftest import FakeProvider
from conftest import select_character as _select_character
from gptrpg.agents import providers as providers_module
from gptrpg.agents.envelope import AgentResult
from gptrpg.agents.narration_guard import NOTICE_FILTERED
from gptrpg.cli.main import main
from gptrpg.event_log.store import EventStore
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
        "rulebook_id": "dungeonworld_like",
    }
    body.update(overrides)
    return body


def _confirm_body(declare_seq: int, **overrides) -> dict:
    body = {
        "player_id": "bram",
        "move": "parley",
        "stat": "CHA",
        "suggestion_move": "parley",
        "suggestion_stat": "CHA",
        "confirmed": True,
        "declare_seq": declare_seq,
        "target": 10,
        "rulebook_id": "dungeonworld_like",
        "character_id": "bram",
        "modifiers": [],
    }
    body.update(overrides)
    return body


def _events(client: TestClient, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events")
    assert response.status_code == 200
    return response.json()["events"]


def _events_of_type(client: TestClient, event_type: str, session_id: str = SESSION_ID) -> list[dict]:
    return [event for event in _events(client, session_id) if event["event_type"] == event_type]


def _run_web_turn(web_client_with_fake_provider, *, stream_text: str):
    """선언 -> 캐릭터 선택 -> 확인까지 실제 경로로 밀어붙여 서사를 만든다.

    `web_client_with_fake_provider` 픽스처가 만드는 `TestClient`는 `with`
    문맥이 열려 있는 동안만 유효하다 — 호출자가 그 문맥 안에서 이 함수를
    부른다.
    """
    classifier = FakeProvider(complete_value=_CANDIDATE_JSON)
    gm = FakeProvider(stream_text=stream_text)
    client = web_client_with_fake_provider(action_classifier=classifier, master_gm=gm)
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
    with _run_web_turn(web_client_with_fake_provider, stream_text=_THINK_IN_ONE_SENTENCE) as client:
        body = _declare_and_confirm(client)
        narrations = _events_of_type(client, "narration_appended")
        flags = _events_of_type(client, "safety_flagged")

    assert body["narration_failed"] is not True
    joined = "\n".join(n["text"] for n in narrations)
    for marker in _LEAK_MARKERS:
        assert marker not in joined, f"'{marker}'가 화면에 나간 서사에 남아 있다"

    assert len(narrations) == 2
    assert narrations[0]["text"] == "문이 열린다."
    assert narrations[1]["text"] == NOTICE_FILTERED

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
    with _run_web_turn(
        web_client_with_fake_provider, stream_text=_THINK_SPANS_TWO_SENTENCES
    ) as client:
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
    with _run_web_turn(web_client_with_fake_provider, stream_text=_THINK_IN_ONE_SENTENCE) as client:
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
# 명령줄 경로 (test_turn_flow_failure.py의 _install_fake_provider/_read_events와
# 같은 모양) — 웹과 짝을 이룬다(Pitfall 1: 한쪽만 고치면 회귀가 재발한다).
# ---------------------------------------------------------------------------


class _StreamTextProvider:
    """`turn_flow`가 쓰는 classify+narrate 양쪽을 결정적으로 채우는 가짜 제공자.

    `conftest.FakeProvider`와 같은 방식(단어 단위 스트리밍)이지만, CLI는
    `agents.providers.PROVIDER_FACTORIES`에 이름으로 등록해 넣는 방식이라
    이 파일 안에 따로 둔다(`tests/test_turn_flow_failure.py`의 관례와 같음).
    """

    name = "fake-think-stream"

    def __init__(self, *, complete_value: str, text: str) -> None:
        self._complete_value = complete_value
        self._text = text
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
        for word in self._text.split(" "):
            if word:
                yield word + " "
        self._last_result = AgentResult(
            ok=True, value=self._text, elapsed_ms=5, prompt_tokens=2, completion_tokens=2
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
    db = str(tmp_db_path)
    provider = _StreamTextProvider(complete_value=_CANDIDATE_JSON, text=_THINK_IN_ONE_SENTENCE)
    _install_fake_provider(monkeypatch, provider)

    exit_code = _run_turn(db, "cli-s1", "문을 두드린다", monkeypatch=monkeypatch)
    assert exit_code == 0

    captured = capsys.readouterr()
    for marker in _LEAK_MARKERS:
        assert marker not in captured.out, f"'{marker}'가 명령줄 화면에 남아 있다"

    events = _read_events(db, "cli-s1")
    narration_events = [e for e in events if e.event_type == "narration_appended"]
    flag_events = [e for e in events if e.event_type == "safety_flagged"]

    assert len(narration_events) == 2
    assert narration_events[0].text == "문이 열린다."
    assert narration_events[1].text == NOTICE_FILTERED

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
