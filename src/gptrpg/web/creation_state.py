"""캐릭터 만들기 진행 상태 계산 — `routes_creation.py`와 `routes_events.py`가
**같은 함수를** 부르는 자리다(D-04, Phase 12.3).

이 모듈이 따로 있는 이유는 `routes_events.py`가 `routes_creation.py`의
비공개 도우미(`_unfinished_candidates`/`_required_steps_filled`)를 찔러 쓰지
않게 하려는 것이다 — 판단이 두 곳에 생기면(한 라우터가 계산을 복제하면)
언젠가 어긋난다(Phase 12.2가 방금 고친 사고). 두 라우터가 같은 함수를
부르면 그 어긋남이 구조적으로 불가능하다.

**`session_actor/actor.py`의 `_unfinished_creation_candidates`가 여전히
따로 있는 이유:** 층 계약(`.importlinter` contract:2, `gptrpg.web`이
`gptrpg.session_actor`보다 위층)상 `session_actor`가 `gptrpg.web`을 import할
수 없다 — 액터도 같은 계산이 필요하므로(동의·명단 잠금 전제 검사) 이 모듈을
가져다 쓰지 못하고 같은 계산을 자기 층에서 다시 한다. 세 번째 사본을 만들지
않는다는 규율은 지키되, 층 경계를 넘는 import는 만들지 않는다.

`_transcript_for`는 이 모듈로 옮기지 않는다 — GM 프롬프트 조립 전용이고
폴링 화면 상태와 무관하다.
"""

import time

from gptrpg.rules_core.reducer import GameState
from gptrpg.rules_core.rulebook import Rulebook

HOST_IDLE_S = 30.0
"""방장이 유휴로 판정되는 문턱(초, D-11). 화면이 15초마다 자기를 알리는
재실 신호(`POST /creation/host`)를 보내는 것을 전제로 잡은 값이다 —
두 배를 두는 이유는 한 번의 폴링 지연이나 네트워크 요동만으로 방장을
잃지 않으려면 최소 두 번은 놓쳐야 하기 때문이다."""

NOMINATION_IDLE_S = 300.0
"""지목된 사람이 만들기 항목 값을 하나도 안 낸 채로 흘려보낸 것으로
판정되는 문턱(초, Phase 12.3-08). `HOST_IDLE_S`(30초)보다 훨씬 큰 이유:
자기소개 서술을 쓰는 사람이 5분 동안 항목 값을 **하나도** 안 내는 일은
없고, 30초로 잡으면 글을 쓰고 있는 진짜 참가자의 편집 화면이 도중에
닫혀 이 값이 고치려는 것보다 나쁜 결함이 된다.

**이 값은 재실 신호가 살아 있는데도 아무것도 안 내는 경우에만 쓴다.**
재실 신호 자체가 `HOST_IDLE_S`를 넘겨 끊긴 경우(탭을 닫고 떠났다)는
`forfeited_nominee`가 그 문턱을 그대로 쓴다 — 12.3-VERIFICATION.md의
`missing` ②가 문자 그대로 `HOST_IDLE_S`를 적었으나 그 값은 재실 신호가
끊긴 갈래에만 안전하다(12.3-08-PLAN.md planner_assumptions ①)."""

_browser_last_seen: dict[tuple[str, str], float] = {}
"""(session_id, browser_id) -> 마지막으로 재실 신호를 받은 시각
(`time.monotonic()` 기준, 벽시계가 아니다 — 이 저장소가 경과 시간을 잴 때
이미 쓰는 관례, `agents/invoke.py` 등).

**이 표가 사건이 아니라 프로세스 메모리인 이유:** 「누가 지금 창을 열어
두고 있나」는 기록할 사실이 아니라 지금 이 순간의 관측값이다 — 사건으로
남기면 15초마다 참가자 수만큼 사건이 쌓인다. 판단은 여전히 서버 한
자리에서만 나지만(D-04와 같은 규율), 그 판단의 재료(재실 여부)까지 전부
사건일 필요는 없다.

**한계 — 단일 프로세스 전제다.** 서버를 재시작하면 이 표가 빈다. 그
직후 `browser_last_seen()`이 `None`을 돌려주면 호출부(`routes_creation.py`)가
그것을 「방금 봤다」로 취급해야 한다 — 그래야 재시작 직후 멀쩡한 방장이
유휴로 오판돼 승계당하지 않는다(T-12.3-13). 배경에서 혼자 도는 정리
장치는 두지 않는다(D-12 경계) — 이 표는 요청이 올 때만 늘고, 세션이
끝나도 스스로 줄지 않는다(T-12.3-12, DoS 위험 accept — 이 서버가 링크를
아는 소수만 쓰는 단일 프로세스 개발 서버라는 전제 위에서만 유효한
판단이다. 배포를 진지하게 다루는 단계가 오면 상한을 다시 볼 것)."""


def mark_browser_seen(session_id: str, browser_id: str) -> None:
    """브라우저가 지금 살아 있다고 표시한다 — `POST /creation/host` 호출
    자체가 곧 재실 신호다."""
    _browser_last_seen[(session_id, browser_id)] = time.monotonic()


def browser_last_seen(session_id: str, browser_id: str) -> float | None:
    """마지막으로 재실 신호를 받은 시각(`time.monotonic()` 기준) — 이
    프로세스에서 한 번도 못 봤으면(재시작 직후 포함) `None`이다."""
    return _browser_last_seen.get((session_id, browser_id))


_character_last_seen: dict[tuple[str, str], float] = {}
"""(session_id, character_id) -> 마지막으로 재실 신호를 받은 시각(Phase
12.3-06, D-06 갈래 ①) — `_browser_last_seen`과 정확히 같은 몸이다. 왜
사건이 아니라 프로세스 메모리인지, 재시작하면 왜 비는지는 위
`_browser_last_seen`의 docstring이 이미 말한 이유와 같다(되풀이하지
않는다). 이 표가 닫는 gap: 지목 후보 목록의 유일한 출처가 이제까지
「이미 항목을 낸 사람」(`unfinished_candidates`)뿐이었는데, 완전히 새
세션에는 그런 사람이 있을 수 없어 첫 지목이 구조적으로 절대 못 일어났다
(12.3-VERIFICATION.md 2차). 이 표는 그 반대 재료 — 「지금 이 방에 와
있는 사람」 — 를 더한다."""


def mark_character_present(session_id: str, character_id: str) -> None:
    """캐릭터가 지금 살아 있다고 표시한다 — `POST /creation/host` 호출에
    `character_id`가 함께 실리면 이 함수가 불린다. `mark_browser_seen`과
    정확히 같은 몸이다."""
    _character_last_seen[(session_id, character_id)] = time.monotonic()


_nomination_watermark: dict[tuple[str, str], tuple[int, float]] = {}
"""(session_id, character_id) -> (지금까지 관측한 가장 앞선 순번, 그
순번을 **처음 본** 시각(`time.monotonic()` 기준)) — Phase 12.3-08.
왜 사건이 아니라 프로세스 메모리인지는 `_browser_last_seen`의
docstring이 이미 말한 이유와 같다(되풀이하지 않는다)."""

_forfeited_at: dict[tuple[str, str], float] = {}
"""(session_id, character_id) -> 차례를 흘려보낸 것으로 판정된 시각
(`time.monotonic()` 기준) — Phase 12.3-08. 한 번 들어가면 세션 동안
안 지운다(재시작하면 프로세스 메모리라 자연히 빈다, T-12.3-26이 그
한계를 받아들인 이유)."""


def latest_nomination(state: GameState) -> tuple[str, int] | None:
    """가장 최근 `nominate` 지목의 대상과 순번 — 대상이 없거나 이미
    `state.created_characters`에 있으면(차례가 끝났으면) `None`이다.

    **이 본문은 `routes_events._creation_current_speaker_id`에서 그대로
    옮겨온 것이다** — 새로 쓴 계산이 아니다(D-04, 판단은 한 자리)."""
    latest_seq = -1
    latest_target: str | None = None
    for fold in state.creation_gm_said.values():
        if fold.kind != "nominate":
            continue
        if fold.seq > latest_seq:
            latest_seq = fold.seq
            latest_target = fold.target_character_id
    if latest_target is None or latest_target in state.created_characters:
        return None
    return (latest_target, latest_seq)


def nomination_progress_seq(state: GameState, character_id: str) -> int:
    """`character_id`가 만들기 항목에 낸 값 중 가장 앞선 순번
    (`CreationStepFold.seq`) — 하나도 없으면 `0`."""
    max_seq = 0
    for (fold_character_id, _step_id), fold in state.creation_step_values.items():
        if fold_character_id == character_id and fold.seq > max_seq:
            max_seq = fold.seq
    return max_seq


def forfeited_nominee(state: GameState, session_id: str) -> str | None:
    """지금 지목된 사람이 자기 차례를 흘려보냈으면 그 `character_id`를,
    아니면 `None`을 돌려준다(Phase 12.3-08, T-12.3-22).

    **부수효과가 있다 — 순수 함수가 아니다.** 호출할 때마다
    `_nomination_watermark`의 관측 시계를 다시 맞추고, 판정되면
    `_forfeited_at`에 그 사실을 찍는다. `present_candidates`가 폴링마다
    이 함수를 불러 관측을 최신으로 유지하는 것이 그래서다.

    **이 구간에는 신원을 증명시킬 수단이 구조적으로 없다**(서명 쿠키는
    캐릭터가 완성돼야 구워진다) — 그래서 신원을 검증하는 대신 자격을
    회수 가능하게 만든다: 차례를 받고 아무 값도 안 낸 식별자는 그
    차례를 잃는다.
    """
    nomination = latest_nomination(state)
    if nomination is None:
        return None
    nominee, nominated_seq = nomination
    key = (session_id, nominee)
    if key in _forfeited_at:
        # 같은 판정을 되풀이 계산하지 않는다 — 이미 흘려보낸 것으로
        # 판정된 지목은 그 사람이 완성되거나 새 지목이 나기 전까지
        # 계속 흘려보낸 상태다.
        return nominee

    # 지목 자체와 그 사람이 낸 마지막 값 중 더 앞선 순번 — 앞으로
    # 나아간 것이 있으면 이 값이 커진다.
    mark = max(nominated_seq, nomination_progress_seq(state, nominee))
    watermark = _nomination_watermark.get(key)
    if watermark is None or watermark[0] != mark:
        # 재시작 직후와 「방금 값을 냈다」가 같은 갈래로 처리된다 —
        # 처음 본 순간부터 다시 잰다(T-12.3-13이 방장에게 세운 것과
        # 같은 규율).
        _nomination_watermark[key] = (mark, time.monotonic())
        return None

    _, started_at = watermark
    now = time.monotonic()
    last_seen = _character_last_seen.get((session_id, nominee))

    # 빠른 갈래 — 재실 신호가 `HOST_IDLE_S`를 넘겨 끊겼다(탭을 닫고
    # 떠났다). 진짜 참가자는 글을 쓰는 동안에도 재실 신호를 계속
    # 보내므로 이 갈래에 안 걸린다.
    quick_branch = now - started_at > HOST_IDLE_S and (
        last_seen is None or now - last_seen > HOST_IDLE_S
    )
    # 느린 갈래 — 재실 신호는 살아 있는데 아무것도 안 낸다(탭을 열어
    # 둔 채 방치했다).
    slow_branch = now - started_at > NOMINATION_IDLE_S

    if quick_branch or slow_branch:
        _forfeited_at[key] = time.monotonic()
        return nominee
    return None


def present_candidates(state: GameState, session_id: str) -> tuple[str, ...]:
    """지목 후보 목록 — `unfinished_candidates`(사건에서 나온, 절대
    안 잘림)를 앞에 놓고, 재실 신호만 있고 아직 항목을 안 낸 사람을
    처음 본 순서대로 뒤에 붙인다(Phase 12.3-06, D-06 갈래 ①).

    **`unfinished_candidates`는 이 함수가 바꾸지 않는다** — 정리
    (`wrap_up`)와 폴링의 `creation_unfinished_character_ids`, 화면의
    동의 관문은 여전히 사건 기반 목록만 본다(add-alongside, 12.3-06
    계획의 `<assumption_delta_decision>`). 재실 표는 서버 재시작에
    취약하므로 그 값이 명단 잠금 판단에 흘러들면 재시작 직후 「아무도
    안 남았다」로 오판할 수 있다 — 그래서 지목 후보 계산 하나에만
    쓴다.

    **상한(T-12.3-17, 위조 방지):** `state.party_size_fixed`가 정해져
    있으면 남은 자리(`party_size_fixed - len(created_characters)`)를
    넘는 **뒤쪽(재실에서 나온) 항목만** 버린다 — 앞쪽(사건에서 나온
    항목)은 상한을 넘더라도 절대 안 버린다. 실제로 값을 낸 사람을
    후보에서 빼면 그 사람이 영영 못 끝낸다.
    """
    # 폴링이 먼저 돌았는지에 기대지 않고 이 함수를 부르는 것만으로
    # 관측이 최신이 된다 — 돌려받은 값 자체는 아래 목록 분류에 안
    # 쓴다, `_forfeited_at`이 최신이 되게 하는 것이 목적이다.
    forfeited_nominee(state, session_id)

    front = list(unfinished_candidates(state))
    seen = set(front)
    now = time.monotonic()
    tail: list[str] = []
    demoted: list[tuple[str, float]] = []
    for (sid, character_id), seen_at in _character_last_seen.items():
        if sid != session_id or now - seen_at > HOST_IDLE_S:
            continue
        if character_id in state.created_characters or character_id in seen:
            continue
        seen.add(character_id)
        forfeited_at = _forfeited_at.get((session_id, character_id))
        if forfeited_at is not None:
            demoted.append((character_id, forfeited_at))
        else:
            tail.append(character_id)
    # 흘려보낸 식별자는 뒤로 밀린다 — 먼저 흘려보낸 쪽이 먼저 온다
    # (결정론적 순서, 탐침 `ordering` 유지).
    demoted.sort(key=lambda item: item[1])
    tail = tail + [character_id for character_id, _forfeited_at in demoted]
    if state.party_size_fixed is not None:
        tail_budget = max(0, state.party_size_fixed - len(state.created_characters) - len(front))
        tail = tail[:tail_budget]
    return tuple(front + tail)


def alive_browsers(session_id: str) -> tuple[str, ...]:
    """이 세션에서 `HOST_IDLE_S` 안에 재실 신호를 보낸 브라우저들 —
    처음 본 순서를 보존한다(딕셔너리 삽입 순서)."""
    now = time.monotonic()
    return tuple(
        browser_id
        for (sid, browser_id), seen_at in _browser_last_seen.items()
        if sid == session_id and now - seen_at <= HOST_IDLE_S
    )


def unfinished_candidates(state: GameState) -> tuple[str, ...]:
    """진행 중인데 아직 완성되지 않은 사람의 닫힌 목록.

    **대화의 상태 기계는 코드가 돌린다**(12.1-03-PLAN.md § 결정한 열린
    지점 ①) — 에이전트에게 묻지 않는다. `state.creation_step_values`의
    키에서 `character_id`를 뽑고 `state.created_characters`에 아직 없는
    사람만 남긴다. 순서는 그 사람이 만들기 항목을 처음 제출한 순서를
    보존한다(딕셔너리 삽입 순서 = 사건 순번 오름차순).

    아직 항목을 하나도 제출하지 않은 사람은 이 목록에 못 들어간다 —
    플랫폼이 아는 유일한 참가자 식별 통로가 `CompleteCreationStep`의
    `character_id`이기 때문이다(방을 여는 사람이 정한 인원수와 실제
    참가자 식별자는 다른 정보다).
    """
    seen: list[str] = []
    for character_id, _step_id in state.creation_step_values:
        if character_id not in state.created_characters and character_id not in seen:
            seen.append(character_id)
    return tuple(seen)


def required_steps_filled(state: GameState, rulebook: Rulebook, character_id: str) -> bool:
    """룰북 최소선(`required=True`)이 채워졌는지 코드가 직접 본다(D-05
    아래층) — GM 재량(위층, `judge_hooks`)과는 다른 층의 판단이다."""
    for step in rulebook.creation_steps:
        if step.required and (character_id, step.step_id) not in state.creation_step_values:
            return False
    return True
