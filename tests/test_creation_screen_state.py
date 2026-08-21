"""12.3-02 — GM의 나머지 세 마디를 사건으로 남기고(Task 1), 만들기 진행
상태를 폴링 응답에 싣고(Task 2), 룰북 만들기 항목 선언 전용 경로를 시험한다
(Task 3).

`tests/test_creation_screen_tracer.py`의 조립 방식(`web_client_with_fake_provider`
+ `conftest.FakeProvider`)을 그대로 따른다.
"""

import dataclasses
import json
import time

from conftest import FakeProvider

from gptrpg.rules_core.reducer import CreationGmLineFold, GameState
from gptrpg.web import creation_state

SESSION_ID = "creation-screen-state-s1"
CHARACTER_ID = "hero-1"
BROWSER_ID = "b-hero-1"


def _fix_party_size(
    client, *, count: int = 3, browser_id: str = "", session_id: str = SESSION_ID
):
    return client.post(
        f"/api/sessions/{session_id}/creation/party-size",
        json={
            "player_character_count": count,
            "rulebook_id": "dungeonworld_like",
            "browser_id": browser_id,
        },
    )


def _claim_host(client, *, character_id: str, browser_id: str, session_id: str = SESSION_ID):
    """방장 잡기(D-11)이자 재실 신호 — 12.3-06부터는 `character_id`도
    함께 실어 서버가 「지금 누가 와 있는가」를 안다(D-06 갈래 ①)."""
    return client.post(
        f"/api/sessions/{session_id}/creation/host",
        json={"browser_id": browser_id, "character_id": character_id},
    )


def _submit_step(
    client,
    *,
    character_id: str,
    browser_id: str,
    step_id: str,
    session_id: str = SESSION_ID,
    **payload,
):
    return client.post(
        f"/api/sessions/{session_id}/creation/step",
        json={
            "character_id": character_id,
            "browser_id": browser_id,
            "step_id": step_id,
            "rulebook_id": "dungeonworld_like",
            **payload,
        },
    )


def _submit_name_step(
    client,
    *,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    text_value: str = "브람",
    session_id: str = SESSION_ID,
):
    return _submit_step(
        client,
        character_id=character_id,
        browser_id=browser_id,
        step_id="name",
        session_id=session_id,
        text_value=text_value,
    )


def _complete_all_required_steps(
    client,
    *,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    session_id: str = SESSION_ID,
):
    """던전월드류 대본의 필수 항목 전부(archetype/backstory/ability_array/hp/name)를
    채운다 — `tests/test_creation_gm.py`와 같은 흐름."""
    for step_id, payload in (
        ("archetype", {"picked": ["몸으로 먼저 막아선다"]}),
        ("backstory", {"text_value": "우물 마을 순찰대에 뒤늦게 합류한 떠돌이 검객"}),
        (
            "ability_array",
            {
                "axis_values": [
                    {"axis_name": "STR", "value": 2},
                    {"axis_name": "DEX", "value": 1},
                    {"axis_name": "CON", "value": 1},
                    {"axis_name": "INT", "value": 0},
                    {"axis_name": "WIS", "value": 0},
                    {"axis_name": "CHA", "value": -1},
                ]
            },
        ),
        ("hp", {}),
    ):
        response = _submit_step(
            client,
            character_id=character_id,
            browser_id=browser_id,
            step_id=step_id,
            session_id=session_id,
            **payload,
        )
        assert response.status_code == 200, response.text
    assert (
        _submit_name_step(
            client, character_id=character_id, browser_id=browser_id, session_id=session_id
        ).status_code
        == 200
    )


def _complete_creation(
    client,
    *,
    character_id: str = CHARACTER_ID,
    browser_id: str = BROWSER_ID,
    session_id: str = SESSION_ID,
    one_line_intro: str = "브람은 조용한 마을을 떠나온 모험가다.",
):
    return client.post(
        f"/api/sessions/{session_id}/creation/complete",
        json={
            "character_id": character_id,
            "browser_id": browser_id,
            "rulebook_id": "dungeonworld_like",
            "one_line_intro": one_line_intro,
        },
    )


def _nominate(client, *, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/nominate",
        json={"rulebook_id": "dungeonworld_like"},
    )


def _follow_up(client, *, character_id: str = CHARACTER_ID, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/follow-up",
        json={"character_id": character_id, "rulebook_id": "dungeonworld_like"},
    )


def _wrap_up(client, *, session_id: str = SESSION_ID):
    return client.post(
        f"/api/sessions/{session_id}/creation/wrap-up",
        json={"rulebook_id": "dungeonworld_like"},
    )


def _events_of_type(client, event_type: str, *, session_id: str = SESSION_ID) -> list[dict]:
    response = client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert response.status_code == 200
    return [event for event in response.json()["events"] if event["event_type"] == event_type]


# ---------------------------------------------------------------------------
# Task 1 — nominate/follow-up/wrap-up이 announce와 같은 모양으로 사건에 남고
# 서버가 한 번만 낸다(D-02/D-12).
# ---------------------------------------------------------------------------


def test_nominate_records_a_single_creation_gm_spoke_event(web_client_with_fake_provider):
    provider = FakeProvider(complete_value="[]")  # 계약 위반 -> 후보 첫 번째로 폴백
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-nominate-once"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        response = _nominate(client, session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["character_id"] == CHARACTER_ID
        assert isinstance(body["seq"], int)

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert len(events) == 1
        assert events[0]["kind"] == "nominate"
        assert events[0]["target_character_id"] == CHARACTER_ID


def test_nominate_called_twice_in_the_same_state_does_not_call_the_provider_again(
    web_client_with_fake_provider,
):
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-nominate-dedupe"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        first = _nominate(client, session_id=session_id)
        assert first.status_code == 200
        assert len(provider.calls) == 1

        second = _nominate(client, session_id=session_id)
        assert second.status_code == 200
        assert len(provider.calls) == 1  # 다시 부르지 않았다

        assert first.json() == second.json()
        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert len(events) == 1


def test_nominate_records_a_new_event_after_candidate_list_changes(
    web_client_with_fake_provider,
):
    """후보 목록이 실제로 바뀐 뒤(한 사람이 완성된 뒤)에는 새 사건을
    남긴다 — 중복 방지가 진행을 막지 않는다."""
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-nominate-progress"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(
            client, character_id="hero-1", browser_id="b-hero-1", session_id=session_id
        ).status_code == 200

        first = _nominate(client, session_id=session_id)
        assert first.status_code == 200
        assert first.json()["character_id"] == "hero-1"

        _complete_all_required_steps(
            client, character_id="hero-1", browser_id="b-hero-1", session_id=session_id
        )
        assert _complete_creation(
            client, character_id="hero-1", browser_id="b-hero-1", session_id=session_id
        ).status_code == 200
        client.cookies.clear()  # hero-1의 쿠키를 벗어야 hero-2의 항목을 낼 수 있다
        assert _submit_name_step(
            client, character_id="hero-2", browser_id="b-hero-2", session_id=session_id
        ).status_code == 200

        second = _nominate(client, session_id=session_id)
        assert second.status_code == 200
        assert second.json()["character_id"] == "hero-2"
        assert second.json()["seq"] != first.json()["seq"]

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        nominate_events = [event for event in events if event["kind"] == "nominate"]
        assert len(nominate_events) == 2


def test_follow_up_records_a_single_creation_gm_spoke_event_when_needs_more(
    web_client_with_fake_provider,
):
    provider = FakeProvider(
        complete_value=json.dumps([{"needs_more": True, "question": "그때 무슨 소리를 들었나요?"}])
    )
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-once"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        response = _follow_up(client, session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["needs_more"] is True
        assert body["question"]
        assert isinstance(body["seq"], int)

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        follow_up_events = [event for event in events if event["kind"] == "follow_up"]
        assert len(follow_up_events) == 1
        assert follow_up_events[0]["target_character_id"] == CHARACTER_ID


def test_follow_up_called_twice_in_the_same_state_does_not_call_the_provider_again(
    web_client_with_fake_provider,
):
    provider = FakeProvider(
        complete_value=json.dumps([{"needs_more": True, "question": "그때 무슨 소리를 들었나요?"}])
    )
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-dedupe"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        first = _follow_up(client, session_id=session_id)
        assert first.status_code == 200
        assert len(provider.calls) == 1

        second = _follow_up(client, session_id=session_id)
        assert second.status_code == 200
        assert len(provider.calls) == 1

        assert first.json() == second.json()
        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert len([e for e in events if e["kind"] == "follow_up"]) == 1


def test_follow_up_with_no_more_questions_records_no_event(web_client_with_fake_provider):
    """GM이 되묻지 않기로 하면(`needs_more=False`) 대화 줄기에 남길 말이
    없으므로 사건을 안 남긴다(D-02 ④)."""
    provider = FakeProvider(complete_value=json.dumps([{"needs_more": False, "question": None}]))
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-none"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200

        response = _follow_up(client, session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["needs_more"] is False
        assert body["question"] is None
        assert body["seq"] is None

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert [e for e in events if e["kind"] == "follow_up"] == []


def test_follow_up_rejects_mismatched_character_id_with_403_and_records_no_event(
    web_client_with_fake_provider,
):
    provider = FakeProvider(
        complete_value=json.dumps([{"needs_more": True, "question": "..."}])
    )
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-followup-403"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        _complete_all_required_steps(
            client, character_id="hero-1", browser_id="b-hero-1", session_id=session_id
        )
        assert _complete_creation(
            client, character_id="hero-1", browser_id="b-hero-1", session_id=session_id
        ).status_code == 200
        assert client.cookies.get("gptrpg_character") is not None

        response = _follow_up(client, character_id="hero-2", session_id=session_id)
        assert response.status_code == 403

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert [e for e in events if e["kind"] == "follow_up"] == []


# ---------------------------------------------------------------------------
# 12.3-06 — 첫 지목 교착 gap 닫기(D-06). 아무도 아직 항목을 하나도 안 낸
# 완전히 새 세션에서도 지목이 성공해야 한다.
# ---------------------------------------------------------------------------


def test_nominate_after_party_size_fixed_works_with_no_prior_step_submission(
    web_client_with_fake_provider,
):
    """CHAR-06 gap(12.3-VERIFICATION.md 2차) — 지목 후보 목록의 유일한
    출처가 「이미 항목을 낸 사람」이면, 완전히 새 세션에는 그런 사람이
    있을 수 없어 지목이 영원히 안 일어난다(닭이 먼저냐 달걀이 먼저냐).
    `_submit_name_step`을 의도적으로 안 쓴다 — 화면이 실제로 밟는 경로
    (재실 신호 -> 인원 확정 -> 안내 -> 지목)만 밟는다. 세션 식별자를 이
    시험 전용으로 새로 두는 이유: 재실 표(`_character_last_seen`)가
    모듈 수준 전역이라 session_id로만 격리된다."""
    provider = FakeProvider(complete_value="[]")  # 계약 위반 -> 후보 첫 번째로 폴백
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-bootstrap-nominate"
        browser_id = "b-bootstrap-1"
        character_id = "pc-bootstrap-1"

        assert (
            _claim_host(
                client, character_id=character_id, browser_id=browser_id, session_id=session_id
            ).status_code
            == 200
        )
        assert (
            _fix_party_size(client, browser_id=browser_id, session_id=session_id).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/sessions/{session_id}/creation/announce",
                json={"rulebook_id": "dungeonworld_like"},
            ).status_code
            == 200
        )

        response = _nominate(client, session_id=session_id)
        assert response.status_code == 200
        assert response.json()["character_id"] == character_id

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        nominate_events = [e for e in events if e["kind"] == "nominate"]
        assert len(nominate_events) == 1


def test_nominate_moves_to_the_next_present_participant_after_the_first_one_finishes(
    web_client_with_fake_provider,
):
    """T-12.3-20 회귀 그물 — `_gm_dedupe_key`가 후보 목록과 따로 계산되면
    이 시험이 무너진다: 첫 사람이 완성돼 candidates가 바뀌었는데 키가 그걸
    안 반영하면 두 번째 지목이 첫 번째 기록을 그대로 재사용해, 이미
    완성된 사람을 다시 가리키는 채로 같은 교착이 되돌아온다. 이 그물이
    무엇을 잡는지는 이름만으로 안 보이므로 여기 적는다."""
    provider = FakeProvider(complete_value="[]")  # 계약 위반 -> 후보 첫 번째로 폴백
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-next-participant"
        browsers = {"pc-a1": "b-a1", "pc-a2": "b-a2", "pc-a3": "b-a3"}
        for character_id, browser_id in browsers.items():
            assert (
                _claim_host(
                    client,
                    character_id=character_id,
                    browser_id=browser_id,
                    session_id=session_id,
                ).status_code
                == 200
            )

        host_browser_id = next(iter(browsers.values()))
        assert (
            _fix_party_size(
                client, browser_id=host_browser_id, session_id=session_id
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/sessions/{session_id}/creation/announce",
                json={"rulebook_id": "dungeonworld_like"},
            ).status_code
            == 200
        )

        first = _nominate(client, session_id=session_id)
        assert first.status_code == 200
        first_target = first.json()["character_id"]
        assert first_target in browsers

        _complete_all_required_steps(
            client,
            character_id=first_target,
            browser_id=browsers[first_target],
            session_id=session_id,
        )
        assert (
            _complete_creation(
                client,
                character_id=first_target,
                browser_id=browsers[first_target],
                session_id=session_id,
            ).status_code
            == 200
        )
        client.cookies.clear()  # 다음 지목은 신원을 안 보므로 필수는 아니지만 위생상 비운다

        second = _nominate(client, session_id=session_id)
        assert second.status_code == 200
        second_target = second.json()["character_id"]
        assert second_target != first_target
        assert second_target in browsers

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        nominate_events = [e for e in events if e["kind"] == "nominate"]
        assert len(nominate_events) == 2


def test_nominate_candidates_never_exceed_the_remaining_party_size(
    web_client_with_fake_provider,
):
    """T-12.3-17 상한 회귀 그물 — 재실 신호는 브라우저가 스스로 신고하는
    값이라 위조될 수 있다. `present_candidates`가 남은 자리 수로 뒤쪽
    (재실에서 나온) 항목만 자르는지, 그리고 남은 자리가 후보 수와
    정확히 같을 때는(adjacency 경계) 전부 들어오는지 직접 확인한다.
    던전월드류의 인원 하한이 3이라(`DUNGEONWORLD_PARTY_SIZE_RANGE`) 인원을
    3으로 고정하고 신호 수 쪽을 바꿔 두 경우를 가른다."""
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        # 경우 1 — 재실 신호 다섯, 남은 자리 셋: 후보가 셋을 못 넘는다.
        session_over = SESSION_ID + "-cap-over"
        for i in range(5):
            assert (
                _claim_host(
                    client,
                    character_id=f"pc-over-{i}",
                    browser_id=f"b-over-{i}",
                    session_id=session_over,
                ).status_code
                == 200
            )
        assert (
            _fix_party_size(
                client, count=3, browser_id="b-over-0", session_id=session_over
            ).status_code
            == 200
        )

        state = client.app.state.registry.get_or_create(session_over).state
        candidates = creation_state.present_candidates(state, session_over)
        assert len(candidates) == 3

        # 경우 2 — 재실 신호 셋, 남은 자리도 정확히 셋: 전부 들어온다.
        session_exact = SESSION_ID + "-cap-exact"
        for i in range(3):
            assert (
                _claim_host(
                    client,
                    character_id=f"pc-exact-{i}",
                    browser_id=f"b-exact-{i}",
                    session_id=session_exact,
                ).status_code
                == 200
            )
        assert (
            _fix_party_size(
                client, count=3, browser_id="b-exact-0", session_id=session_exact
            ).status_code
            == 200
        )

        state = client.app.state.registry.get_or_create(session_exact).state
        exact_candidates = creation_state.present_candidates(state, session_exact)
        assert len(exact_candidates) == 3
        # 탐침 ordering — 같은 상태를 연달아 두 번 물으면 같은 순서가 나온다.
        assert creation_state.present_candidates(state, session_exact) == exact_candidates


def test_ghost_presence_signals_do_not_permanently_push_out_real_participants(
    web_client_with_fake_provider,
):
    """3차 검증(12.3-VERIFICATION.md §「새로 확인한 결함 (3차) — CR-01,
    재현으로 독립 확인」)이 스크래치 스크립트로 돌린 재현을 그대로
    옮긴다. `present_candidates`를 직접 부른다(라우트를 안 거친다 —
    정원 2를 던전월드류의 인원 하한 3 없이 만들 수 있는 유일한 길이다).

    **왜 12.3-06의 시험 넷이 이걸 못 잡았는지:** 그 넷은 전부 같은 모양의
    정상 신호만 먹인다(`test_nominate_candidates_never_exceed_the_remaining_
    party_size`의 다섯 신호도 `pc-over-0`..`pc-over-4`로 전부 같다) —
    신원을 지어낸 경로를 한 번도 밟지 않는다. 개수만 세는 단언은 개수만
    지킨다."""
    session_id = SESSION_ID + "-ghost-presence"
    creation_state.mark_character_present(session_id, "ghost-1")
    creation_state.mark_character_present(session_id, "ghost-2")
    creation_state.mark_character_present(session_id, "real-1")
    creation_state.mark_character_present(session_id, "real-2")

    state = GameState(session_id=session_id, party_size_fixed=2)

    # t=0의 상태를 있는 그대로 못박는다 — 이 시점에는 서버가 넷을 가를
    # 정보를 하나도 안 가진다(쿠키는 캐릭터 완성 시점에 구워진다). 이것은
    # 고칠 수 있는 결함이 **아니라** 불가피한 상태다(12.3-08-PLAN.md
    # planner_assumptions ②) — 다음 리뷰가 이 단언을 결함으로 오해하지
    # 않게 여기 남긴다.
    candidates = creation_state.present_candidates(state, session_id)
    assert "real-1" not in candidates
    assert "real-2" not in candidates

    # 가짜 둘이 차례를 흘려보내면 진짜 참가자가 들어온다.
    for seq, ghost_id in ((1, "ghost-1"), (2, "ghost-2")):
        state = dataclasses.replace(
            state,
            creation_gm_said={
                "nominate:ghost": CreationGmLineFold(
                    seq=seq, kind="nominate", say="", target_character_id=ghost_id
                )
            },
        )
        creation_state.forfeited_nominee(state, session_id)  # 관측 기록을 찍는다.
        key = (session_id, ghost_id)
        watermark_seq, _started_at = creation_state._nomination_watermark[key]
        creation_state._nomination_watermark[key] = (
            watermark_seq,
            time.monotonic() - creation_state.NOMINATION_IDLE_S - 5,
        )
        assert creation_state.forfeited_nominee(state, session_id) == ghost_id

    # 최종 상태 — 진짜 참가자 둘이 정확히 후보 전부다.
    assert creation_state.present_candidates(state, session_id) == ("real-1", "real-2")


def test_a_nominee_that_keeps_submitting_values_never_loses_the_turn(
    web_client_with_fake_provider,
):
    """이 시험이 지키는 것은 「회복이 진짜 참가자를 벌하는 도구가 되지
    않는다」이고, 그것이 왜 이 계획에서 가장 중요한 경계인지가 이유다.
    자기 차례에 항목 값을 계속 내고 있는 사람은 제출마다 관측 순번이
    앞으로 밀려 시계가 다시 맞춰지므로, 회복 시계가 아무리 흘러도
    차례를 안 뺏긴다."""
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-keeps-submitting"
        browsers = {"pc-keep-1": "b-keep-1", "pc-keep-2": "b-keep-2", "pc-keep-3": "b-keep-3"}
        for character_id, browser_id in browsers.items():
            assert (
                _claim_host(
                    client,
                    character_id=character_id,
                    browser_id=browser_id,
                    session_id=session_id,
                ).status_code
                == 200
            )
        assert (
            _fix_party_size(
                client, count=3, browser_id="b-keep-1", session_id=session_id
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/sessions/{session_id}/creation/announce",
                json={"rulebook_id": "dungeonworld_like"},
            ).status_code
            == 200
        )

        nomination = _nominate(client, session_id=session_id)
        assert nomination.status_code == 200
        nominee = nomination.json()["character_id"]
        assert nominee in browsers

        state = _poll_state(client, session_id=session_id)
        assert state["creation_current_speaker_id"] == nominee

        seq, _started_at = creation_state._nomination_watermark[(session_id, nominee)]
        creation_state._nomination_watermark[(session_id, nominee)] = (
            seq,
            time.monotonic() - creation_state.NOMINATION_IDLE_S - 5,
        )

        assert (
            _submit_step(
                client,
                character_id=nominee,
                browser_id=browsers[nominee],
                step_id="name",
                session_id=session_id,
                text_value="여전히 쓰는 중",
            ).status_code
            == 200
        )

        state = _poll_state(client, session_id=session_id)
        assert state["creation_current_speaker_id"] == nominee


def test_a_restart_of_the_watermark_table_never_releases_a_nomination_immediately(
    web_client_with_fake_provider,
):
    """T-12.3-13과 같은 규율 — 관측 기록이 빈 상태를 「오래 조용했다」로
    오판하면 재시작마다 멀쩡한 차례가 날아간다. 재시작 직후에는 관측을
    처음부터 다시 시작해야지, 곧바로 풀리면 안 된다."""
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-watermark-restart"
        browsers = {
            "pc-restart-1": "b-restart-1",
            "pc-restart-2": "b-restart-2",
            "pc-restart-3": "b-restart-3",
        }
        for character_id, browser_id in browsers.items():
            assert (
                _claim_host(
                    client,
                    character_id=character_id,
                    browser_id=browser_id,
                    session_id=session_id,
                ).status_code
                == 200
            )
        assert (
            _fix_party_size(
                client, count=3, browser_id="b-restart-1", session_id=session_id
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/sessions/{session_id}/creation/announce",
                json={"rulebook_id": "dungeonworld_like"},
            ).status_code
            == 200
        )

        nomination = _nominate(client, session_id=session_id)
        assert nomination.status_code == 200
        nominee = nomination.json()["character_id"]
        assert nominee in browsers

        state = _poll_state(client, session_id=session_id)
        assert state["creation_current_speaker_id"] == nominee

        # 프로세스 재시작 재현 — 관측 기록만 통째로 지운다(GameState는
        # 사건에서 다시 접히므로 지목은 그대로다).
        creation_state._nomination_watermark.pop((session_id, nominee), None)
        for character_id in browsers:
            creation_state._character_last_seen.pop((session_id, character_id), None)

        state = _poll_state(client, session_id=session_id)
        assert state["creation_current_speaker_id"] == nominee


def test_nominate_without_any_presence_signal_is_still_rejected_and_records_no_event(
    web_client_with_fake_provider,
):
    """탐침 empty 해소 — 재실 신호를 보낸 사람도 항목을 낸 사람도 없으면
    지목할 대상이 진짜로 없다. 빈 후보 목록이 조용히 통과하지 않는다."""
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-no-presence"
        assert _fix_party_size(client, session_id=session_id).status_code == 200

        response = _nominate(client, session_id=session_id)
        assert response.status_code == 409

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert [e for e in events if e["kind"] == "nominate"] == []


# ---------------------------------------------------------------------------
# Task 2 — 만들기 진행 상태를 폴링 응답에 싣는다(D-04).
# ---------------------------------------------------------------------------


def _poll_state(client, *, session_id: str = SESSION_ID) -> dict:
    response = client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert response.status_code == 200
    return response.json()["state"]


def test_poll_state_reports_party_size_and_unfinished_candidates(
    web_client_with_fake_provider,
):
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-poll-unfinished"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200
        assert _submit_step(
            client,
            character_id=CHARACTER_ID,
            browser_id=BROWSER_ID,
            step_id="archetype",
            session_id=session_id,
            picked=["몸으로 먼저 막아선다"],
        ).status_code == 200

        state = _poll_state(client, session_id=session_id)
        assert state["party_size_fixed"] == 3
        assert state["creation_rulebook_id"] == "dungeonworld_like"
        assert state["creation_unfinished_character_ids"] == [CHARACTER_ID]


def test_poll_state_current_speaker_clears_once_that_person_finishes(
    web_client_with_fake_provider,
):
    provider = FakeProvider(complete_value="[]")  # 계약 위반 -> 후보 첫 번째로 폴백
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-poll-speaker"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(client, session_id=session_id).status_code == 200
        assert _nominate(client, session_id=session_id).status_code == 200

        state = _poll_state(client, session_id=session_id)
        assert state["creation_current_speaker_id"] == CHARACTER_ID

        _complete_all_required_steps(client, session_id=session_id)
        assert _complete_creation(client, session_id=session_id).status_code == 200

        state = _poll_state(client, session_id=session_id)
        assert state["creation_current_speaker_id"] is None


def test_a_stalled_nomination_is_released_and_the_next_one_lands_on_someone_else(
    web_client_with_fake_provider,
):
    """3차 검증이 코드 실행으로 재현한 새 교착(12.3-VERIFICATION.md
    `missing` ②) — 가짜 식별자가 지목되면 그 지목은 완성돼야만 풀리는데
    가짜는 완성될 수 없어 `creation_current_speaker_id`가 영원히
    고정된다(회복 경로가 코드 어디에도 없었다). 이 시험은 그 회복
    경로가 서버 함수(`forfeited_nominee`)부터 폴링 응답까지 끝에서
    끝까지 이어지는지 확인한다.

    시간은 `_nomination_watermark`의 시각만 되감아 흘려보낸다(실제로
    잠들지 않는다) — `test_idle_host_is_succeeded_by_another_browser_
    and_cannot_reclaim`(test_creation_consent_host.py)과 같은 관례다."""
    provider = FakeProvider(complete_value="[]")  # 계약 위반 -> candidates[0] 폴백
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-stalled-nomination"
        # 가짜가 먼저 도착하는 것이 이 결함의 모양이다(T-12.3-21).
        for character_id, browser_id in (
            ("pc-stall-ghost", "b-stall-ghost"),
            ("pc-stall-1", "b-stall-1"),
            ("pc-stall-2", "b-stall-2"),
        ):
            assert (
                _claim_host(
                    client,
                    character_id=character_id,
                    browser_id=browser_id,
                    session_id=session_id,
                ).status_code
                == 200
            )
        assert (
            _fix_party_size(
                client, count=3, browser_id="b-stall-ghost", session_id=session_id
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/sessions/{session_id}/creation/announce",
                json={"rulebook_id": "dungeonworld_like"},
            ).status_code
            == 200
        )

        first = _nominate(client, session_id=session_id)
        assert first.status_code == 200
        assert first.json()["character_id"] == "pc-stall-ghost"

        # 이 폴링이 관측 기록(`_nomination_watermark`)을 처음 찍는다.
        state = _poll_state(client, session_id=session_id)
        assert state["creation_current_speaker_id"] == "pc-stall-ghost"

        # 순번은 그대로 두고 시각만 되감아 "흘려보냈다"를 재현한다.
        seq, _started_at = creation_state._nomination_watermark[
            (session_id, "pc-stall-ghost")
        ]
        creation_state._nomination_watermark[(session_id, "pc-stall-ghost")] = (
            seq,
            time.monotonic() - creation_state.NOMINATION_IDLE_S - 5,
        )

        state = _poll_state(client, session_id=session_id)
        assert state["creation_current_speaker_id"] is None

        second = _nominate(client, session_id=session_id)
        assert second.status_code == 200
        second_target = second.json()["character_id"]
        assert second_target != "pc-stall-ghost"
        assert second_target in ("pc-stall-1", "pc-stall-2")

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        nominate_events = [e for e in events if e["kind"] == "nominate"]
        assert len(nominate_events) == 2


def test_poll_state_lists_completed_character_with_consent_false(
    web_client_with_fake_provider,
):
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-poll-characters"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        _complete_all_required_steps(client, session_id=session_id)
        assert _complete_creation(client, session_id=session_id).status_code == 200

        state = _poll_state(client, session_id=session_id)
        assert len(state["creation_characters"]) == 1
        character = state["creation_characters"][0]
        assert character["character_id"] == CHARACTER_ID
        assert character["display_name"]
        assert character["consented"] is False
        assert character["required_steps_filled"] is True


def test_poll_state_step_values_keep_only_the_latest_submission_and_omit_browser_id(
    web_client_with_fake_provider,
):
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-poll-values"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        assert _submit_name_step(
            client, text_value="브람", session_id=session_id
        ).status_code == 200
        assert _submit_name_step(
            client, text_value="브람 2세", session_id=session_id
        ).status_code == 200

        state = _poll_state(client, session_id=session_id)
        name_values = [v for v in state["creation_step_values"] if v["step_id"] == "name"]
        assert len(name_values) == 1
        assert name_values[0]["text_value"] == "브람 2세"
        assert name_values[0]["character_id"] == CHARACTER_ID
        assert "browser_id" not in name_values[0]

        raw_state_text = json.dumps(state)
        assert "browser_id" not in raw_state_text
        assert "host_browser_id" not in state


def test_poll_state_before_any_rulebook_chosen_returns_200_with_empty_defaults(
    web_client,
):
    session_id = SESSION_ID + "-poll-empty"
    response = web_client.get(f"/api/sessions/{session_id}/events", params={"from_seq": 0})
    assert response.status_code == 200
    state = response.json()["state"]
    assert state["party_size_fixed"] is None
    assert state["creation_rulebook_id"] is None
    assert state["party_roster"] is None
    assert state["creation_unfinished_character_ids"] == []
    assert state["creation_current_speaker_id"] is None
    assert state["creation_characters"] == []
    assert state["creation_reopened_step_ids"] == []
    assert state["creation_step_values"] == []
    assert state["creation_host_claimed"] is False


def test_wrap_up_records_a_single_creation_gm_spoke_event(web_client_with_fake_provider):
    provider = FakeProvider(complete_value="[]")  # 계약 위반 -> 기본 정리 문구로 폴백
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-wrapup-once"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        _complete_all_required_steps(client, session_id=session_id)
        assert _complete_creation(client, session_id=session_id).status_code == 200

        response = _wrap_up(client, session_id=session_id)
        assert response.status_code == 200
        body = response.json()
        assert body["say"]
        assert isinstance(body["seq"], int)
        assert {intro["character_id"] for intro in body["intros"]} == {CHARACTER_ID}

        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        wrap_up_events = [event for event in events if event["kind"] == "wrap_up"]
        assert len(wrap_up_events) == 1


def test_wrap_up_called_twice_in_the_same_state_does_not_call_the_provider_again(
    web_client_with_fake_provider,
):
    provider = FakeProvider(complete_value="[]")
    with web_client_with_fake_provider(action_classifier=provider) as client:
        session_id = SESSION_ID + "-wrapup-dedupe"
        assert _fix_party_size(client, session_id=session_id).status_code == 200
        _complete_all_required_steps(client, session_id=session_id)
        assert _complete_creation(client, session_id=session_id).status_code == 200

        first = _wrap_up(client, session_id=session_id)
        assert first.status_code == 200
        assert len(provider.calls) == 1

        second = _wrap_up(client, session_id=session_id)
        assert second.status_code == 200
        assert len(provider.calls) == 1

        assert first.json() == second.json()
        events = _events_of_type(client, "creation_gm_spoke", session_id=session_id)
        assert len([e for e in events if e["kind"] == "wrap_up"]) == 1


# ---------------------------------------------------------------------------
# Task 3 — 룰북 만들기 항목 선언을 내려주는 전용 경로(D-05).
# ---------------------------------------------------------------------------


def _fetch_creation_steps(client, *, rulebook_id: str, session_id: str = SESSION_ID):
    return client.get(
        f"/api/sessions/{session_id}/creation/steps",
        params={"rulebook_id": rulebook_id},
    )


def test_creation_steps_for_dungeonworld_matches_declaration_order(web_client):
    from gptrpg.rulebooks.dungeonworld_like import DUNGEONWORLD_CREATION_STEPS

    response = _fetch_creation_steps(web_client, rulebook_id="dungeonworld_like")
    assert response.status_code == 200
    step_ids = [step["step_id"] for step in response.json()]
    assert step_ids == [decl.step_id for decl in DUNGEONWORLD_CREATION_STEPS]


def test_creation_steps_for_cairn_carries_dice_expr(web_client):
    response = _fetch_creation_steps(web_client, rulebook_id="cairn")
    assert response.status_code == 200
    steps_by_id = {step["step_id"]: step for step in response.json()}
    assert steps_by_id["abilities"]["dice_expr"] == "3d6"
    assert steps_by_id["hit_protection"]["dice_expr"] == "1d6"


def test_creation_steps_for_openquest_carries_point_budget(web_client):
    response = _fetch_creation_steps(web_client, rulebook_id="openquest")
    assert response.status_code == 200
    steps_by_id = {step["step_id"]: step for step in response.json()}
    resistances = steps_by_id["skills_resistances"]
    assert resistances["point_budget"] == 50
    assert resistances["per_target_max"] == 30


def test_creation_steps_with_unknown_rulebook_returns_400_with_detail(web_client):
    response = _fetch_creation_steps(web_client, rulebook_id="does-not-exist")
    assert response.status_code == 400
    assert response.json()["detail"]


def test_creation_steps_response_never_carries_per_character_progress(web_client):
    """D-05 경계 — 이 응답 어디에도 캐릭터별 진행 값(`creation_step_values`
    유래 값)이 없다. 응답은 목록(선언)이지 진행 상태(딕셔너리 키가
    character_id인 값)가 아니다."""
    response = _fetch_creation_steps(web_client, rulebook_id="dungeonworld_like")
    assert response.status_code == 200
    steps = response.json()
    assert isinstance(steps, list)
    for step in steps:
        assert set(step.keys()) == {
            "step_id",
            "kind",
            "label",
            "required",
            "provides_display_name",
            "axis_names",
            "options",
            "pick_count",
            "fixed_values",
            "point_budget",
            "per_target_max",
            "dice_expr",
            "derive_base_axis",
            "derive_multiplier",
            "derive_offset",
            "depends_on",
            "default_from",
        }
