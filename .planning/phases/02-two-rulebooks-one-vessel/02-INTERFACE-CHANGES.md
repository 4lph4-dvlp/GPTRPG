# Phase 2 인터페이스 변경 기록 (D-22 / 성공조건 5 / HYP-03)

이 문서는 02-01~02-04 네 계획에 걸쳐 실제로 벌어진 일을 사후에 대조해서 쓴 것이다 — 추측이 아니라
`git diff 5e025b4..HEAD -- src/ tests/ .importlinter`로 확인한 실제 변경분과 세 계획의
SUMMARY.md에 남은 "고친 곳/참은 곳" 기록을 그대로 옮긴 것이다. 여섯 가설 중 유일하게 플레이 없이
데이터 작성만으로 답할 수 있는 가설(HYP-03)의 유일한 근거가 이 문서다.

## ① 한 줄 답

**고쳤다.** 두 번째 룰북(OpenQuest d100)을 넣으면서 플랫폼 코드 파일 10개를 실제로 고쳤다 — "코드
수정 없이"라는 요구사항 문구를 문자 그대로 읽으면 이미 거짓이다. 하지만 이 단계가 실제로 답해야 할
질문은 "고쳤는가"가 아니라 **"고친 것이 두 번째 룰북 때문에 한 번만 필요했는가, 아니면 세 번째·네
번째 룰북이 들어올 때마다 또 고쳐야 하는가"**다. 그 기준으로 나누면: 10개 중 8개는 **한 번만
고치면 끝나는 종류**(등급 이름을 문자열로 넓히는 일, 실패 판정 신호를 필드로 만드는 일, 새 판정
방식을 위한 굴림 도구 확장)였고, **`session_actor/actor.py`의 `_RESOLVERS` 분기 하나만** 세 번째
판정 방식이 들어올 때 또 늘어나는 종류다. 나머지(굴림 도구 두 파일)는 조건부 — 완전히 새로운 눈
모양(다이스풀 등)이 오면 또 확장이 필요할 수 있지만 "기존 메서드를 다시 고치는" 일은 없다. 그리고
이 단계가 실제로 표현해야 했던 것(등급 4종, 수정치 4유형, 적 상태값 그릇)은 단 한 곳도 플랫폼
코드를 고치지 않고 전부 룰북 데이터·`Modifier.type` 문자열·`Entity.stats` 튜플만으로 표현됐다 —
아래 ②가 이 단계의 진짜 답이다.

## ② 고치지 않고 데이터로 버틴 곳 (참은 곳) — 이 문서의 본론

D-22가 명시한 우선순위대로, 이 절이 ③보다 더 자세하고 더 무겁다. "고치고 싶었지만 참았다"가
추상화가 옳다는 가장 강력한 증거이기 때문이다.

### 1. `Modifier` 자료구조 (`rules_core/resolution.py`) — 한 글자도 안 고쳤다

- ⓐ 무엇을 고칠 뻔했나: 수정치 네 유형(FLAT/TARGET_SHIFT/BONUS_DICE/PUSH) 중 FLAT 하나만 있던
  `Modifier(type, value, source)`에 새 유형 전용 필드(예: `dice_count`, `target_delta`)를 추가하고
  싶은 유혹이 있었다.
- ⓑ 왜 고치고 싶었나: 유형마다 계산 시점이 다르므로(굴리기 전/굴림 자체/굴린 뒤/판정 후) 각 유형에
  전용 숫자 칸을 두는 것이 언뜻 더 "타입 안전"해 보인다.
- ⓒ 대신 무엇으로 해결했나: `type: str` 한 칸에 새 유형 이름(`"target_shift"`, `"bonus_dice"`,
  `"push"`)만 얹고, `value: int` 한 칸을 유형에 따라 다른 의미로 재해석했다(목표값 변경폭 /
  주사위 개수·부호 / 아무 의미 없음-표식). `resolve_d100`이 수정치 목록을 한 번 훑어 유형별로
  분류하는 것은 **판정 함수 쪽의 일**이지 자료구조를 넓히는 일이 아니다.
- ⓓ 세 번째 룰북에도 통하는가: 그렇다. 새 유형이 필요하면 `type` 문자열 하나와 `resolve_*` 쪽의
  분류 분기 하나만 늘면 된다. `Modifier` dataclass 자체는 다시 고칠 필요가 없다 — 02-02-SUMMARY가
  이것을 "이 단계의 핵심 증거"로 명시했다.

### 2. `CheckOutcome` (`rules_core/resolution.py`) — 자릿수 분해가 필요했지만 칸을 늘리지 않았다

- ⓐ 무엇을 고칠 뻔했나: d100은 십의 자리/일의 자리를 따로 다뤄야 하고(크리티컬/펌블 판정에
  "두 자리 숫자가 같은가"라는 조건이 있다), 그래서 `CheckOutcome`에 `tens`/`units` 전용 필드를
  추가하고 싶은 유혹이 있었다.
- ⓑ 왜 고치고 싶었나: "판정 원본을 그대로 보존해야 한다"는 요구가 있는데, `rolls` 필드가 2d6
  전용(정확히 두 눈)이라는 암묵적 가정이 있었다.
- ⓒ 대신 무엇으로 해결했나: `rolls: tuple[int, ...]`가 이미 가변 길이 튜플이었다 — d100은
  `(십의자리, 일의자리)` 또는 보너스 다이스가 있으면 `(굴린_모든_십의자리..., 일의자리)`를 그
  칸에 그대로 담는다. 등급 계산 함수(`resolve_d100` 내부)가 `chosen_tens == units`인지를 계산
  시점에 판단해서 `grade_for_margin`에 `is_doubles` 불리언 하나만 넘긴다 — `CheckOutcome`
  자체는 "자릿수"라는 개념을 전혀 모른다.
- ⓓ 세 번째 룰북에도 통하는가: 그렇다. `rolls`가 이미 가변 길이라 다이스풀(여러 눈)이 오는
  판정 방식도 같은 칸에 들어간다.

### 3. `_parse_modifier` (CLI) — 이번 계획(02-04)의 실물 증거

- ⓐ 무엇을 고칠 뻔했나: `--modifier target_shift:20:난이도`처럼 새 유형 문자열을 CLI에서 받으려면
  파서가 유형 이름을 알아야 할 것 같은 유혹이 있었다.
- ⓑ 왜 고치고 싶었나: `argparse`에 `choices=[...]`로 유형을 못박아 오타를 조기에 잡고 싶은
  충동이 자연스럽다.
- ⓒ 대신 무엇으로 해결했나: `_parse_modifier`는 처음부터 `"유형:값:출처"` 문자열을 유형 이름을
  전혀 모른 채 세 조각으로 쪼개기만 한다(`raw.split(":", 2)`). 02-04에서 `--rulebook openquest`와
  `--modifier target_shift:20:난이도`를 나란히 넣는 실제 CLI 왕복 테스트
  (`tests/test_cli.py::test_submit_roll_with_new_d100_modifier_type_needs_no_parser_change`)를
  추가해, 이 함수의 `git diff`에 **본문 변경이 0줄**임을 증명했다.
- ⓓ 세 번째 룰북에도 통하는가: 그렇다. 어떤 새 수정치 유형이 와도 `유형:값:출처` 세 조각 규약만
  지키면 이 함수는 다시 볼 필요가 없다.

### 4. `Roller` 프로토콜 (`rules_core/dice.py`) — 나란히 추가, 기존 것은 무손상

- ⓐ 무엇을 고칠 뻔했나: 백분위(십의 자리·일의 자리) 눈이 필요해지자 기존 `Roller` 프로토콜에
  `roll_tens`/`roll_units`를 얹고 싶은 유혹이 있었다.
- ⓑ 왜 고치고 싶었나: "굴림 도구는 하나"라는 단순함을 유지하고 싶었다.
- ⓒ 대신 무엇으로 해결했나: 구조적 타이핑(PEP 544)을 살려 `PercentileRoller`라는 **완전히 별개인
  새 프로토콜**을 나란히 선언했다. 기존 `Roller.roll_d6`은 한 글자도 안 바뀌었다 — 2d6 판정
  경로는 이 신규 프로토콜의 존재 자체를 모른다.
- ⓓ 세 번째 룰북에도 통하는가: **조건부.** 세 번째 판정 방식(예: M1의 d20)이 `Roller`나
  `PercentileRoller` 중 하나로 표현 가능한 눈 모양이면 프로토콜을 다시 안 늘려도 된다. 완전히
  새로운 눈 모양(다이스풀 등)이 오면 세 번째 프로토콜이 또 필요할 수 있다 — 다만 이 경우에도
  "기존 프로토콜을 고치는" 일은 다시 없고 "나란히 하나 더 추가"하는 패턴이 반복될 뿐이다.
  (③의 8번 항목에서 실제 구현체 파일 두 개의 "확장" 여부를 재확인한다.)

### 5. `resolve_2d6` / `grade_for_total` (2d6 경로 본문) — 본문 자체는 손대지 않았다

- ⓐ 무엇을 고칠 뻔했나: 등급 이름을 `Literal`에서 `str`로 넓히는 김에 `grade_for_total`도 룰북
  선언을 받아 계산하도록(예: `grade_for_total(total, target, bands)`) 일반화하고 싶은 유혹이
  있었다.
- ⓑ 왜 고치고 싶었나: 두 판정 방식이 "같은 함수 시그니처"를 쓰면 더 일관돼 보인다.
- ⓒ 대신 무엇으로 해결했나: `grade_for_total`은 여전히 `total`과 `target` 두 스칼라만 받고
  던전월드 세 이름(`strong_hit`/`weak_hit`/`miss`)을 그대로 반환한다 — 함수 **본문**은
  02-01~02-04 어느 계획에서도 한 줄도 안 바뀌었다. 대신 `session_actor`가 그 반환값을
  `dungeonworld_like.py`의 `Rulebook.grade_bands` 선언과 대조해(`require_band`)
  `counts_as_failure`를 읽어오는 식으로, "이름의 권위"만 계산 함수 밖(룰북 선언)으로 옮겼다.
- ⓓ 세 번째 룰북에도 통하는가: **부분적으로.** `grade_for_total` 자체를 다시 고칠 필요는 없지만,
  이 함수 안에 남아 있는 던전월드 세 이름 리터럴은 세 번째 룰북이 2d6과 다른 등급 이름 집합을
  쓰려 할 때 결국 문제가 된다 — 이것은 참은 곳이 아니라 남은 한계다 (⑤에서 다시 다룬다).

### 6. `Entity`/`StatEntry` (`rules_core/entities.py`) — 02-03이 물려준 다섯 가지 유혹을 그대로 참았다

02-03-SUMMARY의 "What the platform code was tempted to add but did not" 절을 그대로 인용한다 —
이 계획(02-04)이 새로 확인한 사실은 없고, 이 문서가 그 기록을 흡수해 한 곳에 모으는 것이 D-22의
요구 그 자체다.

- ⓐ **전용 `hp`/`current_hp`/`max_hp` 필드** — 참음. "체력"은 그냥 `StatEntry.name`의 문자열 값일
  뿐이다. 체력이 없는 룰북(또는 자원이 세 개인 룰북)은 플랫폼에서 아무 특별 취급도 필요 없다.
  이걸 만들었으면 D32가 막으려는 위반 그 자체였을 것.
- ⓑ **`stats` 튜플 길이 상한** — 참음. D-21은 상한 없음을 요구한다. 아무리 넉넉한 상한(예: 50개)을
  둬도 미래의 룰북이 그 상한을 넘길 수 있다는 사실 자체가 상한 도입을 거부하는 근거다.
- ⓒ **`StatEntry.max` 필수화** — 참음. OpenQuest의 능력치(STR/CON 등)와 Armour Point는 SRD에
  천장 개념이 없다 — `max`를 강제하면 SRD에 없는 숫자를 창작해야 했을 것이다.
- ⓓ **`depleted_effect_ref` 필수화 또는 자동 추론** — 참음. 대부분의 상태값(능력치)은 플랫폼
  의미로 "바닥나는" 개념이 아예 없다 — 전부에 참조를 강제하면 룰북이 선언하지 않은 의미를
  플랫폼이 대신 지어내는 꼴이다.
- ⓔ **"능력치" vs "자원" 서브타입/열거형을 `rules_core`에 두기** — 참음. 그 구분은 어떤 상태값에
  `depleted_effect_ref`를 붙이는지로 이미 룰북 쪽에 있다 — 플랫폼 타입으로 만들면 룰북 규칙이
  플랫폼 계층으로 새는 것.
- ⓕ **음수 `current`를 일반 규칙으로 거부** — 참음(D32). "0 아래로 깎인 값의 뜻은 룰북이 정한다" —
  플랫폼은 구조적으로 잘못된 선언(빈 이름, 음수 `max`)만 거부하고 룰북이 의미를 정하는 값은
  건드리지 않는다.

이 여섯 항목이 세 번째 룰북(크게 다른 스탯 체계를 가진 룰북)이 들어와도 그대로 통한다 — D-21의
"제한 없음"과 D-20의 "룰북 고유 개념 배제"가 코드 구조로 이미 증명됐기 때문이다.

### 7. `GradeBand`/`grade_for_margin` (`rules_core/rulebook.py`) — 이름 목록형·수치 구간형 모두 통과

- ⓐ 무엇을 고칠 뻔했나: OpenQuest(이름 목록: critical/success/failure/fumble)와 향후 수치 구간형
  등급(예: "성공 3회")이 서로 다른 자료구조가 필요할 것 같은 유혹이 있었다.
- ⓑ 왜 고치고 싶었나: "이름"과 "숫자"는 타입이 다르니 각각 전용 필드가 안전해 보인다.
- ⓒ 대신 무엇으로 해결했나: `GradeBand(name, counts_as_failure, margin_at_least, margin_at_most,
  requires_doubles)` 하나로 통일했다. 수치 구간형은 `name`에 숫자를 문자열로 넣고
  `requires_doubles`를 안 쓰는 식으로 **같은 구조를 다르게 채워서** 표현한다.
  `tests/test_grading_d100.py`의 `NUMERIC_BAND_RULEBOOK_BANDS`가 이것을 코드 수정 없이
  증명했다(테스트 파일 안에서만 선언 — 세 번째 실제 룰북으로 출하하지는 않음, ⑤에서 재확인).
- ⓓ 세 번째 룰북에도 통하는가: 그렇다. `GradeBand` 자료구조 자체는 다시 고칠 필요가 없다.

## ③ 고친 곳 (파일 · 줄 · 이유 · 재발 여부)

`git diff 5e025b4..HEAD -- src/ tests/ .importlinter`로 확인한 실제 변경 파일 전체는 아래와 같다.
이 중 **기존 플랫폼 코드의 본문을 실제로 고친 것**만 이 절에 담고, 새로 생긴 파일은 절 끝의
"새로 생긴 파일" 소절에 따로 적는다 — 둘을 섞으면 "고쳤다"는 인상이 실제보다 과장된다.

1. **`src/gptrpg/event_log/schema.py`** — `EVENT_SCHEMA_VERSION` 1→2, `Grade`를
   `Literal["strong_hit", "weak_hit", "miss"]`에서 `str`로 넓힘, `CheckResolved`에
   `counts_as_failure: bool` 필수 필드 추가.
   불가피했던 이유: 고정 `Literal`로는 OpenQuest의 등급 이름(critical/success/failure/fumble)을
   전혀 담을 수 없었다 — 이것은 RESEARCH.md가 계획 전에 이미 예견한 유일한 "반드시 고쳐야 하는"
   지점이다.
   재발 여부: **아니오.** `str`로 넓힌 뒤에는 세 번째 룰북도 같은 필드에 자기 등급 이름만 넣으면
   된다 — 다시 넓힐 필요가 없다.

2. **`src/gptrpg/rules_core/reducer.py`** — `GameState.miss_count`를 `failure_count`로 개명하고,
   `check_resolved` 분기가 `grade == "miss"` 문자열 비교 대신 `counts_as_failure` 신호(판 2 사건)
   또는 `_legacy_v1_counts_as_failure`(판 1 사건, `grade == "miss"`를 그대로 격리해 보존)로
   계산하도록 재작성.
   불가피했던 이유: RESEARCH.md Pitfall 1이 지목한 "여섯 번째 지뢰" — OpenQuest 등급 이름이
   "miss"가 아니므로 문자열 비교로는 실패 집계가 조용히 0으로 고정된다.
   재발 여부: **아니오** (계산 로직 자체는). 세 번째 룰북도 `counts_as_failure`만 선언하면 이
   리듀서를 다시 고칠 필요가 없다. 다만 **판 1 해석 분기(`_legacy_v1_counts_as_failure`) 자체는
   영구적으로 리듀서 안에 남는다** — 이것은 "재발"이 아니라 "잔존"이며 ⑤에서 다시 다룬다.

3. **`src/gptrpg/rules_core/grading.py`** — `Grade` 별칭만 `Literal`에서 `str`로 넓힘.
   `grade_for_total` 함수 **본문은 무손상**(경계 규칙·던전월드 세 이름 리터럴 그대로).
   불가피했던 이유: `event_log/schema.py`와 같은 이유 — `rules_core`도 별도로 `Grade`를 선언하고
   있어(계층 경계상 event_log를 import 못 함) 똑같이 넓혀야 두 층의 타입이 계속 맞는다.
   재발 여부: **아니오**(타입 별칭 자체는). 그러나 함수 본문 안의 세 이름 리터럴은 남은 한계다(⑤).

4. **`src/gptrpg/rules_core/resolution.py`** — `UnsupportedModifier.__init__`에 `resolver: str =
   "resolve_2d6"` 키워드 인자 추가(기본값이 있어 기존 호출부 무손상). `CheckOutcome`/`Modifier`/
   `resolve_2d6`/`_flat_total` 본문은 전혀 안 바뀜.
   불가피했던 이유: `resolve_2d6`과 `resolve_d100` 둘 다 이 예외를 던지므로, 오류 메시지가 "어느
   판정 함수에서 났는지" 구분해야 사람이 읽고 디버깅할 수 있다.
   재발 여부: **아니오.** 이미 매개변수화됐으므로 세 번째 판정 함수는 자기 이름만 넘기면 된다.

5. **`src/gptrpg/session_actor/actor.py`** — `ResolveCheck`에 `rulebook_id: str =
   DUNGEONWORLD_LIKE_ID` 필드 추가, `_resolve_two_d6`/`_resolve_d100_roll_under` 래퍼와
   `_RESOLVERS: dict[str, Callable]` 배선 신설, `_prepare_resolve_check`가 `get_rulebook` →
   `_RESOLVERS` 조회 → `require_band`로 `counts_as_failure` 획득 순서로 재작성.
   불가피했던 이유: RESEARCH.md Pitfall 2 — 판정 방식이 하나뿐이던 시절엔 `resolve_2d6`을 무조건
   호출해도 됐지만, 이제 "어떤 순수 함수를 부를지" 배선이 필요하다. `rules_core`는 계층 경계상
   자기 위(session_actor)나 룰북을 몰라야 하므로 이 배선은 `session_actor`의 몫일 수밖에 없다.
   재발 여부: **예.** `_RESOLVERS` 딕셔너리는 세 번째 판정 방식(예: M1의 d20)이 들어올 때마다
   새 키-값 쌍(그리고 대응하는 `_resolve_*` 래퍼 함수)이 하나씩 늘어난다. 이것이 이 단계 전체에서
   "참았다"가 아니라 **"제한적으로, 그러나 반복적으로 고쳤다"**로 정직하게 분류해야 하는 유일한
   지점이다(RESEARCH.md Pitfall 2가 이미 이렇게 기록하라고 지목했다).

   **사후 추가 수정 (02-REVIEW.md CR-01):** 이 문서가 사장님 승인을 받은 뒤 코드 리뷰가
   `_prepare_resolve_check`의 `except` 절이 `UnsupportedModifier`/`AttributeError`만 잡고
   `grade_for_margin`이 던지는 `NoMatchingGradeBand`(등급 밴드가 margin/doubles 조합을 다
   못 덮는 룰북)는 못 잡는다는 것을 발견했다 — 지금 두 룰북은 둘 다 밴드가 빈틈없어서 안
   걸리지만, 세 번째 룰북이 구간을 하나라도 빠뜨리면 CLI가 raw traceback으로 죽는다. `except
   NoMatchingGradeBand` 한 절을 추가해 다른 판정 실패와 똑같이 `CommandRejected`로 바뀌도록
   고쳤다(`tests/test_session_actor.py::test_rulebook_with_incomplete_grade_bands_is_rejected_not_a_raw_traceback`
   가 RED→GREEN으로 증명). 재발 여부: **아니오** — 이 한 줄을 추가한 뒤에는 어떤 룰북이 등록돼도
   같은 예외 처리 경로를 그대로 탄다.

6. **`src/gptrpg/session_actor/live_roller.py`** — `roll_tens`/`roll_units` 메서드 추가.
   `roll_d6` 본문은 무손상.
   불가피했던 이유: d100 판정에 필요한 실제 난수(백분위 눈)를 공급할 구현체가 있어야 한다.
   재발 여부: **조건부.** 세 번째 판정 방식이 `Roller`/`PercentileRoller` 중 하나로 표현되는
   눈 모양이면 이 파일을 다시 안 건드려도 된다. 완전히 새로운 눈 모양(다이스풀 등)이면 새
   메서드 추가가 또 필요하다 — 다만 이번에도 "확장"이지 "기존 메서드 수정"은 아니다.

7. **`src/gptrpg/event_log/replay_roller.py`** — `roll_tens`/`roll_units` 추가, 기존 `roll_d6`
   본문을 공통 헬퍼 `_next_roll`로 리팩터(겉보기 동작·시그니처는 무손상 — 내부 구현만 재사용
   구조로 바뀜).
   불가피했던 이유: 기록된 눈을 재생할 때도 판정 방식과 무관하게 "기록된 순서 그대로" 눈을
   내줘야 한다 — d100이 세 개(보너스 다이스 포함 시) 이상의 눈을 소비할 수 있으므로 별도
   반복자를 두면 기록 순서가 깨진다.
   재발 여부: 6번과 동일 — **조건부.**

8. **`src/gptrpg/rules_core/dice.py`** — 기존 `Roller` 프로토콜 무손상, `PercentileRoller` 프로토콜
   신규 추가(나란히).
   불가피했던 이유: d100에 필요한 새 구조적 타입을 선언할 자리가 필요했다.
   재발 여부: **조건부** — ②의 4번 항목과 같은 이유.

9. **`src/gptrpg/cli/main.py`** — (a) 02-01에서 `state.miss_count`→`state.failure_count` 출력
   자리 갱신(라벨 문구 자체는 무손상), (b) 이번 계획(02-04)에서 `roll` 하위 파서에 `--rulebook`
   인자 추가(기본값을 `gptrpg.rulebooks.dungeonworld_like.DUNGEONWORLD_LIKE_ID`에서 가져와 문자열을
   CLI에 다시 적어 넣지 않음) + `--target` 도움말에 두 판정 방식에서 이 값의 의미가 다르다는 한 줄
   추가. `_parse_modifier` 함수 본문은 **한 글자도 안 바뀜**(②의 3번, 이 계획의 실물 증거).
   불가피했던 이유: (a)는 2번 항목의 필드명 변경을 그대로 반영해야 했고, (b)는 이 단계의 실제
   산출물(명령줄에서 룰북 선택)이다.
   재발 여부: **아니오.** `--rulebook`은 이미 임의 문자열을 받으므로 세 번째 룰북도 같은 플래그에
   다른 이름만 넣으면 된다.

10. **`.importlinter`** — 계약 2번(`cli -> session_actor -> (rules_core | event_log)`)에
    `gptrpg.rulebooks` 계층을 끼워 넣음(`cli -> session_actor -> rulebooks -> (rules_core |
    event_log)`).
    불가피했던 이유: 신규 `gptrpg.rulebooks` 계층이 생겼으므로 경계 자동 검사 대상에 포함시켜야
    `rules_core -> rulebooks` 역방향 import를 기계적으로 계속 막을 수 있다.
    재발 여부: **아니오.** 세 번째 룰북은 이 계층 **안에** 파일만 추가하면 되고, 계약 자체를
    다시 고칠 필요가 없다.

11. **`tests/conftest.py`, `tests/test_event_log.py`, `tests/test_session_actor.py`** — 세
    파일 모두 1번 항목(`EVENT_SCHEMA_VERSION` 1→2, `CheckResolved.counts_as_failure` 필수화)이
    강제한 테스트 픽스처 갱신이다: `conftest.py`의 `CheckResolved` 생성부 세 곳과
    `test_event_log.py`의 원시 dict 픽스처에 `counts_as_failure` 필드를 추가했고,
    `test_session_actor.py`는 2번 항목의 `GameState.miss_count`→`failure_count` 개명을
    반영해 단언문을 갱신했다. 새 로직을 시험하는 파일이 아니라 이름·필드가 바뀐 만큼만
    따라간 것이라 ③ 본문에서는 빠뜨렸으나, `git diff` 범위 안에 실제로 존재하는 변경이므로
    완전성을 위해 여기 기록한다.
    불가피했던 이유: 1·2번 항목의 직접적인 결과 — 스키마·필드명이 바뀌면 그 값을 참조하는
    픽스처도 같이 바뀌어야 컴파일·단언이 깨지지 않는다.
    재발 여부: **아니오.** 세 번째 룰북이 새 스키마 버전을 강제하지 않는 한(1번 항목과 동일
    조건) 이 파일들을 다시 건드릴 필요가 없다.

### 새로 생긴 파일 (기존 코드를 고친 것이 아니라 새 계층·새 순수 함수를 얹은 것)

이 파일들은 위 acceptance 기준이 요구하는 "실제 diff에 등장한 모든 파일이 문서에 이름으로
등장해야 한다"를 만족시키기 위해 이름만 적는다 — "고쳤다"고 셀 대상이 아니라 D32가 요구하는
"새 계층"과 "새 순수 함수"가 정확히 여기에 해당한다.

- `src/gptrpg/rulebooks/__init__.py` — `RULEBOOKS` 등록소, `get_rulebook`, `UnknownRulebook`
- `src/gptrpg/rulebooks/dungeonworld_like.py` — 던전월드 계열 세 등급 이름을 룰북 선언으로 명시,
  `EXAMPLE_SINGLE_STAT_FOE`
- `src/gptrpg/rulebooks/openquest.py` — OpenQuest SRD(CC BY 4.0) 등급 4종·난이도 5단계
- `src/gptrpg/rulebooks/openquest_creatures.py` — OpenQuest 고블린·스켈레톤 SRD 실 수치
- `src/gptrpg/rules_core/entities.py` — `Entity`/`StatEntry` (D-20/D-21)
- `src/gptrpg/rules_core/resolution_d100.py` — `resolve_d100`/`push_d100` (새 순수 함수, 기존
  `resolve_2d6`과 나란히)
- `src/gptrpg/rules_core/rulebook.py` — `GradeBand`/`Rulebook`/`grade_for_margin`/`require_band`
  (새 선언 구조)

## ④ `EVENT_SCHEMA_VERSION` 판단

**올렸다 — 1에서 2로.** 근거: `event_log/schema.py`의 D-12 규약 docstring이 "사건 모양이 실제로
바뀌면 `EVENT_SCHEMA_VERSION`을 올리고, 읽는 쪽에 옛 판을 해석하는 경로를 추가하라"고 명시한다.
`CheckResolved`에 **새 필수 필드(`counts_as_failure: bool`)가 늘었다** — 이것은 RESEARCH.md
Pitfall 4가 경고한 "검증 범위만 넓어진 것"(`Grade`의 `Literal`→`str`)과는 다른 종류의 변화다.
`Grade` 자체의 폭 확장만이었다면 하위 호환이라 버전을 안 올리는 실용적 절충안도 있었겠지만,
새 **필수** 필드가 생긴 이상 옛 기록(판 1)에는 그 필드가 물리적으로 없으므로 버전을 올리지 않으면
"모양이 그대로"라고 거짓말하는 것이 된다.

옛 판 기록을 해석하는 경로: `src/gptrpg/rules_core/reducer.py`의 `_legacy_v1_counts_as_failure`
함수가 그 자리다. `apply_event`가 `check_resolved` 사건을 접을 때 `payload.get("schema_version",
1)`로 판을 확인하고, 2 미만이면(즉 옛 기록) `grade == "miss"`라는 판 1 시절 규칙을 이 함수 하나에
격리해서 쓴다 — **이미 기록된 판 1 데이터는 한 바이트도 고치지 않는다**(D-12의 핵심 요구).
`tests/test_reducer_failure_count.py`의 `test_v1_payload_without_counts_as_failure_field_uses_legacy_grade_name_rule`과
`test_v1_and_v2_events_mixed_in_one_record_each_rule_applies_independently`가 판 1·판 2가 한
기록 안에 섞여도 각자의 규칙으로 올바르게 해석됨을 증명한다.

## ⑤ 남은 한계 (정직하게)

- **`_RESOLVERS` 분기가 판정 방식마다 하나씩 늘어난다** (`session_actor/actor.py`). 세 번째 판정
  방식(예: M1의 d20)이 들어오면 `_resolve_*` 래퍼 함수 하나와 `_RESOLVERS` 딕셔너리 항목 하나가
  또 필요하다. RESEARCH.md Pitfall 2가 이미 이것을 "참았다가 아니라 제한적으로 고쳤다"로 기록하라고
  지목했다 — ③의 5번 항목이 그 기록이다.
- **`rules_core/grading.py`의 `grade_for_total` 함수 본문에 던전월드 세 이름
  (`"strong_hit"`/`"weak_hit"`/`"miss"`)이 문자열 리터럴로 그대로 남아 있다.** 이 함수의 계산
  자체는 2d6 전용이라 다른 룰북이 이 함수를 호출할 일이 없어서 지금 당장은 문제가 안 되지만,
  "룰북 이름이 플랫폼 코드에 문자열로 있으면 안 된다"는 원칙을 엄밀하게 지키면 이 함수도 언젠가
  `dungeonworld_like.py`로 옮겨야 한다. 02-01이 이 결정을 처음 내렸고("세 번째 룰북이 강제할
  때로 미룬다"), 02-02와 02-04 모두 다시 손대지 않았다 — 세 계획에 걸쳐 일관되게 유지된 의도적
  유예다.
- **`reducer.py`의 판 1 해석 분기(`_legacy_v1_counts_as_failure`)는 영구적으로 남는다.** 이것은
  "언젠가 지울 기술 부채"가 아니라 D-12 규약이 요구하는 구조 자체다 — 판 1로 기록된 데이터가
  존재하는 한 이 분기는 계속 있어야 한다. 세 번째 룰북이 들어와도 이 분기의 존재 이유는 그대로다.
- **`GradeBand`의 수치 구간형 선언(`NUMERIC_BAND_RULEBOOK_BANDS`)은 `tests/test_grading_d100.py`
  안에서만 존재하고 `rulebooks/`에 실제 세 번째 룰북으로 출하되지 않았다.** "구조가 코드 수정
  없이 통과한다"는 것은 증명됐지만, 실제 수치 구간형 콘텐츠(예: 다이스풀 성공 개수)를 쓰는 룰북이
  아직 하나도 없다 — 이것은 구조적 검증이지 콘텐츠 검증이 아니다.
- **`MAX_BONUS_DICE_MAGNITUDE=20` 상한(`resolution_d100.py`)은 02-02가 위협 모델(T-02-06) 대응으로
  추가한 방어 코드다.** 이 상한이 실제 OpenQuest나 미래 룰북의 정당한 사용 범위를 침해하지
  않는다는 것은 검증되지 않았다 — 임의로 정한 안전값이다.

## ⑥ 성공조건 다섯 개 자기 채점

| # | 성공조건 | 판정 | 근거 |
|---|---|---|---|
| 1 | 2d6 등급식 룰북과 d100 롤언더 룰북이 같은 판정 요청·판정 결과 형태 위에서 돈다 | **만족** | `resolve_2d6`/`resolve_d100`이 같은 `CheckOutcome` 반환, `ResolveCheck`가 같은 명령 모양(`rulebook_id`만 다름) — `tests/test_tracer_d100.py`, 이 문서 ②의 1·2번 |
| 2 | 결과 등급이 코드에 박혀 있지 않다 — 룰북이 자기 등급 집합을 선언하고, 이름 목록형·수치 구간형을 둘 다 받는다 | **만족** | `Grade: str`, `GradeBand` 구조가 OpenQuest(이름 목록)와 `NUMERIC_BAND_RULEBOOK_BANDS`(수치 구간, 테스트 전용) 둘 다 통과 — `tests/test_grading_d100.py::test_numeric_band_rulebook_passes_through_resolve_d100_without_code_change` |
| 3 | 수정치 네 유형(숫자 가감/주사위 추가·제거/목표값 변경/재굴림)이 모두 표현된다 | **만족** | FLAT/TARGET_SHIFT/BONUS_DICE/PUSH 전부 실제 계산에 반영 — `tests/test_resolution_d100.py` 전체, 특히 `-k modifier` |
| 4 | 두 룰북의 적과 NPC가 같은 그릇에 들어간다 — 플랫폼 코드에 체력·피해·태그 같은 룰북 고유 개념이 없다 | **만족** | `Entity`/`StatEntry` 4칸 고정, `hp` 전용 필드 없음 — `tests/test_entities.py`, 이 문서 ②의 6번 |
| 5 | 두 번째 룰북을 넣으면서 플랫폼 코드를 고쳐야 했는지 아닌지가 명확히 기록된다 | **자동 검증 불가 — Task 3 사람 확인 대기** | 이 문서 자체가 그 기록이다. §①~⑤가 고친 곳(10개 파일, 그중 재발형은 1개)과 참은 곳(7개 항목)을 둘 다 담았고, 참은 곳 절이 고친 곳 절보다 길다. 최종 판정은 사람이 이 문서를 읽고 내린다 |

---
*이 문서는 02-04-PLAN.md Task 2의 산출물이며, Phase 6의 HYP-03 채점 입력이다.*
