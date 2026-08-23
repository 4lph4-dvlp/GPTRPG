"""G-12.3-13 (12.3-UAT.md) — GM의 되물음에 **말로** 답할 수 있는가.

되묻기가 읽는 대화록(`_transcript_for`)은 `GameState`에서 만들어진다.
예전에는 `creation_interjection` 사건이 상태에 아무것도 안 남겨서
(`reducer.py` — `last_seq`만 갱신), 사람이 입력칸에 적은 말이 GM에게
닿을 길이 **원리적으로** 없었다. 게다가 되묻기의 중복방지 키가 그
사람의 마지막 **항목** 순번만 봤으므로, 답을 적어도 키가 안 바뀌어
다시 물으면 같은 질문이 그대로 되돌아왔다.

이 시험은 그 두 갈래를 각각 고정한다.
"""

from gptrpg.rules_core.reducer import (
    CreationInterjectionFold,
    CreationStepFold,
    GameState,
)
from gptrpg.web.routes_creation import _gm_dedupe_key, _transcript_for

CHARACTER_ID = "hero-1"


def _state_with_a_backstory_and(interjections: tuple[CreationInterjectionFold, ...]) -> GameState:
    return GameState(
        session_id="s1",
        creation_step_values={
            (CHARACTER_ID, "backstory"): CreationStepFold(
                seq=10,
                kind="free_text",
                text_value="빚더미에 앉은 백수다",
                picked=None,
                axis_values=None,
                rolls=None,
                browser_id="b-hero-1",
            ),
        },
        creation_interjections=interjections,
    )


def test_a_spoken_answer_reaches_the_transcript_the_gm_reads():
    answer = "그냥 아무것도 없으니 잃을 것도 없지 않은가?"
    state = _state_with_a_backstory_and(
        (CreationInterjectionFold(seq=20, speaker_character_id=CHARACTER_ID, text=answer),)
    )
    transcript = _transcript_for(state, (CHARACTER_ID,))
    assert any(answer in line for line in transcript), (
        "사람이 한 말이 대화록에 없으면 GM은 되물음의 답을 볼 수 없다"
    )
    # 항목 값이 먼저, 답이 나중 — 순번 순서다(답은 질문 뒤에 온다).
    assert "빚더미" in transcript[0]
    assert answer in transcript[-1]


def test_only_that_persons_words_are_in_their_transcript():
    state = _state_with_a_backstory_and(
        (
            CreationInterjectionFold(seq=20, speaker_character_id=CHARACTER_ID, text="내 답"),
            CreationInterjectionFold(seq=21, speaker_character_id="hero-2", text="남의 말"),
        )
    )
    transcript = _transcript_for(state, (CHARACTER_ID,))
    assert any("내 답" in line for line in transcript)
    assert not any("남의 말" in line for line in transcript)


def test_speaking_makes_a_new_follow_up_possible():
    """말을 하나 더 하면 중복방지 키가 바뀐다 — 안 그러면 GM이 같은
    질문만 되돌려줘서 되물음에 답할 길이 구조적으로 막힌다."""
    before = _state_with_a_backstory_and(())
    after = _state_with_a_backstory_and(
        (CreationInterjectionFold(seq=20, speaker_character_id=CHARACTER_ID, text="답"),)
    )
    assert _gm_dedupe_key("follow_up", before, CHARACTER_ID) != _gm_dedupe_key(
        "follow_up", after, CHARACTER_ID
    )


def test_someone_elses_words_do_not_reopen_my_follow_up():
    before = _state_with_a_backstory_and(())
    after = _state_with_a_backstory_and(
        (CreationInterjectionFold(seq=20, speaker_character_id="hero-2", text="남의 말"),)
    )
    assert _gm_dedupe_key("follow_up", before, CHARACTER_ID) == _gm_dedupe_key(
        "follow_up", after, CHARACTER_ID
    )


# ---------------------------------------------------------------------------
# G-12.3-24 — 되묻기에 말로 답하는 사람을 「가만히 있다」로 보면 안 된다.
# ---------------------------------------------------------------------------


def test_speaking_counts_as_progress_so_an_answering_player_is_not_forfeited():
    """회복 시간(D-13)이 보는 진척에 **그 사람이 한 말**도 들어간다.

    항목을 다 채운 사람은 GM의 되물음에 말로 답한다 — 그동안 항목 값은
    하나도 안 늘어난다. 말을 안 세면 열심히 대화 중인 사람이 「가만히
    있다」로 판정되어 차례를 회수당한다. 2026-08-23 시험에서 실제로
    그렇게 됐고, 지목 문장이 남들 대화판에만 뜨고 당사자는 못 보는
    모양으로 나타났다.
    """
    from gptrpg.web.creation_state import nomination_progress_seq

    steps_only = _state_with_a_backstory_and(())
    assert nomination_progress_seq(steps_only, CHARACTER_ID) == 10

    after_speaking = _state_with_a_backstory_and(
        (CreationInterjectionFold(seq=42, speaker_character_id=CHARACTER_ID, text="답"),)
    )
    assert nomination_progress_seq(after_speaking, CHARACTER_ID) == 42, (
        "말이 진척으로 안 세어지면 대화 중인 사람이 흘려보낸 것으로 판정된다"
    )


def test_someone_elses_words_are_not_my_progress():
    from gptrpg.web.creation_state import nomination_progress_seq

    state = _state_with_a_backstory_and(
        (CreationInterjectionFold(seq=42, speaker_character_id="hero-2", text="남의 말"),)
    )
    assert nomination_progress_seq(state, CHARACTER_ID) == 10
