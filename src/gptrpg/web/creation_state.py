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

HOST_IDLE_S = 240.0
"""방장이 유휴로 판정되는 문턱(초, D-11). 2026-08-26(verify-13-06 결함3
재현 뒤) 30.0 → 240.0으로 올렸다.

**옛 값(30초)의 전제 — 네트워크 요동만 본다.** 화면이 15초마다 자기를
알리는 재실 신호(`POST /creation/host`)를 보내는 것을 전제로, 두 배를
두어 "한 번의 폴링 지연이나 네트워크 요동만으로 방장을 잃지 않으려면
최소 두 번은 놓쳐야 한다"는 계산이었다. **이 전제가 실측으로 무너졌다.**

**실측(verify-13-06 — 정정된 원인).** 애초에 이 문제를 처음 발견한
`.planning/todos/pending/2026-08-26-creation-host-transfers-on-timeout.md`
는 "모바일이라서" 넘어간 것인지 "마지막 입장이라서" 넘어간 것인지를
갈라야 한다고 남겨 뒀다 — 이번 재현이 그 답을 갈랐다. 첫 번째 캐릭터
(방장, `d6192fc5`)는 **자기 캐릭터를 다 만든 뒤에도 세션을 계속 열어
두고 있었다**(마지막 동의까지 세션 끝까지 참여) — 모바일도 아니고,
탭을 닫고 떠난 것도 아니다. 그런데도 승계(`creation_host_claimed`,
`reason: "succession"`)가 그 방장의 마지막 활동(13:54:11) 뒤 **약
174초**(13:57:05, 다른 캐릭터가 완성된 직후) 만에 났다 — 15초마다
도는 재실 신호가 174초 동안 서버에 안 닿았다는 뜻이다.

**"마지막 입장"도 "모바일"도 아니다 — 배경 탭 스로틀링이다.** 재실
신호는 `useEffect`의 평범한 `setInterval`(`frontend/src/config.ts`의
`HOST_BEACON_MS`)이다 — 브라우저(특히 Chrome)는 **백그라운드로 밀린
탭의 타이머를 강하게 스로틀링한다**(보통 초 단위에서 분 단위로
늘어난다). 자기 캐릭터를 다 만든 참가자가 다른 두 명을 기다리며
탭을 전환하거나(메시지 확인 등) 화면을 끄는 것은 **지극히 정상적인
행동**인데, 옛 30초 문턱은 그 정상적인 대기조차 "탭을 닫고 떠났다"와
구분하지 못했다. 방장이 계속 붙어 있었다는 사실(끝까지 세션에
참여)이 이 가설을 확정한다 — 만약 정말 탭을 닫고 떠났다면 마지막
동의(seq36)조차 못 냈을 것이다.

**240초로 정한 이유.** 실측 간격(174초)에 여유(약 40%)를 더했다 —
여러 명이 순서대로 항목을 채우는 이 화면의 정상적인 "남 기다리는
시간"을 배경 탭 스로틀링까지 포함해 통째로 흡수하기 위해서다.
`NOMINATION_IDLE_S`(300초, "타이핑 중이지만 재실 신호는 살아 있다")
보다는 여전히 작게 둔다 — 재실 신호 자체가 완전히 끊긴 경우(진짜
탭을 닫고 떠남)를 그보다는 빠르게 잡아내는 것이 `quick_branch`의
존재 이유이기 때문이다(아래 `forfeited_nominee` 참조)."""

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

_forfeited_at: dict[tuple[str, str], tuple[float, int]] = {}
"""(session_id, character_id) -> (차례를 흘려보낸 것으로 판정된 시각
(`time.monotonic()` 기준), 그 판정이 적용되는 `nominated_seq`) —
Phase 12.3-08, 값 모양은 12.3-09(4차 검증 CR-01, `missing` ①)가
고쳤다. 한 번 들어가면 세션 동안 안 지운다(재시작하면 프로세스
메모리라 자연히 빈다, T-12.3-26이 그 한계를 받아들인 이유) — 그러나
**지우지 않는 것이 그 사람이 영원히 지목을 못 받는다는 뜻은 아니다.**
기록은 남되, 저장된 지목 순번과 **같은** 지목에만 적용된다. 새 지목
(다른 순번)이 오면 이 옛 기록은 조회되지 않고 회복 판정이 처음부터
다시 돈다(`forfeited_nominee`의 순번 비교 참조)."""


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


UNNAMED_SUBJECT = "아직 이름을 안 정한 분"
"""이름을 아직 안 정한 사람을 GM이 부르는 말(G-12.3-10).

화면의 `labels.ts::creationUnknownNameSubject`와 같은 문구다 — 같은 사람을
두 자리에서 다르게 부르면 안 된다."""


def display_label(state: GameState, rulebook: Rulebook, character_id: str) -> str:
    """GM이 이 사람을 부를 때 쓸 **사람이 읽는 이름**(G-12.3-10).

    출처는 둘이고 순서가 있다:
    ① 이미 완성된 캐릭터의 `display_name`
    ② 아직 완성 전이라면 `provides_display_name` 항목에 넣어 둔 값
    둘 다 없으면 `UNNAMED_SUBJECT` — **내부 식별자를 절대 안 쓴다.**

    12.3-14가 화면의 차례 표시에 넣은 규율(`creationView.ts::creationTurn`)을
    서버 쪽에도 둔 것이다. 그때는 화면 절반만 덮여서, GM이 하는 말에는
    `pc-ca9b917c` 같은 값이 그대로 실려 나갔다 — 2026-08-23 시험 기록에서
    지목 문장 52개 중 47개가 그랬다.
    """
    entity = state.created_characters.get(character_id)
    if entity is not None and entity.display_name:
        return entity.display_name
    for step in rulebook.creation_steps:
        if not step.provides_display_name:
            continue
        fold = state.creation_step_values.get((character_id, step.step_id))
        if fold is None:
            continue
        if fold.text_value:
            return fold.text_value
        if fold.picked:
            return ", ".join(fold.picked)
    return UNNAMED_SUBJECT


def nomination_progress_seq(state: GameState, character_id: str) -> int:
    """`character_id`가 자기 차례에 **무언가 한** 가장 앞선 순번 — 하나도
    없으면 `0`. 회복 시간(D-13)이 「이 사람이 가만히 있나」를 이 값으로 본다.

    항목 값(`CreationStepFold.seq`)과 **그 사람이 한 말**
    (`CreationInterjectionFold.seq`)을 함께 본다.

    **말을 빼면 안 되는 이유(G-12.3-24).** 항목을 다 채운 사람은 GM의
    되물음에 **말로** 답한다(G-12.3-13) — 그동안 항목 값은 하나도 안
    늘어난다. 말을 안 세면 열심히 대화 중인 사람이 「가만히 있다」로
    판정되어 차례를 회수당한다. 2026-08-23 시험에서 실제로 그렇게 됐다:
    되묻기 일곱 번을 주고받는 동안 회복 시간이 돌아, GM이 그 사람을
    흘려보낸 것으로 보고 다른 사람을 새로 지목했다. 지목 문장은 남들
    대화판에만 뜨고 당사자는 자기 되묻기 화면을 보고 있어서, 「나한테
    안 보이는 질문이 남에게 보인다」로 나타났다."""
    max_seq = 0
    for (fold_character_id, _step_id), fold in state.creation_step_values.items():
        if fold_character_id == character_id and fold.seq > max_seq:
            max_seq = fold.seq
    for interjection in state.creation_interjections:
        if interjection.speaker_character_id == character_id and interjection.seq > max_seq:
            max_seq = interjection.seq
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
    forfeited = _forfeited_at.get(key)
    if forfeited is not None and forfeited[1] == nominated_seq:
        # 같은 판정을 되풀이 계산하지 않는다 — **이 지목 순번에 대해서만**
        # 이미 흘려보낸 것으로 판정됐으면 그 사람이 완성되거나 이 순번의
        # 지목이 남아 있는 동안 계속 흘려보낸 상태다. 판정은 사람이 아니라
        # 그 사람의 그 차례에 대한 것이므로, 순번이 다르면(=새 지목이면)
        # 이 조기 반환에 안 걸리고 아래에서 관측 시계를 처음부터 다시
        # 잰다(12.3-09, 4차 검증 CR-01/truth #20).
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
        _forfeited_at[key] = (time.monotonic(), nominated_seq)
        return nominee
    return None


def forfeited_nomination_mark(state: GameState, session_id: str) -> str:
    """이 세션에서 **마지막으로 판정된 흘려보냄**을 나타내는 표시
    (`"#after:{character_id}:{nominated_seq}"`), 한 번도 흘려보낸 적이
    없으면 빈 문자열(Phase 12.3-09가 만들고 Phase 12.3-10이 의미를
    고친 함수 — 4차 검증 `missing` ③ / 5차 검증·`12.3-REVIEW.md`
    CR-01).

    **이 값은 「지금 흘려보낸 상태인가」가 아니다 — 「이 세션에서
    마지막으로 판정된 흘려보냄이 무엇인가」다.** 그래서 회복 지목이
    기록되어 판정이 풀려도 **뒤로 안 돌아간다.** 옛 구현(12.3-09)은
    `latest_nomination`/`forfeited_nominee`가 `None`을 돌려주는
    순간(=회복) 조기 반환으로 빈 문자열을 냈는데, 이미 항목 값을 낸
    사람이 흘려보내진 경우(후보 앞줄, 후보 목록 자체는 안 바뀐다)에는
    그 빈 문자열이 흘려보내지기 **전**의 원래 키와 완전히 같아져, 회복
    뒤 같은 상황에서 지목을 한 번 더 부르면 리듀서가 영구 보관한 옛
    (흘려보내지기 전) 지목 기록이 그대로 되돌아왔다 — `_forfeited_at`
    자체는 안 지워졌는데 그 사실을 표시가 숨겼다(5차 검증 CR-01의
    본체).

    **`_forfeited_at`을 지우거나 조건부로 무시하면 이 함수가 다시 뒤로
    돌아가 이 결함이 그대로 되살아난다** — 안 지우는 것이 이 함수의
    전제다. `present_candidates`가 이미 `_forfeited_at`을 판정이 서
    있든 아니든 그대로 읽어 뒤로 밀기 정렬에 쓰는 것과 같은 관례다.

    **값이 단조(앞으로만 간다)라서 D-12가 안 깨진다.** `forfeited_nominee`
    를 여전히 부르는 것(부수효과로 판정을 최신으로 만들기 위해서다,
    D-04)과 별개로, 표시 자체는 이 세션의 `_forfeited_at` 항목 중
    **적용 대상 지목 순번이 가장 큰 것** 하나로 조립한다 — 그 값은
    새로운 흘려보냄 판정이 나올 때만 바뀌므로, 같은 시대의 재호출(아무
    것도 안 바뀐 이중 클릭·경쟁 폴링)은 여전히 같은 키로 중복 방지에
    잡힌다(D-12, truth #4 유지)."""
    forfeited_nominee(state, session_id)  # 판정을 최신으로 만드는 부수효과 호출(D-04)

    session_entries = (
        (character_id, applied_seq)
        for (sid, character_id), (_ruled_at, applied_seq) in _forfeited_at.items()
        if sid == session_id
    )
    latest = max(session_entries, key=lambda entry: (entry[1], entry[0]), default=None)
    if latest is None:
        return ""
    character_id, applied_seq = latest
    return f"#after:{character_id}:{applied_seq}"


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

    **상한(T-12.3-17)이 막는 범위는 개수뿐이다 — 신원을 검증하지
    않는다.** `state.party_size_fixed`가 정해져 있으면 남은 자리
    (`party_size_fixed - len(created_characters)`)를 넘는 **뒤쪽(재실에서
    나온) 항목만** 버린다 — 앞쪽(사건에서 나온 항목)은 상한을 넘더라도
    절대 안 버린다. 신원 쪽은 `forfeited_nominee`가 맡되(Phase 12.3-08),
    그것도 신원을 증명시키는 것이 아니라 자격을 회수 가능하게 만드는
    것이다 — 이 구간에는 신원을 증명시킬 수단이 구조적으로 없다(서명
    쿠키는 캐릭터 완성 시점에 구워진다).

    **정렬 — 흘려보낸 식별자가 뒤로 밀린다.** 상한이 잘라야 할 때
    가장 먼저 잘리는 것이 「차례를 받고 아무것도 안 한 식별자」가
    되도록, `_forfeited_at`에 있는 항목을 관측한 시각 순으로 목록
    맨 뒤에 둔다. 실제로 값을 낸 사람을 후보에서 빼면 그 사람이 영영
    못 끝난다.
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
        forfeited = _forfeited_at.get((session_id, character_id))
        if forfeited is not None:
            # 정렬에 쓰는 것은 판정 시각(짝의 첫 원소)이다 — 짝의 두
            # 번째 원소(적용 대상 순번)는 여기서 안 쓴다.
            demoted.append((character_id, forfeited[0]))
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
