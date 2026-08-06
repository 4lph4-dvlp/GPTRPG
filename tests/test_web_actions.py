"""`POST /api/sessions/{id}/actions/declare` · `.../confirm` 시험 (04-05).

선언 경로(Task 2)는 `web_client_with_fake_provider` 픽스처로 네트워크 없이
`FakeProvider`만 넣어 부른다. `action_declared`/`ai_invoked` 사건이 실제로
기록에 남았는지는 `GET /api/sessions/{id}/events`(04-01)로 다시 읽어
확인한다 — 두 번째 검증 경로를 새로 만들지 않는다.
"""

import json

from fastapi.testclient import TestClient

from conftest import FakeProvider
from conftest import select_character as _select_character_at
from gptrpg.agents.envelope import AgentResult

SESSION_ID = "s1"


def _events(client: TestClient, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events")
    assert response.status_code == 200
    return response.json()["events"]


def _events_of_type(client: TestClient, event_type: str, session_id: str = SESSION_ID) -> list[dict]:
    return [event for event in _events(client, session_id) if event["event_type"] == event_type]


def _declare_body(**overrides) -> dict:
    body = {
        "player_id": "p1",
        "character_id": "bram",
        "raw_text": "경비병을 설득해 통로를 열어 보려 한다",
        "rulebook_id": "dungeonworld_like",
    }
    body.update(overrides)
    return body


def _select_character(client: TestClient, character_id: str, session_id: str = SESSION_ID) -> None:
    """`conftest.select_character` 공용 도우미의 이 파일 기본 세션 얇은
    래퍼(08-01 Task 4) — declare/confirm이 이제 신원 대조를 요구하므로
    (TRUST-02), 대다수 시험이 판정 내용을 확인하기 전에 먼저 이 통로를
    거쳐야 한다."""
    _select_character_at(client, session_id, character_id)


def _declare(client: TestClient, **overrides):
    """`_declare_body`의 `character_id`로 쿠키를 먼저 걸고 declare를 부른다.

    `character_id` 오버라이드가 알려지지 않은 캐릭터일 수 있는 신원 불일치
    시험은 이 도우미를 쓰지 않는다 — select-character 자체가 모르는
    캐릭터를 거부하므로(400) 그 경우는 각 시험이 유효한 캐릭터로 먼저
    선택한 뒤 본문만 어긋내는 방식으로 직접 조립한다.
    """
    body = _declare_body(**overrides)
    _select_character(client, body["character_id"])
    return client.post(f"/api/sessions/{SESSION_ID}/actions/declare", json=body)


# ---------------------------------------------------------------------------
# Task 2: 선언 경로
# ---------------------------------------------------------------------------


def test_declare_single_candidate_returns_tier_single(web_client_with_fake_provider) -> None:
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "single"
    assert len(body["candidates"]) == 1
    assert body["candidates"][0] == {"move": "parley", "stat": "CHA"}


def test_declare_no_candidates_returns_tier_none(web_client_with_fake_provider) -> None:
    fake = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)

    assert response.status_code == 200
    body = response.json()
    assert body["tier"] == "none"
    assert body["candidates"] == []


def test_action_declared_event_persists_even_when_classification_fails(
    web_client_with_fake_provider,
) -> None:
    """모델이 닫힌 목록에 없는 무브 이름을 돌려줘 분류가 400으로 실패해도,
    `action_declared` 사건은 이미 기록되어 있다 — 선언이 분류보다 먼저 남는다."""
    fake = FakeProvider(complete_value=json.dumps([{"move": "not_a_real_move", "stat": "STR"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)

        assert response.status_code == 400
        declared = _events_of_type(client, "action_declared")

    assert len(declared) == 1
    assert declared[0]["raw_text"] == "경비병을 설득해 통로를 열어 보려 한다"


def test_ai_invoked_event_caused_by_seq_points_at_declare(
    web_client_with_fake_provider,
) -> None:
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)
        assert response.status_code == 200
        declare_seq = response.json()["declare_seq"]

        declared = _events_of_type(client, "action_declared")
        ai_invoked = _events_of_type(client, "ai_invoked")

    assert declared[0]["seq"] == declare_seq
    assert len(ai_invoked) == 1
    assert ai_invoked[0]["caused_by_seq"] == declare_seq
    assert ai_invoked[0]["agent_role"] == "action_classifier"


def test_empty_raw_text_returns_422(web_client_with_fake_provider) -> None:
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(raw_text=""),
        )
    assert response.status_code == 422


def test_raw_text_over_max_length_returns_422(web_client_with_fake_provider) -> None:
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(raw_text="가" * 2001),
        )
    assert response.status_code == 422


def test_declare_identity_mismatch_returns_403(web_client_with_fake_provider) -> None:
    """08-01 Task 4: 신원 대조(TRUST-02)가 declare()의 맨 앞에 생기면서, 이
    시험의 뜻이 「모르는 캐릭터」에서 「쿠키의 캐릭터와 본문의 캐릭터가
    어긋남」으로 바뀌었다 — 본문의 `character_id`가 알려진 캐릭터인지는
    쿠키 검증을 통과한 뒤에야 확인되므로, 유효한 쿠키(bram)로도 본문이
    다른 값(모르는 캐릭터 포함)이면 403이 먼저 난다. 「모르는 캐릭터」를
    재는 원래 의도는 `select-character`가 400을 내는 것으로 이미
    `test_web_characters.py::test_select_unknown_character_returns_400_and_sets_no_cookie`가
    덮는다.
    """
    fake = FakeProvider()
    with web_client_with_fake_provider(action_classifier=fake) as client:
        _select_character(client, "bram")
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/declare",
            json=_declare_body(character_id="no_such_character"),
        )
    assert response.status_code == 403


def test_prompt_never_carries_clock_advance_count_or_failure_accumulator(
    web_client_with_fake_provider,
) -> None:
    """관측 지표(시계 진행 횟수·판정 실패 누적)가 AI 프롬프트로 새면 안 된다(T-04-16)."""
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client)
    assert response.status_code == 200

    assert len(fake.calls) == 1
    system, _messages = fake.calls[0]
    combined = json.dumps(system, ensure_ascii=False)
    assert "clock_advances" not in combined
    assert "fails_since_clock" not in combined
    assert "시계 진행 횟수" not in combined
    assert "판정 실패 수" not in combined


def test_prompt_carries_the_acting_character_real_stat_names(
    web_client_with_fake_provider,
) -> None:
    """행동한 사람의 실제 캐릭터 상태값이 AI 문맥에 들어간다 — 자리 표시자 적이 아니다."""
    fake = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=fake) as client:
        response = _declare(client, character_id="bram")
    assert response.status_code == 200

    system, _messages = fake.calls[0]
    combined = json.dumps(system, ensure_ascii=False)
    # bram만 갖는 일곱 번째 상태값(방어구) — 자리 표시자 적(장면 대상 칸에는
    # 여전히 등장한다, scene_entities는 이 계획이 바꾸지 않는다)의 "체력"
    # 하나짜리 상태값에는 없는 이름이라, "캐릭터 상태" 칸에 이 값이 있다는
    # 것 자체가 실제 캐릭터 상태값이 넘어왔음을 증명한다.
    assert "방어구" in combined
    assert "캐릭터 상태: 체력 20, STR 2, DEX 0, CON 1, INT -1, WIS 0, CHA 0, 방어구 2" in combined


# ---------------------------------------------------------------------------
# Task 3: 확인 경로
# ---------------------------------------------------------------------------

_NARRATION_TEXT = "문이 요란하게 부서진다. 안에서 서늘한 바람이 흘러나온다."
"""두 문장짜리 결정적인 대역 서사 — `conftest.fake_provider`가 쓰는 것과 같은
문장(이미 문장 경계에서 정확히 둘로 갈라짐이 확인된 텍스트)."""


class _NarrationRaisingProvider:
    """`master_gm.narrate()`의 재시도가 전부 실패하는 상황을 흉내내는 대역.

    `stream()`을 부르면 즉시 예외를 던지는 제너레이터를 돌려준다 — `classify()`가
    쓰는 `complete()`는 이 시험에서 안 쓰이므로 구현하지 않는다.
    """

    name = "fake-narration-failure"

    def __init__(self) -> None:
        self.calls: list[tuple[list[dict], list[dict]]] = []
        self._last_result: AgentResult | None = None

    def list_models(self) -> list[str]:
        return ["fake-model"]

    def complete(self, **kwargs):  # pragma: no cover - narrate()만 쓰는 대역, classify() 경로는 안 씀
        raise NotImplementedError

    def stream(self, *, model, system, messages, max_tokens, timeout_s):
        self.calls.append((system, messages))

        def _boom():
            raise RuntimeError("제공자 스트림이 죽었다")
            yield  # pragma: no cover - 절대 도달하지 않는다, 제너레이터 형태만 유지

        return _boom()

    def last_result(self) -> AgentResult:
        if self._last_result is None:
            raise RuntimeError("stream()을 먼저 불러야 last_result()를 부를 수 있다")
        return self._last_result

    def note_result(self, result: AgentResult) -> None:
        self._last_result = result


class _SwitchableProvider:
    """`Provider` 프로토콜을 만족하면서 매 호출마다 `self.current`가 가리키는
    실제 대역으로 위임한다 — 재시도 시험에서 첫 요청은 실패하는 대역, 두 번째
    요청은 성공하는 대역을 같은 `master_gm` 자리에 순서대로 물릴 때 쓴다
    (08-03 Task 2). 픽스처 공장(`web_client_with_fake_provider`) 자체는
    고치지 않는다 — 이 대역은 시험 파일 안에서만 산다."""

    name = "fake-switchable"

    def __init__(self, current) -> None:
        self.current = current

    def list_models(self) -> list[str]:
        return self.current.list_models()

    def complete(self, **kwargs):
        return self.current.complete(**kwargs)

    def stream(self, **kwargs):
        return self.current.stream(**kwargs)

    def last_result(self):
        return self.current.last_result()

    def note_result(self, result) -> None:
        self.current.note_result(result)


def _declare_first(client: TestClient, **overrides) -> int:
    response = _declare(client, **overrides)
    assert response.status_code == 200
    return response.json()["declare_seq"]


def _confirm_body(declare_seq: int, **overrides) -> dict:
    body = {
        "player_id": "p1",
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


def test_confirm_rejected_produces_no_check_resolved_event(web_client_with_fake_provider) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(declare_seq, confirmed=False),
        )
        assert response.status_code == 200
        resolved = _events_of_type(client, "check_resolved")
        narrations = _events_of_type(client, "narration_appended")

    body = response.json()
    assert body["confirmed"] is False
    assert body["resolve_seq"] is None
    assert body["narration_chunk_count"] == 0
    assert resolved == []
    assert narrations == []


def test_confirm_identity_mismatch_returns_403_and_no_confirm_event(
    web_client_with_fake_provider,
) -> None:
    """08-01 Task 4: 신원 대조(TRUST-02)가 confirm()의 맨 앞에 생기면서, 이
    시험의 뜻이 「모르는 캐릭터」에서 「쿠키의 캐릭터와 본문의 캐릭터가
    어긋남」으로 바뀌었다. 검증은 여전히 사건을 기록하기 전에 끝난다(CR-01,
    D-04) — 「모르는 캐릭터」를 재는 원래 의도는 `select-character`가 400을
    내는 것으로 이미
    `test_web_characters.py::test_select_unknown_character_returns_400_and_sets_no_cookie`가
    덮는다.
    """
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=classifier) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(declare_seq, character_id="no_such_character"),
        )
        assert response.status_code == 403
        confirmed = _events_of_type(client, "action_confirmed")

    assert confirmed == []


def test_confirm_accepted_check_resolved_caused_by_confirm_seq(web_client_with_fake_provider) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        confirm_seq = response.json()["confirm_seq"]
        confirmed_events = _events_of_type(client, "action_confirmed")
        resolved = _events_of_type(client, "check_resolved")

    assert len(confirmed_events) == 1
    assert confirmed_events[0]["seq"] == confirm_seq
    assert len(resolved) == 1
    assert resolved[0]["caused_by_seq"] == confirm_seq


def test_check_resolved_seq_precedes_every_narration_appended_seq(
    web_client_with_fake_provider,
) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        resolved = _events_of_type(client, "check_resolved")
        narrations = _events_of_type(client, "narration_appended")

    assert len(resolved) == 1
    assert narrations
    check_seq = resolved[0]["seq"]
    assert all(check_seq < narration["seq"] for narration in narrations)


def test_two_sentence_narration_produces_two_chunked_events(web_client_with_fake_provider) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        assert response.json()["narration_chunk_count"] == 2
        narrations = sorted(
            _events_of_type(client, "narration_appended"), key=lambda event: event["chunk_index"]
        )

    assert [narration["chunk_index"] for narration in narrations] == [0, 1]


def test_narration_failure_returns_roll_result_and_records_master_gm_ai_call(
    web_client_with_fake_provider,
) -> None:
    """뜻이 바뀐 시험(08-03 Task 2) — 서사만 실패하면 502가 아니라 200이고,
    이미 굴린 판정 결과(rolls)가 그대로 담겨 돌아온다(D-08, TRUST-06).
    `ai_invoked` 하나 단언은 그대로 남는다(그 성질은 안 바뀐다)."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = _NarrationRaisingProvider()
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert response.status_code == 200
        body = response.json()

        ai_calls = [
            event
            for event in _events_of_type(client, "ai_invoked")
            if event["agent_role"] == "master_gm"
        ]
        resolved = _events_of_type(client, "check_resolved")
        illustrated = _events_of_type(client, "scene_illustrated")

    assert body["narration_failed"] is True
    assert body["rolls"] is not None
    assert body["grade"] is not None
    assert body["target"] is not None
    assert len(ai_calls) == 1
    # 판정 값이 되읽은 사건과 글자 그대로 같다.
    assert body["rolls"] == list(resolved[0]["rolls"])
    # 서사가 실패한 턴에는 삽화가 만들어지지 않는다(기존 성질 유지).
    assert illustrated == []


def test_narration_retry_reuses_roll_and_only_narration_appended_grows(
    web_client_with_fake_provider,
) -> None:
    """다시 시도를 누르면 이야기만 다시 쓴다(D-09) — 같은 declare_seq로 다시
    확인을 보내면(이번엔 서사가 성공하는 대역) check_resolved 사건은 여전히
    하나이고 rolls가 첫 응답과 글자 그대로 같다. narration_appended 사건만
    새로 늘어나고, action_confirmed 사건은 늘지 않는다."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    failing_gm = _NarrationRaisingProvider()
    switchable = _SwitchableProvider(failing_gm)
    with web_client_with_fake_provider(
        action_classifier=classifier, master_gm=switchable
    ) as client:
        declare_seq = _declare_first(client)
        first_response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert first_response.status_code == 200
        first_body = first_response.json()
        assert first_body["narration_failed"] is True

        confirmed_before = _events_of_type(client, "action_confirmed")
        resolved_before = _events_of_type(client, "check_resolved")
        narrations_before = _events_of_type(client, "narration_appended")

        switchable.current = FakeProvider(stream_text=_NARRATION_TEXT)
        second_response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert second_response.status_code == 200
        second_body = second_response.json()

        confirmed_after = _events_of_type(client, "action_confirmed")
        resolved_after = _events_of_type(client, "check_resolved")
        narrations_after = _events_of_type(client, "narration_appended")

    assert second_body["narration_failed"] is False
    # TRUST-05 + D-09 — check_resolved 사건 수 1과 rolls 동일을 함께 단언한다.
    assert len(resolved_after) == len(resolved_before) == 1
    assert second_body["rolls"] == first_body["rolls"]
    assert len(confirmed_after) == len(confirmed_before) == 1
    assert len(narrations_after) > len(narrations_before)


def test_confirm_different_move_after_confirmed_returns_400_and_appends_nothing(
    web_client_with_fake_provider,
) -> None:
    """이미 확인된 선언에 다른 move로 재확인하면 400이고 사건이 하나도
    늘지 않는다(D-10)."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        first = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm", json=_confirm_body(declare_seq)
        )
        assert first.status_code == 200
        events_before = len(_events(client))

        second = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(
                declare_seq,
                move="defy_danger",
                stat="DEX",
                suggestion_move="defy_danger",
                suggestion_stat="DEX",
            ),
        )
        events_after = len(_events(client))

    assert second.status_code == 400
    assert events_after == events_before


def test_check_submission_failure_returns_error_status_with_no_rolls(
    web_client_with_fake_provider,
) -> None:
    """굴림 실패(판정 제출 자체가 거부됨)는 오류 상태 코드이고 응답에 rolls가
    없다 — 서사 실패(200 + rolls 있음)와 구분된다(TRUST-06)."""
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    with web_client_with_fake_provider(action_classifier=classifier) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(declare_seq, modifiers=["percentage:10:버프"]),
        )

    assert response.status_code == 400
    assert response.json().get("rolls") in (None, [])


def test_confirm_event_keeps_system_suggestion_separate_from_picked_move(
    web_client_with_fake_provider,
) -> None:
    classifier = FakeProvider(complete_value=json.dumps([{"move": "parley", "stat": "CHA"}]))
    gm = FakeProvider(stream_text=_NARRATION_TEXT)
    with web_client_with_fake_provider(action_classifier=classifier, master_gm=gm) as client:
        declare_seq = _declare_first(client)
        response = client.post(
            f"/api/sessions/{SESSION_ID}/actions/confirm",
            json=_confirm_body(
                declare_seq,
                move="defy_danger",
                stat="DEX",
                suggestion_move="parley",
                suggestion_stat="CHA",
            ),
        )
        assert response.status_code == 200
        confirmed_events = _events_of_type(client, "action_confirmed")

    assert confirmed_events[0]["system_suggestion"] == {"move": "parley", "stat": "CHA"}
    assert confirmed_events[0]["move"] == "defy_danger"
    assert confirmed_events[0]["stat"] == "DEX"
