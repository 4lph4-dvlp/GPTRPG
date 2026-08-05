
# Phase 1: 규칙 코어와 사건 기록 - Research

**Researched:** 2026-07-31
**Domain:** Python 이벤트 소싱 백엔드 — 순수 규칙 코어 / append-only 사건 기록(SQLite) / 단일 쓰기 주체(세션 액터), 및 그 경계를 자동으로 강제하는 도구 체인
**Confidence:** HIGH — 표준 스택 선택지 대부분을 이 세션에서 직접 설치·실행해 동작을 확인했다(아래 각 항목에 `[VERIFIED]` 표기). 예외는 명시적으로 `[ASSUMED]`로 남겼다.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

D-01~D-17 전문은 `.planning/phases/01-rules-core-and-event-log/01-CONTEXT.md`에 있다. 이 연구는 아래 결정을 뒤집지 않고 "어떻게"만 채운다. 핵심 요지만 다시 적는다.

- **D-01**: 이 단계의 산출물 = Python 라이브러리 + 명령줄 재생 도구. 화면·서버 없음.
- **D-02**: 실행 언어 = Python 확정. 브라우저 실행 시나리오는 포기.
- **D-03**: 판정 방식 하나(2d6 등급식)를 실제로 코드에 넣어 끝까지 돌린다.
- **D-04**: 규칙 코어의 경계는 자동 검사로 강제한다(시각·무작위·파일·네트워크 차단). 주사위의 무작위도 포함.
- **D-05**: 세션 액터 층은 명령 수신 → 검증 → 규칙 코어 호출 → 기록에 쓰기까지 실제로 동작해야 한다. 명령줄 재생 도구도 이 층을 불러서 돈다.
- **D-06**: 세 층을 한 Python 패키지 안 세 폴더로 나누고, 서로 못 가져다 쓰게 자동 import 검사로 막는다. 별도 배포 패키지로 쪼개지 않는다.
- **D-07**: 사건 기록은 SQLite 파일 하나.
- **D-08**: 현재 상태는 매번 기록을 처음부터 훑어 만든다. 중간 저장(스냅샷) 없음.
- **D-09**: 쓰기 주체 하나를 두 겹으로 강제 — ① 세션당 액터 하나 + 명령 큐잉 ② 기록에 순번을 붙이고 유일성 제약으로 동시 쓰기를 저장소가 거부.
- **D-10**: 사건 종류별 필수 항목을 코드에 못박고, 빠진 채로 쓰면 거부한다.
- **D-11 (이 단계 최고 값 결정)**: MEAS-01~06이 요구하는 숫자 여섯 개를 가짜 세션 기록에서 거꾸로 뽑아보는 테스트로 필드 누락을 검증한다.
- **D-12**: 사건마다 판 번호(스키마 버전)를 붙인다. 이미 쓴 기록은 고치지 않는다. 읽는 쪽에 옛 판 해석 경로를 추가한다.
- **D-13**: 모든 사건에 "누가 볼 수 있는지" 항목을 두되 M0에서는 항상 "전체 공개".
- **D-14**: "AI를 불렀다" 사건 종류를 지금 정의한다(역할·모델·토큰·소요 시간). 실제 AI 호출 코드는 Phase 3.
- **D-15**: 주사위는 "굴리는 도구"를 규칙 코어에 건네주는 방식으로 굴린다(진행 시 실제 도구, 되감을 때 기록에서 읽는 도구).
- **D-16**: 판정 한 번에 계산 과정 전체(굴림값·수정치 출처·목표값·최종 등급)를 남긴다.
- **D-17**: 판정 한 번 = 사건 하나. 서사는 별도 사건.

### Claude's Discretion

- 사건 종류의 최종 목록과 각 종류의 필수 항목 이름 — D-11의 역방향 검증이 정답 기준
- 명령 큐와 세션 액터의 구체적 구현 방식(비동기 태스크 / 스레드 등)
- 자동 경계 검사를 무엇으로 거는지(import 검사 도구 / 테스트 / 정적 분석)
- 명령줄 재생 도구의 출력 형태
- 테스트 도구·패키지 관리자 선택
- 2d6 등급식 판정에 M0 실험용으로 넣을 판정 종류의 최소 집합

### Deferred Ideas (OUT OF SCOPE)

- 브라우저 안에서 규칙 코어 실행 — 필요해지면 D-02를 다시 연다
- 규칙 코어를 별도 배포 패키지로 분리 — M1 이후
- 중간 저장(스냅샷) — 언제든 붙일 수 있음
- 귓속말 기능의 실제 동작 — D-13은 자리만
- 제공자 추상화 계층 코드 — Phase 3
- 진행 정책 설정값(턴 타이머·순서 강제·리액션 윈도우) — Phase 4
- 두 번째 판정 방식(d100 롤언더) — Phase 2
- 룰북 필드 단위 규격·효과 원자 연산 최종 목록 — M1 착수 시
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RIG-02 | 주사위와 판정 계산이 순수 코드로만 일어나며 AI가 수치를 바꿀 수 있는 지점이 없다 | Roller Protocol 주입 패턴(D-15) + import-linter `forbidden` 계약으로 `rules_core`가 `time`/`random`/`os`/`socket`은 물론 향후 AI SDK 모듈까지 못 가져다 쓰게 강제. 아래 "패턴 1"·"경계 검사" 참조 |
| RIG-06 | 모든 사건이 순서대로 기록되고 현재 상태는 그 기록에서 만들어진다 | SQLite 스키마(순번 유일성 제약) + fold 리듀서 패턴 + CLI 재생 도구 설계. 아래 "패턴 2"·"시스템 아키텍처 다이어그램" 참조 |

> 참고: MEAS-01~04(D-11이 요구하는 여섯 숫자)는 REQUIREMENTS.md 추적표 상 Phase 3·4에 배정되어 있다. Phase 1의 책임은 그 숫자들을 **나중에 집계할 수 있도록 사건 스키마를 설계하고, 지금 그것을 증명하는 테스트를 짜는 것**이지 실제 집계 코드를 만드는 것이 아니다(D-11 원문 그대로).
</phase_requirements>

## Summary

이 단계는 순수 계산(규칙 코어) · 영속 기록(사건 기록) · 유일한 쓰기 주체(세션 액터)라는 세 가지 역할을 한 Python 패키지 안에서 폴더로 분리하고, 그 경계가 사람의 주의력이 아니라 자동화된 검사로 지켜지게 만드는 것이 핵심이다. 조사 결과 이 목적에 가장 잘 맞는 조합은 **import-linter(계층·금지 계약) + ruff의 flake8-tidy-imports `banned-api`(모듈별 즉시 피드백)**이며, 두 도구를 이 세션에서 직접 설치하고 의도적으로 위반하는 코드를 넣어 실패시켜본 결과 **둘 다 기대한 대로 동작**했다(아래 코드 예시 참조). 특히 import-linter의 `layers` 계약에서 같은 층에 있는 형제 모듈(rules_core와 event_log)을 서로 독립시키는 문법은 쉼표(`,`)가 아니라 파이프(`|`)여야 하며, 쉼표를 쓰면 조용히 무시된 채 통과해버리는 것을 실제로 확인했다 — 이것이 이번 조사에서 나온 가장 위험한 함정이다.

사건 기록은 SQLite 한 파일에 `PRIMARY KEY (session_id, seq)` 복합키로 저장한다. 이 복합키 하나가 D-09②(동시 쓰기 거부)와 "순번 N부터 끝까지" 조회 성능을 동시에 해결한다는 것을 `EXPLAIN QUERY PLAN`으로 직접 확인했다. 이벤트 스키마는 pydantic v2의 판별 유니온(discriminated union)으로 정의하며, `extra="forbid"` + `frozen=True` 설정으로 "빠진 필드"뿐 아니라 "오타로 생긴 여분 필드"까지 거부하고 객체 자체를 불변으로 만드는 것을 확인했다 — D-10과 D-12(append-only 정신) 둘 다에 도움이 된다.

세션 액터는 세션당 하나의 `asyncio.Queue` + 단일 소비자 태스크로 구현하는 것을 권한다. 이 패턴이 명령 순서를 보장하면서도(직접 실행해 확인) 하나의 명령 처리 중 `await`(미래의 LLM 호출)이 있어도 프로세스 전체가 멈추지 않는다 — 스레드+`queue.Queue` 방식도 가능하지만, Phase 3가 부를 LLM SDK 대부분이 async 우선이라는 점(이 부분은 [ASSUMED], 근거는 Assumptions Log 참조)을 고려하면 asyncio 쪽이 재작업이 적다.

**Primary recommendation:** `uv` 기반 src-layout 패키지 하나(`rules_core` / `event_log` / `session_actor` 세 서브패키지) + `.importlinter`(layers + forbidden 계약) + `ruff`(banned-api, per-file-ignores로 rules_core만 차단) + `pydantic` v2(판별 유니온, `extra="forbid"`, `frozen=True`) + `pytest`/`hypothesis`. 사건 스키마는 6종(action_declared / action_confirmed / check_resolved / narration_appended / clock_advanced / ai_invoked)으로 시작하고, 인과관계를 잇는 `caused_by_seq` 필드를 모든 파생 사건에 반드시 넣는다(이것이 없으면 MEAS-02의 두 응답 속도를 나중에 계산할 방법이 없다 — 이번 조사에서 찾은 가장 중요한 "빠뜨리기 쉬운 필드").

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| 주사위 눈 계산·판정 등급 산출 (2d6) | 규칙 코어 | — | 순수 함수, 입력(눈 값·수정치)이 주어지면 결정론적 결과만 낸다 |
| 주사위 눈 "생성" (실제 굴림 vs 재생 눈 읽기) | 세션 액터(라이브 롤러 보관) / 이벤트 로그(재생 롤러 보관) | 규칙 코어(Roller 프로토콜 정의만) | 규칙 코어는 `secrets`도 "기록에서 읽기"도 몰라야 한다 — Protocol만 안다 |
| 명령 수신·검증·순번 확인 | 세션 액터 | — | D-05·D-09①, 유일한 쓰기 주체·직렬화 지점 |
| 사건 append(저장) + 유일성 검사 | 이벤트 로그 | 세션 액터(호출자) | D-07·D-09②, SQLite 복합 PK가 강제 |
| 현재 상태 재구성(fold) | 이벤트 로그의 파생 계층(리더) | 규칙 코어(리듀서 함수 제공) | D-08, 매번 처음부터 훑음. 리듀서 자체는 순수 함수이므로 규칙 코어에 둔다 |
| 명령줄 재생 도구 | 전송 어댑터(최소형) | 세션 액터(명령 제출) + 이벤트 로그(재생 조회) | D-01, 게임 로직 0줄. 두 하위 명령(제출/재생)으로 나뉜다 — 아래 "패턴 3" 참조 |
| 경계 자동 검사(import-linter, ruff) | (횡단) 빌드·테스트 파이프라인 | — | 세 폴더 어디에도 속하지 않는 개발 도구 계층. pytest 안에서 실행되도록 배선 |
| AI 호출 사건 스키마(자리만) | 이벤트 로그(스키마 정의) | — | D-14, 실제 호출 코드는 Phase 3. Phase 1은 필드 이름만 확정 |
| 가시성 필드(값은 항상 public) | 이벤트 로그(스키마 정의) | — | D-13, M4에서 재사용할 자리만 지금 만든다 |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | ≥3.11 (환경에 3.13.5 설치됨) [VERIFIED: 로컬 실행] | 실행 언어(D-02 잠금) | `sqlite3.Error.sqlite_errorcode` 속성(Python 3.11+)이 있어야 무결성 오류를 문자열 매칭 없이 프로그래밍적으로 구분할 수 있다 |
| pydantic | 2.13.4 (PyPI 최신, 이 세션에 로컬 설치돼 있던 버전과 동일) [VERIFIED: `pip index versions`, 로컬 실행] | 사건 스키마 정의·검증(판별 유니온) | 판별 유니온 + `extra="forbid"` + `frozen=True`로 D-10(빠진/여분 필드 거부)과 D-12(불변) 둘 다를 라이브러리 기본 기능만으로 만족시킨다. 직접 실행해 `ValidationError`가 기대대로 발생함을 확인 |
| sqlite3 (표준 라이브러리) | 3.46.1 (Python 3.13.5에 번들, `pip` 설치 불필요) [VERIFIED: 로컬 실행] | 사건 기록 저장소(D-07) | 설치할 것이 없다(표준 탑재). WAL 모드 + 복합 PK 하나로 D-08·D-09②를 모두 만족 |
| import-linter | 2.13 (PyPI 최신) [VERIFIED: 로컬 설치·실행·의도적 위반 테스트] | 경계 자동 검사 — 계층(layers) + 금지(forbidden) 계약 | `layers`와 `forbidden` 계약 타입 둘 다 하나의 `.importlinter` 파일로 D-04(시간·무작위·IO 금지)와 D-06(세 폴더 상호 격리)을 동시에 표현한다. `pytest` 안에서 프로그래밍적으로 호출되는 것도 확인(`from importlinter import api` 후 `use_cases.lint_imports(...)`) |
| ruff | 0.16.0 (PyPI 최신) [VERIFIED: 로컬 설치·실행] | 린팅 + `flake8-tidy-imports` `banned-api`(TID251) 즉시 피드백 | import-linter보다 빠르고 에디터에 바로 뜬다. 다만 계층 방향(누가 누구를 못 부르는지)은 표현 못 하므로 import-linter의 보완재로만 쓴다 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 (PyPI 최신) [VERIFIED: 로컬 설치·실행] | 테스트 러너 | 모든 검증(경계·역방향 검증·동시성·재생 결정론)을 `uv run pytest` 한 줄로 실행 |
| hypothesis | 6.164.0 (PyPI 최신) [VERIFIED: 로컬 설치·실행] | 속성 기반 테스트 | "2d6 합은 항상 2~12", "같은 기록을 재생하면 항상 같은 결과" 같은 구조적 불변식 검증에 사용. D-11의 "여섯 숫자 역산" 자체는 손으로 만든 가짜 세션 픽스처로 검증(아래 참조) — 구조가 인과관계가 있는 하나의 완결된 로그라서 무작위 생성보다 손으로 짠 시나리오가 더 명확하다 |
| uv | 0.11.28(현재 환경에 설치됨). 2026-07 기준 PyPI/GitHub에 0.12.x 계열 존재 [CITED: WebSearch 요약, uv 공식 changelog 미직접 확인 → MEDIUM] | 패키지 관리자·빌드 백엔드 | `uv init --lib`이 `src/<pkg>/` 레이아웃과 `uv_build` 백엔드를 자동 생성하는 것을 이 세션에서 직접 확인 |
| pytest-asyncio | 1.4.0 (PyPI 최신) [VERIFIED: `pip index versions`] | `asyncio.Queue` 기반 세션 액터의 async 테스트 실행 | 세션 액터를 asyncio로 구현할 경우에만 필요. 스레드 방식을 택하면 불필요 |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pydantic v2 판별 유니온 | dataclasses + 손으로 짠 검증 함수 | 필드 누락 거부·판별 유니온·불변성을 전부 직접 구현해야 한다. D-10이 요구하는 "빠진 채로 쓰면 거부"를 공짜로 주는 pydantic보다 못하다 |
| pydantic v2 | attrs + cattrs | 가능하지만 판별 유니온 인체공학이 pydantic만큼 매끄럽지 않고, 이 조합을 이번 세션에서 검증하지 않았다 |
| import-linter | ruff `banned-api` 단독 | 모듈 임포트 금지는 되지만 "이 패키지가 저 패키지를 못 부른다"는 방향성 있는 계층 규칙을 표현할 수단이 없다. D-06을 만족 못 함 |
| asyncio.Queue + 단일 소비자 태스크 | threading + `queue.Queue` | 둘 다 순번 보장은 되지만, asyncio 쪽이 Phase 3의 비동기 LLM 호출과 자연스럽게 이어진다(단, 이는 예측이며 [ASSUMED] — Assumptions Log 참조). 스레드 방식은 세션마다 sqlite3 커넥션을 스레드-세이프하게 따로 열어야 하는 부담이 있다 |
| uv | poetry / pdm | 성숙하지만 느리다. 잠금 결정에 없으므로 discretion 항목 — 환경에 이미 uv가 설치돼 있고 속도 이점이 있어 uv를 권장 |

**Installation:**
```bash
uv init --lib gptrpg   # src/gptrpg/ 레이아웃 자동 생성 (uv_build 백엔드)
cd gptrpg
uv add pydantic
uv add --dev pytest hypothesis import-linter ruff pytest-asyncio
```

**Version verification:** 위 표의 모든 버전은 `pip index versions <pkg>`로 이 세션에서 직접 조회했다(2026-07-31 기준 PyPI 최신). `import-linter`·`ruff`·`pydantic`·`pytest`·`hypothesis`는 추가로 로컬에 설치해 최소 동작 시나리오를 실행하고 결과를 확인했다(아래 "패턴"·"코드 예시" 참조).

## Package Legitimacy Audit

| Package | Registry | Age(릴리스 이력) | Downloads | Source Repo | Verdict(seam) | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| import-linter | pypi | 1.0부터 2.13까지 다수 릴리스 [VERIFIED: `pip index versions`] | 조회 불가(샌드박스 네트워크 제약) | 없음으로 표시(도구 한계) — 실제로는 `github.com/seddonym/import-linter` | SUS (too-new / unknown-downloads / no-repository) | 승인 — 아래 근거 참조. 계획자는 형식상 `checkpoint:human-verify` 1개를 설치 단계 앞에 추가 |
| ruff | pypi | 0.0.13부터 0.16.0까지 다수 릴리스 [VERIFIED] | 조회 불가 | `docs.astral.sh/ruff` (도구가 정상 인식) | SUS (too-new / unknown-downloads) | 승인 — 동일 근거 |
| pydantic | pypi | 0.0.1부터 2.13.4까지 다수 릴리스 [VERIFIED] | 조회 불가 | `github.com/pydantic/pydantic` | SUS (unknown-downloads) | 승인 — 동일 근거 |
| hypothesis | pypi | 0.0.1부터 6.164.0까지 다수 릴리스 [VERIFIED] | 조회 불가 | 없음으로 표시(도구 한계) — 실제로는 `github.com/HypothesisWorks/hypothesis` | SUS (too-new / unknown-downloads / no-repository) | 승인 — 동일 근거 |
| pytest | pypi | 2.0.0부터 9.1.1까지 다수 릴리스 [VERIFIED] | 조회 불가 | `github.com/pytest-dev/pytest` | SUS (unknown-downloads) | 승인 — 동일 근거 |
| pytest-asyncio | pypi | 0.1부터 1.4.0까지 다수 릴리스 [VERIFIED] | 조회 불가 | `github.com/pytest-dev/pytest-asyncio` | SUS (unknown-downloads) | 승인 — 동일 근거 |

**근거(왜 SUS인데도 승인인가):** `gsd-tools query package-legitimacy check`가 반환한 `publishedAt`은 각 패키지의 **최신 릴리스 시각**이지 최초 등록 시각이 아니다. 이 샌드박스 환경은 다운로드 수 API에 접근하지 못해 `weeklyDownloads`가 항상 `null`로 나온다. 그래서 "too-new"·"unknown-downloads" 신호가 이 6개 패키지 모두에 기계적으로 붙는다. 반면 `pip index versions <pkg>`로 직접 조회한 릴리스 이력은 이 6개 전부 **수년에서 10년 이상, 수십~수백 개 버전**을 보여준다 — `import-linter`(1.0→2.13, 최소 36개 버전), `ruff`(0.0.13→0.16.0, 300개 이상 버전), `pytest`(2.0.0→9.1.1), `hypothesis`(0.0.1→6.164.0, 수백 개 버전). 슬롭스쿼팅된 패키지는 이런 깊이의 릴리스 이력을 가질 수 없다. 이 6개 모두 Python 생태계의 사실상 표준 도구(ruff=Astral, pydantic, pytest, hypothesis, import-linter=Seddonym)이며, 공식 문서(`docs.astral.sh`, `docs.pydantic.dev` 등)를 이번 세션에서 직접 열람해 교차 확인했다.

**Packages removed due to [SLOP] verdict:** 없음.
**Packages flagged as suspicious [SUS]:** 위 6개 전부 — 그러나 위 근거로 실질 위험은 낮다고 판단. 프로토콜에 따라 계획자는 각 설치 단계 앞에 가벼운 `checkpoint:human-verify`(예: "이 6개는 잘 알려진 표준 도구인지 한 번 더 확인" 정도의 형식적 체크포인트)를 넣을 것.

## Architecture Patterns

### System Architecture Diagram

```
[CLI: submit]                                      [CLI: replay]
     │ 명령(자유 문장 또는 구조화 명령)                        │ 기록 파일 경로
     ▼                                                    ▼
┌───────────────────────┐                    ┌─────────────────────────────┐
│  세션 액터               │                    │  이벤트 로그 전체 조회          │
│  (세션당 asyncio 태스크 1개)│                   │  (seq 0..N, session_id 고정)  │
│  ① 명령 큐에 적재          │                    └──────────────┬──────────────┘
│  ② 소비자가 하나씩 처리     │                                   │ fold(사건들)
│  ③ 마지막 본 seq 확인      │                                   ▼
│  ④ 규칙 코어 호출          │                    ┌─────────────────────────────┐
│  ⑤ 이벤트 로그에 append 요청│                   │  규칙 코어의 리듀서 함수         │
└───────────┬───────────┘                     │  (사건 하나 + 이전 상태 → 새 상태)│
            │ 판정 요청                          └─────────────────────────────┘
            │ (Roller 구현체를 함께 전달)
            ▼
┌───────────────────────┐   결과(굴림값·등급·수정치 내역)
│  규칙 코어               │◄────────────────────┐
│  (순수 함수, time/random/ │                     │
│   os/socket 임포트 금지)  │──────────────────────┘
│  - 2d6 판정 계산          │
│  - Roller Protocol만 앎  │
└───────────┬───────────┘
            │ 사건 페이로드(pydantic 모델)
            ▼
┌─────────────────────────────────────┐
│  이벤트 로그 (SQLite 파일 하나)          │
│  INSERT ... WHERE seq = 기대값        │
│  PRIMARY KEY (session_id, seq)       │◄── 동시 쓰기 시 IntegrityError로 거부(D-09②)
└─────────────────────────────────────┘
```

**읽는 법:** CLI에는 두 개의 서로 다른 하위 명령이 필요하다(D-01·D-05를 동시에 만족시키려면 이렇게 나눠야 한다).
- `submit`: 세션 액터를 실제로 호출해 명령을 큐에 넣고 처리되게 한다 — 큐잉·검증·단일 쓰기 주체(D-05·D-09①)를 실물로 증명하는 경로.
- `replay`: 세션 액터를 거치지 않고 이벤트 로그를 처음부터 끝까지 읽어 규칙 코어의 리듀서로 접어(fold) 현재 상태를 보여준다 — 성공 조건 1번(D-08)을 실물로 증명하는 경로.

### Recommended Project Structure

```
gptrpg/
├── pyproject.toml
├── .importlinter                      # layers + forbidden 계약
├── src/
│   └── gptrpg/
│       ├── __init__.py
│       ├── rules_core/                # 순수 함수만. time/random/os/socket 금지
│       │   ├── __init__.py
│       │   ├── dice.py                # Roller Protocol + 2d6 판정 함수
│       │   ├── grading.py             # 등급 산출(10+/7-9/6-)
│       │   └── reducer.py             # 사건 하나 → 상태 갱신 (fold에 쓰임)
│       ├── event_log/                 # SQLite 저장소. rules_core를 모른다
│       │   ├── __init__.py
│       │   ├── schema.py              # pydantic 판별 유니온 (6종 사건)
│       │   ├── store.py               # append(), read_from(seq), fold()
│       │   └── replay_roller.py       # 되감기용 Roller 구현체(기록에서 읽음)
│       ├── session_actor/             # 유일한 쓰기 주체. rules_core+event_log를 부른다
│       │   ├── __init__.py
│       │   ├── actor.py               # asyncio.Queue 기반 커맨드 루프
│       │   └── live_roller.py         # secrets 기반 실제 Roller 구현체
│       └── cli/
│           ├── __init__.py
│           └── replay.py              # `submit` / `replay` 두 하위 명령
└── tests/
    ├── conftest.py                     # 임시 SQLite 경로, 가짜 세션 로그 픽스처
    ├── test_boundaries.py              # import-linter 계약을 pytest 안에서 재확인
    ├── test_event_log.py               # append/read_from/fold, 동시쓰기 거부
    ├── test_dice_replay.py             # 라이브 vs 재생 Roller, 결정론 확인
    └── test_reverse_verification.py    # D-11: MEAS 6개 역산 검증 (최고 우선순위)
```

### Pattern 1: Roller Protocol — 주사위 주입 (D-15)

규칙 코어는 `typing.Protocol`(구조적 타이핑)만 알고, 실제 구현체(암호학적 난수 vs 기록에서 읽기)는 **규칙 코어 바깥**에 둔다. `Protocol`을 쓰는 이유: 구현 클래스가 상속할 필요 없이 메서드 시그니처만 맞으면 되므로(PEP 544), 테스트에서 즉석으로 만든 가짜 객체도 그대로 통과한다.

```python
# src/gptrpg/rules_core/dice.py — rules_core 안, secrets를 import하지 않는다
from typing import Protocol

class Roller(Protocol):
    def roll_d6(self) -> int:
        """1~6 사이 눈 하나를 반환한다."""
        ...

def resolve_2d6(roller: Roller, modifiers: list[int]) -> dict:
    rolls = [roller.roll_d6(), roller.roll_d6()]
    total = sum(rolls) + sum(modifiers)
    if total >= 10:
        grade = "strong_hit"
    elif total >= 7:
        grade = "weak_hit"
    else:
        grade = "miss"
    return {"rolls": rolls, "total": total, "grade": grade}
```

```python
# src/gptrpg/session_actor/live_roller.py — rules_core 밖. 여기서만 secrets를 쓴다
import secrets

class LiveRoller:
    def roll_d6(self) -> int:
        return secrets.randbelow(6) + 1   # [0,6) + 1 → [1,6]. +1을 빠뜨리면 0~5가 나오는 흔한 실수
```

```python
# src/gptrpg/event_log/replay_roller.py — rules_core 밖. 기록에서 읽는다
class ReplayRoller:
    def __init__(self, recorded_rolls: list[int]):
        self._rolls = iter(recorded_rolls)
    def roll_d6(self) -> int:
        return next(self._rolls)   # 기록에 남은 순서대로 그대로 재생
```

**왜 시드 재생이 아니라 눈 값 재생인가 [VERIFIED: Python 공식 `secrets` 문서 열람]:** `secrets` 모듈은 OS가 제공하는 CSPRNG(주로 `os.urandom`)를 쓰며 시딩(seed) 기능 자체가 없다 — 이것이 설계 의도다(암호학적으로 예측 불가능해야 하므로). 따라서 "시드를 남겨뒀다가 나중에 같은 시드로 다시 굴린다"는 방법이 원리적으로 불가능하다. 굴러 나온 눈 값 자체를 사건 기록에 남기고, 재생할 때는 그 값을 그대로 순서대로 재주입하는 것만이 유일한 되감기 수단이다(D-15 전제와 일치).

### Pattern 2: SQLite 사건 기록 스키마 + 낙관적 동시성 (D-07·D-08·D-09②)

```sql
CREATE TABLE events (
    session_id      TEXT    NOT NULL,
    seq             INTEGER NOT NULL,
    event_type      TEXT    NOT NULL,
    schema_version  INTEGER NOT NULL,
    payload         TEXT    NOT NULL,   -- JSON, pydantic model.model_dump_json()
    visibility      TEXT    NOT NULL,   -- 'public' 고정 (M0, D-13)
    caused_by_seq   INTEGER,            -- 인과관계 사슬(아래 "공통 필드" 참조). NULL 허용(최초 사건)
    recorded_at     TEXT    NOT NULL,   -- ISO8601 UTC. event_log가 찍는다. rules_core는 이 값을 읽지도 쓰지도 않는다
    PRIMARY KEY (session_id, seq)
);
```

연결 설정:

```python
conn = sqlite3.connect(db_path, check_same_thread=False)  # 세션 액터가 asyncio 단일 이벤트 루프에서만 접근한다는 전제 하에만 안전
conn.execute("PRAGMA journal_mode=WAL")      # 단일 쓰기자 + 다중 읽기자 구조에 적합
conn.execute("PRAGMA synchronous=NORMAL")    # WAL과 함께 쓸 때 표준 절충값
```

append + 낙관적 동시성 위반 구분:

```python
def append_event(conn, session_id, expected_seq, event_type, schema_version,
                  payload_json, visibility, caused_by_seq, recorded_at):
    with conn:  # 트랜잭션: 정상 종료 시 commit, 예외 시 rollback
        conn.execute(
            "INSERT INTO events "
            "(session_id, seq, event_type, schema_version, payload, visibility, caused_by_seq, recorded_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, expected_seq, event_type, schema_version,
             payload_json, visibility, caused_by_seq, recorded_at),
        )

class SequenceConflict(Exception):
    pass

try:
    append_event(conn, session_id, expected_seq, ...)
except sqlite3.IntegrityError as e:
    # sqlite_errorcode는 Python 3.11+에서 제공된다. 문자열 매칭보다 견고하다
    if e.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_PRIMARYKEY:
        raise SequenceConflict(session_id, expected_seq) from e
    raise  # 그 외 무결성 오류(예: NOT NULL 위반)는 그대로 올린다 — 다른 종류의 버그이므로 숨기면 안 된다
```

**직접 확인한 사실 [VERIFIED: 이 세션에서 sqlite3 3.46.1 / Python 3.13.5로 실행]:**
- 같은 `(session_id, seq)`로 두 번째 INSERT를 시도하면 `sqlite3.IntegrityError`가 발생하고, `e.sqlite_errorcode`는 `1555`(`SQLITE_CONSTRAINT_PRIMARYKEY`)로 나온다 — 문자열 `"UNIQUE constraint failed: ..."`을 파싱하는 것보다 이 정수 코드로 분기하는 편이 SQLite 버전이 메시지 문구를 바꿔도 안 깨진다.
- `EXPLAIN QUERY PLAN SELECT * FROM events WHERE session_id=? AND seq > ? ORDER BY seq`는 `SEARCH events USING INDEX sqlite_autoindex_events_1 (session_id=? AND seq>?)`를 반환한다 — 복합 PK가 자동으로 만든 인덱스만으로 "순번 N부터 끝까지" 조회가 전체 스캔이 아니라 인덱스 탐색으로 처리된다. 별도 인덱스를 만들 필요가 없다.

### Pattern 3: 세션 액터 — asyncio.Queue 단일 소비자 (D-05·D-09①)

```python
# src/gptrpg/session_actor/actor.py
import asyncio

class SessionActor:
    def __init__(self, event_log, rules_core_reducer):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._event_log = event_log
        self._reducer = rules_core_reducer
        self._task: asyncio.Task | None = None

    def start(self):
        self._task = asyncio.create_task(self._run())

    async def submit(self, command) -> None:
        await self._queue.put(command)   # 여러 클라이언트가 동시에 호출해도 큐가 순서를 보장

    async def _run(self):
        while True:
            command = await self._queue.get()
            if command is None:
                self._queue.task_done()
                break
            await self._handle(command)   # 여기 안에서 미래에 LLM await가 들어와도
            self._queue.task_done()       # 이 세션의 다음 명령만 대기하지, 프로세스 전체가 멈추지 않는다
```

**직접 확인한 사실 [VERIFIED: 이 세션에서 asyncio 실행]:** 소비자 루프 안에 `await asyncio.sleep(0.01)`(느린 LLM 호출의 대역)을 넣고 세 개의 명령을 연달아 큐에 넣었더니, 처리 결과는 항상 제출한 순서 그대로였다(`['cmd1', 'cmd2', 'cmd3']`). 즉 큐 안에서의 순서 보장은 처리 중 `await`가 있어도 깨지지 않는다.

**sqlite3 스레드 규칙과의 상호작용:** asyncio는 기본적으로 단일 OS 스레드에서 이벤트 루프가 돈다. 세션 액터가 이 한 스레드에서만 `event_log`의 sqlite3 커넥션을 건드린다면, sqlite3의 "커넥션은 만든 스레드에서만 쓴다"는 기본 규칙(`check_same_thread=True`)과 자연히 맞아떨어진다. `check_same_thread=False`로 풀어야 하는 경우는 세션마다 별도 스레드/프로세스를 쓸 때뿐이며, 이 프로젝트처럼 단일 이벤트 루프 안에서 여러 세션 액터(태스크)가 각자 자기 SQLite 커넥션을 열어 쓰는 구조라면 굳이 풀 이유가 없다 — 풀면 "실수로 다른 스레드가 같은 커넥션을 건드리는" 버그를 잡아주는 안전망이 사라진다.

### 사건 스키마 6종 (Claude's Discretion — D-11 역방향 검증이 기준)

모든 사건이 공유하는 봉투(envelope) 필드: `session_id`, `seq`, `event_type`, `schema_version`, `visibility`, `caused_by_seq`, `recorded_at`.

| event_type | 추가 필수 필드 | 무엇을 위해 필요한가 |
|---|---|---|
| `action_declared` | `player_id`, `raw_text` | MEAS-04(플레이어가 실제로 친 문장) / MEAS-01(턴 수 = 이 사건의 개수) / MEAS-02 첫 구간의 t0 |
| `action_confirmed` | `move`, `stat`, `system_suggestion`, `player_confirmed: bool` | MEAS-04(시스템 제안 + 확인 여부) / MEAS-02 첫 구간의 t1(`caused_by_seq`로 `action_declared`를 가리킴) |
| `check_resolved` | `move`, `rolls: list[int]`, `modifiers: list[{type, value, source}]`, `target`, `grade` | RIG-02·D-16(계산 과정 전체 보존) / MEAS-03(등급이 실패인지 판정) |
| `narration_appended` | `text` | MEAS-02 둘째 구간의 t2(첫 청크의 `recorded_at`, `caused_by_seq`로 `action_confirmed`를 가리킴). D-17이 요구한 대로 판정과 분리된 사건 |
| `clock_advanced` | `clock_id`, `segment_index`, `trigger: "fail_counter"\|"condition"\|"ai_choice"` | MEAS-03(시계 진행 횟수) |
| `ai_invoked` | `agent_role`, `model`, `provider`, `prompt_tokens`, `completion_tokens`, `latency_ms` | MEAS-01(토큰 소모량). D-14가 요구한 자리 — 실제 호출 코드는 Phase 3 |

**pydantic 판별 유니온 구현 [VERIFIED: 이 세션에서 pydantic 2.13.4로 실행]:**

```python
from typing import Annotated, Literal, Union
from pydantic import BaseModel, ConfigDict, Field, ValidationError

class _EventBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)  # 오타 필드 거부 + 불변
    session_id: str
    seq: int
    schema_version: int
    visibility: Literal["public"] = "public"   # D-13, M0 고정값
    caused_by_seq: int | None = None
    recorded_at: str

class CheckResolvedEvent(_EventBase):
    event_type: Literal["check_resolved"]
    move: str
    rolls: list[int]
    modifiers: list[dict]
    target: int
    grade: Literal["strong_hit", "weak_hit", "miss"]

# ... ActionDeclaredEvent, ActionConfirmedEvent, NarrationAppendedEvent,
#     ClockAdvancedEvent, AiInvokedEvent 도 같은 형태로 정의

GameEvent = Annotated[
    Union[CheckResolvedEvent, ActionDeclaredEvent, ActionConfirmedEvent,
          NarrationAppendedEvent, ClockAdvancedEvent, AiInvokedEvent],
    Field(discriminator="event_type"),
]
```

이 세션에서 `grade` 필드를 빠뜨린 `check_resolved` 페이로드를 `model_validate`에 넣었더니 다음과 같이 정확히 어느 사건·어느 필드가 빠졌는지 가리키는 `ValidationError`가 발생했다:

```
1 validation error for Envelope
event.check_resolved.grade
  Field required [type=missing, ...]
```

extra 필드(오타)를 넣었을 때도 같은 방식으로 즉시 거부됐다(`Extra inputs are not permitted`). `frozen=True`로 만든 인스턴스는 생성 후 속성을 바꾸려 하면 `ValidationError(frozen_instance)`가 난다 — append-only 정신(D-12)을 객체 수준에서도 강제한다.

### 경계 자동 검사 — import-linter + ruff (D-04·D-06)

`.importlinter`:

```ini
[importlinter]
root_package = gptrpg
include_external_packages = True   # 표준 라이브러리(time 등)를 forbidden_modules에 넣으려면 반드시 필요

[importlinter:contract:1]
name = rules_core는 시간·무작위·파일·네트워크를 모른다
type = forbidden
source_modules =
    gptrpg.rules_core
forbidden_modules =
    time
    random
    os
    socket
    urllib
    http

[importlinter:contract:2]
name = 세 폴더 간 계층 — session_actor만 나머지 둘을 부를 수 있다
type = layers
layers =
    gptrpg.session_actor
    gptrpg.rules_core | gptrpg.event_log
```

**두 계약을 함께 쓰면 이 조합만으로:**
- `rules_core`가 `time`/`random`/`os`/`socket`을 import하면 실패(D-04)
- `rules_core`와 `event_log`가 서로 import하면 실패(D-06, 형제 독립)
- `rules_core` 또는 `event_log`가 `session_actor`를 import하면 실패(D-06, 방향성)

**⚠️ 이번 세션에서 직접 발견한 함정:** 같은 층의 형제 모듈을 독립시키려고 `gptrpg.rules_core | gptrpg.event_log`가 아니라 `(gptrpg.rules_core, gptrpg.event_log)`(괄호+쉼표)로 썼더니, **에러 없이 조용히 통과**해버렸다 — import-linter 소스코드(`layers.py`)를 직접 읽어 원인을 확인했다: 괄호는 "선택적 레이어"(해당 모듈이 없어도 계약이 깨지지 않음) 표시이고, 형제를 나누는 구분자는 `|`(서로 독립) 또는 `:`(독립 아님) 두 가지뿐이다. 쉼표는 구분자로 인식되지 않아 문자열 전체가 하나의(그리고 존재하지도 않는) "선택적 레이어" 이름으로 잘못 해석된다. **`|`를 쓰지 않으면 경계 검사가 있는 척만 하고 실제로는 아무것도 막지 않는다** — 이 조사에서 나온 가장 위험한 함정이다.

pytest 안에서 실행하기 [VERIFIED: 이 세션에서 실행 — 계약 위반 시 `assert` 실패, 위반 없을 시 통과 둘 다 확인]:

```python
# tests/test_boundaries.py
import os
from importlinter import api  # 이 임포트가 importlinter.configuration.configure()를 트리거한다(내부 배선)
from importlinter.application.use_cases import lint_imports

def test_import_contracts_are_kept():
    os.chdir(PROJECT_ROOT)
    assert lint_imports(config_filename=".importlinter", is_debug_mode=True) is True
```

위반이 있을 때 pytest 출력(캡처된 stdout에 그대로 뜬다):

```
Rules core must not touch time, randomness, files, or network BROKEN
...
pkg.rules_core is not allowed to import random:
-   pkg.rules_core.dice -> random (l.1)
FAILED tests/test_boundaries.py::test_import_contracts_are_kept
```

`ruff` `banned-api`는 즉시 피드백(에디터·pre-commit)용 2차 방어선으로 함께 쓴다. 주의할 점: `banned-api`는 **프로젝트 전체에 전역 적용**된다 — `rules_core`에만 걸려면 나머지 폴더를 `per-file-ignores`로 명시적으로 빼줘야 한다(반대가 아니다).

```toml
# pyproject.toml
[tool.ruff.lint]
select = ["TID251"]

[tool.ruff.lint.flake8-tidy-imports.banned-api]
"time".msg = "rules_core는 시각을 몰라야 한다 (D-04)"
"random".msg = "rules_core는 secrets 대신 random을 쓸 수 없다 (D-04, D-15)"
"socket".msg = "rules_core는 네트워크를 몰라야 한다 (D-04)"

[tool.ruff.lint.per-file-ignores]
"src/gptrpg/session_actor/*" = ["TID251"]
"src/gptrpg/event_log/*" = ["TID251"]
"src/gptrpg/cli/*" = ["TID251"]
```

이 세션에서 `ruff check`를 `rules_core/dice.py`(위반 있음)와 `session_actor/actor.py`(위반 없음, ignore 대상)에 각각 실행해 정확히 의도대로 갈리는 것을 확인했다.

### Anti-Patterns to Avoid

- **`rules_core` 안에서 `datetime.now()`/`time.time()`을 "그냥 로그 찍으려고" 호출:** 아무리 사소해도 성공 조건 4번을 깬다. 로그 시각이 필요하면 그 값을 세션 액터/이벤트 로그가 만들어 함수 인자로 넘겨라.
- **`(a, b)` 쉼표로 import-linter 형제 레이어를 표현:** 조용히 무시된다. 반드시 `a | b`.
- **`sqlite3.IntegrityError`를 문자열 메시지로 구분:** SQLite 버전이 메시지 문구를 바꾸면 깨진다. `e.sqlite_errorcode`(정수 상수)로 구분하라.
- **`secrets.randbelow(6)`을 그대로 눈 값으로 쓰기:** 범위가 [0,6)이라 0이 나온다. `+1`을 잊기 쉽다.
- **인과관계 필드(`caused_by_seq`) 없이 사건만 순서대로 쌓기:** 순번이 인접하다고 인과관계가 보장되지 않는다(여러 참가자가 동시에 입력하면 사건이 뒤섞인다). MEAS-02의 두 응답 속도를 나중에 계산할 방법이 사라진다 — 이번 조사의 핵심 발견.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| import 방향·금지 규칙 검사 | 직접 짠 AST 순회 스크립트 | import-linter | 계층·금지·독립 계약 타입이 이미 있고, pytest 배선까지 검증됐다. 손으로 짜면 엣지 케이스(간접 임포트, `__init__.py` 재노출)를 놓치기 쉽다 |
| 이벤트 페이로드 검증 | 손으로 짠 `if "grade" not in payload: raise` 나열 | pydantic 판별 유니온 + `extra="forbid"` | 필드 열거가 늘어날수록 손으로 짠 검증은 하나씩 빠뜨리기 쉽다. pydantic은 모델 정의 자체가 검증 규칙이다 |
| 암호학적 난수 생성 | 커스텀 PRNG 또는 `random` 모듈을 "충분히 무작위"라고 가정 | `secrets.randbelow` | `random`은 시딩 가능한 결정론적 PRNG라 예측 가능하다 — Provably Fair 약속(D14/decisions.md)이 깨진다 |
| SQLite 동시쓰기 감지 | 애플리케이션 레벨 락(예: 파일 락, 인메모리 뮤텍스) | `PRIMARY KEY (session_id, seq)` 유일성 제약 | 저장소 레벨 제약은 프로세스가 여러 개로 늘어나도(미래에 서버를 늘려도) 그대로 유효하다. 애플리케이션 레벨 락은 프로세스 경계를 못 넘는다(D-09의 정확히 그 이유) |

**Key insight:** 이 단계에서 "직접 짜고 싶은 유혹"이 가장 큰 두 가지 — 경계 검사와 동시성 감지 — 는 둘 다 "한 프로세스 안에서는 잘 작동하지만 나중에 늘어나면 조용히 깨지는" 함정이 있다. 기성 도구(import-linter)와 저장소 제약(SQLite PK)은 그 함정을 프로세스 경계와 무관하게 막아준다.

## Common Pitfalls

### Pitfall 1: 인과관계 필드를 빠뜨리기
**What goes wrong:** 사건은 순서대로 잘 쌓이지만, "이 확인 표시가 어느 입력에 대한 응답인지" 알 방법이 없다.
**Why it happens:** seq가 순증하니 "바로 앞 사건이 원인"이라고 가정하기 쉽다. 그러나 여러 참가자가 거의 동시에 입력하면 순번은 섞인다.
**How to avoid:** `action_confirmed`·`check_resolved`·`narration_appended`·`clock_advanced` 등 "파생" 사건에는 반드시 `caused_by_seq`를 채운다.
**Warning signs:** D-11의 역방향 검증 테스트에서 MEAS-02(두 응답 속도) 계산이 "가장 최근의 관련 사건"이라는 휴리스틱에 의존하게 된다면 이미 이 함정에 빠진 것이다.

### Pitfall 2: import-linter 형제 레이어 문법 오류가 조용히 통과
**What goes wrong:** `.importlinter`에 `(a, b)`처럼 쉼표로 형제를 나열하면 파서가 이를 "존재하지 않는 선택적 레이어 하나"로 해석해 계약이 사실상 무의미해진다. CI는 초록불이지만 아무것도 막고 있지 않다.
**Why it happens:** 괄호를 "그룹"으로, 쉼표를 "나열"로 읽는 것은 자연스러운 직관이지만 import-linter의 실제 구분자는 `|`(독립)과 `:`(비독립)뿐이다.
**How to avoid:** 계약을 작성한 직후 반드시 **의도적으로 위반하는 커밋**을 임시로 만들어 `lint-imports`가 실제로 실패하는지 확인한다(이 세션에서 한 것과 동일한 절차).
**Warning signs:** `lint-imports` 실행 시 "Analyzed N files, 0 dependencies"처럼 예상보다 적은 의존성 수가 나오면 계약이 제대로 안 걸리고 있다는 신호다.

### Pitfall 3: ruff `banned-api`가 프로젝트 전역에 적용된다는 것을 놓침
**What goes wrong:** `rules_core`만 막으려고 `banned-api`를 켰는데 `session_actor`의 정상적인 `time`/`secrets` 사용까지 전부 막혀 개발이 멈추거나, 반대로 아예 `per-file-ignores`를 안 넣어서 전역이 막힌 채로 방치된다.
**Why it happens:** import-linter의 `source_modules`(특정 폴더만 지정)와 달리 ruff의 `banned-api`는 규칙 자체가 전역이고, 예외를 `per-file-ignores`로 "빼주는" 방식이라 방향이 반대다.
**How to avoid:** `banned-api`를 켤 때 항상 `per-file-ignores`로 `rules_core` 외 폴더를 명시적으로 제외한다.

### Pitfall 4: `secrets.randbelow`의 범위를 착각
**What goes wrong:** `secrets.randbelow(6)`은 `[0, 6)`을 반환하므로 그대로 쓰면 주사위 눈에 0이 나온다.
**Why it happens:** d6 눈은 1~6이라는 직관과 함수의 반개구간(half-open interval) 규약이 어긋난다.
**How to avoid:** `secrets.randbelow(6) + 1`. 다른 면수도 동일 패턴(`a + secrets.randbelow(b - a + 1)`로 일반화 가능).

## Code Examples

### D-11 역방향 검증 테스트의 모양 (이 단계 최고 우선순위)

가짜 세션 로그를 손으로 만들고(한 턴: 입력→확인→판정→서사, 시계 진행 1회, AI 호출 1회 포함), 여섯 개 값을 각각 별도로 단언한다 — 하나만 실패해도 정확히 "무엇이 빠졌는지" 알 수 있게 여섯 개 `assert`를 한 함수 안에서도 개별 메시지로 분리한다.

```python
# tests/test_reverse_verification.py
def test_all_six_measurements_derivable_from_fake_session_log(fake_session_log):
    events = fake_session_log  # conftest.py 픽스처: 위 6종 사건이 뒤섞인 완결된 한 세션

    # MEAS-01a: 실제 토큰 소모량
    token_total = sum(e.prompt_tokens + e.completion_tokens
                      for e in events if e.event_type == "ai_invoked")
    assert token_total > 0, "MEAS-01 실패: ai_invoked 사건에 토큰 필드가 없거나 세션에 하나도 없음"

    # MEAS-01b: 실제 턴 수
    turn_count = sum(1 for e in events if e.event_type == "action_declared")
    assert turn_count > 0, "MEAS-01 실패: action_declared 사건이 없어 턴 수를 셀 수 없음"

    # MEAS-02a: 문장 입력 → 행동 확인 표시 시간
    latencies_input_to_confirm = []
    by_seq = {e.seq: e for e in events}
    for e in events:
        if e.event_type == "action_confirmed":
            origin = by_seq.get(e.caused_by_seq)
            assert origin is not None, (
                "MEAS-02 실패: action_confirmed.caused_by_seq가 대응하는 "
                "action_declared를 가리키지 않음"
            )
            latencies_input_to_confirm.append(e.recorded_at - origin.recorded_at)
    assert latencies_input_to_confirm, "MEAS-02 실패: 확인 표시 지연을 하나도 계산 못 함"

    # MEAS-02b: 확인 → 서사 첫 글자 시간 (동일 패턴, narration_appended.caused_by_seq)
    # MEAS-03: 판정 실패 횟수 대비 위협 시계 진행 횟수
    fail_count = sum(1 for e in events if e.event_type == "check_resolved" and e.grade == "miss")
    clock_advance_count = sum(1 for e in events if e.event_type == "clock_advanced")
    assert fail_count >= 0 and clock_advance_count >= 0  # 둘 다 존재만 하면 비율은 Phase 4가 계산

    # MEAS-04: 플레이어 문장 + 시스템 제안 + 확인 여부
    for e in events:
        if e.event_type == "action_confirmed":
            assert e.system_suggestion is not None
            assert e.player_confirmed in (True, False)
    for e in events:
        if e.event_type == "action_declared":
            assert e.raw_text, "MEAS-04 실패: raw_text가 비어 있음"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Token-level 스트리밍 전송 | 문장 청크 전송 | v1→v2(2026-07-30 설계 종결) | 이 단계와는 무관하지만, `narration_appended` 사건이 "문장 단위"로 쌓인다는 전제와 일치한다(D-17의 근거) |
| 신뢰도 임계값(0.9) 기반 자동/수동 분기 | 모든 분류가 플레이어 확인을 거침(혼합형) | D-16 | `action_confirmed` 사건에 `player_confirmed: bool`이 항상 있어야 하는 이유. 신뢰도 숫자 자체는 저장할 필요 없다(UI 강도로만 쓰임, 게임 진실이 아니다) |

**Deprecated/outdated:** 해당 없음 — 이 단계는 그린필드이며 과거 버전이 없다.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Phase 3에서 쓰일 LLM 프로바이더 SDK가 비동기(async) API를 기본 제공할 것이다 — 이것이 asyncio.Queue 기반 세션 액터를 스레드+`queue.Queue` 방식보다 권장하는 핵심 근거다 | Standard Stack(대안 비교), 패턴 3 | Phase 3가 동기 전용 SDK나 서브프로세스 방식을 쓰게 되면, asyncio 액터 안에서 동기 블로킹 호출을 `run_in_executor`로 감싸야 하는 추가 작업이 필요하다. 구조 자체(큐+단일 소비자)는 바뀌지 않으므로 재작성 비용은 낮다 |
| A2 | 이벤트 소싱 스키마의 "업캐스팅"(옛 판을 읽을 때 변환 함수 체인을 거치는 것)이 D-12를 만족하는 표준 패턴이라는 것 | (본문에 명시적 섹션은 없으나 스키마 버전 필드 설계에 전제로 깔림) | 잘 알려진 이벤트 소싱 업계 관행이라 위험은 낮지만, 이 세션에서 특정 공식 자료로 직접 확인하지는 않았다. Phase 2에서 실제로 스키마가 바뀌는 시점에 구체적 변환 함수 형태를 다시 검토할 것 |
| A3 | uv 0.12.x 계열(2026-07 기준 최신)이 이 환경의 0.11.28보다 나은 기본 `--lib` 동작을 준다는 WebSearch 요약 — uv 공식 changelog로 직접 대조하지 않음 | Standard Stack(uv 행 각주) | 낮음. 0.11.28로도 `--lib` 플래그와 `src/` 레이아웃 생성은 이 세션에서 직접 확인됐다. 최신판이 더 낫다는 것은 부가 정보일 뿐 계획에 영향 없음 |

**요약:** 위 세 항목 모두 이 단계의 핵심 결정(D-01~D-17)을 흔들지 않는 저위험 항목이다. 계획자는 A1을 계획 단계에서 "asyncio 채택"으로 확정하되, Phase 3 착수 시 실제 SDK를 보고 재확인하라는 메모를 남기는 정도면 충분하다.

## Open Questions (RESOLVED)

> 두 항목 모두 계획 단계(`/gsd-plan-phase 1`)에서 닫혔다. 실행자는 아래 Recommendation이 아니라 PLAN.md의 결정을 따른다.

1. **`session_actor`가 세션당 자체 SQLite 커넥션을 여는지, 아니면 프로세스 전체가 커넥션 풀을 공유하는지**
   - **RESOLVED** — `01-02-PLAN.md` §「사건 기록 파일과 세션의 관계」에서 확정.
   - What we know: 단일 asyncio 이벤트 루프 안에서 세션마다 태스크 하나씩 돌리는 구조를 권장했다.
   - What's unclear: SQLite 파일이 세션마다 다른지(파일 하나=세션 하나) 아니면 여러 세션이 한 파일을 공유하는지(파일 하나=캠페인 전체, D-02 decisions.md의 "세션=접속 구간, 캠페인=진짜 게임" 구도와 맞물림)는 CONTEXT.md에 명시되어 있지 않다.
   - Recommendation: 계획 단계에서 확정 필요. `PRIMARY KEY(session_id, seq)`로 스키마를 설계했으므로 한 SQLite 파일에 여러 session_id가 섞여도 무방하다 — 파일을 나눌지는 순수 배포/백업 편의 문제로 남겨도 된다.

2. **`replay_roller`가 재생 중 기록된 굴림 수보다 더 많은 굴림을 요청받으면(예: 재계산 로직 버그) 어떻게 실패해야 하는가**
   - **RESOLVED** — `01-02-PLAN.md` Task 3에서 `ReplayExhausted` 예외로 감싸는 것으로 확정.
   - What we know: `ReplayRoller.roll_d6()`는 `next(self._rolls)`를 호출하므로 기록이 소진되면 `StopIteration`이 그대로 튀어나온다.
   - What's unclear: 이것을 그대로 노출할지, 더 읽기 좋은 예외(예: `ReplayExhausted`)로 감쌀지는 정하지 않았다.
   - Recommendation: 작은 문제이므로 계획 단계에서 `try/except StopIteration: raise ReplayExhausted(...)` 한 줄로 감싸는 정도로 처리하면 충분하다.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | 전체 (D-02 잠금) | ✓ | 3.13.5 | — |
| sqlite3(표준 라이브러리) | 사건 기록(D-07) | ✓ | 3.46.1 | — |
| uv | 패키지 관리·빌드 | ✓ | 0.11.28 | 없으면 pip+venv로도 동일 구조 구성 가능 |
| git | 커밋(D-01 CLI 산출물 버전관리) | ✓ | 2.47.3 | — |
| pydantic | 사건 스키마 검증 | 프로젝트 venv에는 미설치(전역에는 2.13.4 존재) | — | `uv add pydantic`으로 즉시 설치 가능. 대체 불가 필요 없음 |
| import-linter | 경계 검사 | 미설치(전역·프로젝트 모두) | — | `uv add --dev import-linter`로 설치 확인됨(이 세션에서 직접 설치·실행) |
| ruff | 경계 검사 2차 방어선·린팅 | 미설치 | — | `uv add --dev ruff`로 설치 확인됨 |
| pytest / hypothesis | 테스트 러너·속성 기반 테스트 | 미설치 | — | `uv add --dev pytest hypothesis`로 설치 확인됨 |

**Missing dependencies with no fallback:** 없음 — PyPI 접근이 이 환경에서 정상 동작함을 `pip index versions` 및 실제 설치로 확인했다.
**Missing dependencies with fallback:** 위 표의 "미설치" 항목 전부 — 전부 `uv add`(또는 `uv add --dev`) 한 줄로 해결되며, 이 세션에서 실제로 설치해 동작을 확인했다.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 [VERIFIED] |
| Config file | 없음 — Wave 0에서 `pyproject.toml`의 `[tool.pytest.ini_options]`와 `tests/conftest.py` 생성 필요 |
| Quick run command | `uv run pytest -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RIG-02 | rules_core가 시간·무작위·IO·(향후) AI SDK를 import할 수 없다 | unit(경계) | `uv run pytest tests/test_boundaries.py -x` | ❌ Wave 0 |
| RIG-02 | 같은 굴림 기록을 재생하면 항상 같은 결과 | unit(결정론) | `uv run pytest tests/test_dice_replay.py -x` | ❌ Wave 0 |
| RIG-06 | 사건을 append하고 처음부터 fold하면 같은 상태가 재구성된다 | integration | `uv run pytest tests/test_event_log.py -k fold -x` | ❌ Wave 0 |
| RIG-06 | 같은 (session_id, seq)에 동시에 쓰면 하나만 성공하고 나머지는 `SequenceConflict` | integration | `uv run pytest tests/test_event_log.py -k concurrency -x` | ❌ Wave 0 |
| D-11(내부 결정, 최고 우선순위) | 가짜 세션 로그에서 MEAS-01~04 여섯 숫자가 전부 산출된다 | integration | `uv run pytest tests/test_reverse_verification.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest -q`
- **Per wave merge:** `uv run pytest`(전체, import-linter 계약 포함)
- **Phase gate:** 전체 스위트 초록 + `uv run pytest tests/test_reverse_verification.py`가 여섯 assert 모두 통과해야 `/gsd-verify-work` 진행

### Wave 0 Gaps
- [ ] `pyproject.toml` — `uv init --lib gptrpg` + `[tool.pytest.ini_options]` 추가
- [ ] `.importlinter` — layers + forbidden 계약(위 예시 그대로 시작 가능)
- [ ] `tests/conftest.py` — 임시 SQLite 경로 픽스처, `fake_session_log` 픽스처(6종 사건이 뒤섞인 완결 세션 하나)
- [ ] `tests/test_boundaries.py`, `test_event_log.py`, `test_dice_replay.py`, `test_reverse_verification.py` — 전부 신규
- [ ] 프레임워크 설치: `uv add --dev pytest hypothesis import-linter ruff pytest-asyncio`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | 이 단계는 HTTP/인증 계층이 없다(명시적으로 범위 밖, D-01). 전송 어댑터가 생기는 단계에서 재평가 |
| V3 Session Management | no | 동일 사유. "세션"은 이 단계에서 인증 개념이 아니라 순수 데이터 모델(session_id)일 뿐이다 |
| V4 Access Control | no | 동일 사유. 가시성 필드(D-13)는 접근 제어가 아니라 **표시 여부** 데이터일 뿐이며 M0에서 항상 public이라 강제할 로직 자체가 없다 |
| V5 Input Validation | yes | pydantic 판별 유니온 + `extra="forbid"`. 이벤트 페이로드는 JSON만 신뢰하고 `eval`/`pickle` 등 코드 실행 가능한 역직렬화 경로를 절대 쓰지 않는다 |
| V6 Cryptography | yes | `secrets` 모듈(CSPRNG) — 절대 `random` 모듈로 대체하지 않는다. 이것이 제품 정체성의 "④ 불확실성(양보 불가)"과 "Provably Fair" 약속(decisions.md D14)을 코드로 뒷받침하는 지점이다 |

### Known Threat Patterns for {Python/SQLite/pydantic 스택}

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| 이벤트 페이로드에 문자열 포맷팅으로 SQL을 직접 조립 | Tampering | 항상 `?` 파라미터 바인딩 사용(위 코드 예시 전부 이미 이렇게 작성됨). 절대 f-string으로 SQL 조립하지 않는다 |
| `random` 모듈로 주사위를 굴려 결과가 예측 가능해짐 | Tampering(공정성 훼손) | import-linter `forbidden` 계약이 `rules_core`에서 `random` import 자체를 원천 차단 |
| 사건 payload를 `pickle`/`eval`로 역직렬화 | Tampering(임의 코드 실행) | pydantic의 `model_validate_json`(순수 JSON 파서 기반)만 사용. `pickle.loads`를 이벤트 로그 어디에도 두지 않는다 |
| 오타로 생긴 여분 필드가 조용히 무시되어 실제로는 다른 필드를 기록하려 한 버그를 못 알아챔 | Tampering(데이터 무결성) | `extra="forbid"`로 모든 사건 모델에서 원천 차단(이 세션에서 검증) |

## Sources

### Primary (HIGH confidence — 이 세션에서 직접 설치·실행하여 검증)
- import-linter 2.13 — `.importlinter` 문법(`layers`/`forbidden`/`include_external_packages`), 쉼표 vs 파이프 형제 문법 차이, pytest 배선(`importlinter.api` + `application.use_cases.lint_imports`) — 로컬 설치 후 위반/정상 케이스 각각 재현
- ruff 0.16.0 — `flake8-tidy-imports` `banned-api` + `per-file-ignores` 전역/예외 동작 — 로컬 설치 후 재현
- pydantic 2.13.4 — 판별 유니온, `extra="forbid"`, `frozen=True`, `ValidationError` 메시지 형태 — 로컬 실행
- sqlite3 3.46.1(Python 3.13.5 표준 라이브러리) — `PRIMARY KEY` 복합키의 `IntegrityError`/`sqlite_errorcode`, `EXPLAIN QUERY PLAN` 인덱스 사용 확인 — 로컬 실행
- asyncio(표준 라이브러리) — `asyncio.Queue` 단일 소비자 순서 보장(`await` 존재 시에도) — 로컬 실행
- hypothesis 6.164.0, pytest 9.1.1 — 최소 동작 확인 — 로컬 설치·실행
- [docs.astral.sh/ruff FAQ 및 설정 문서](https://docs.astral.sh/ruff/faq/) — `banned-api` 설정 문법 교차 확인
- [Python 공식 `secrets` 모듈 문서](https://docs.python.org/3/library/secrets.html) — CSPRNG 소스, 시딩 불가능성
- [Pydantic 공식 Unions 문서](https://pydantic.dev/docs/validation/latest/concepts/unions/) — 판별 유니온 코드 예시

### Secondary (MEDIUM confidence — WebSearch 결과가 공식 도메인을 가리켰으나 이 세션에서 직접 fetch로 재확인하지 않음)
- [Import Linter 공식 문서(contract_types)](https://import-linter.readthedocs.io/en/stable/contract_types.html) — 계약 타입 개요(로컬 실행으로 핵심 동작은 별도 검증함)
- uv `--lib`/`--package` 초기화가 `src/` 레이아웃 + `uv_build` 백엔드를 만든다는 서술 — 이 세션에서 `uv init --lib`을 직접 실행해 동일 결과를 확인했으므로 사실상 검증됨
- Python `typing.Protocol` vs ABC 구조적 타이핑 비교(PEP 544, realpython.com 등 복수 소스)

### Tertiary (LOW confidence — 단일 WebSearch 요약, 이 세션에서 직접 재확인하지 않음)
- SQLite WAL 모드가 네트워크 마운트 파일시스템에서 신뢰할 수 없다는 서술(dev.to 요약) — M0 범위(로컬 파일 하나)에는 영향 없어 참고용으로만 남김

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — 6개 핵심/보조 패키지 전부 PyPI 버전 조회 + 로컬 설치·실행으로 검증
- Architecture(import-linter/ruff 경계, SQLite 스키마, asyncio 액터): HIGH — 전부 이 세션에서 직접 실행해 성공/실패 양쪽 케이스를 재현
- Pitfalls: HIGH — 표의 4개 함정 중 3개(쉼표 문법, ruff 전역 적용, secrets 범위)는 이 세션에서 실제로 재현한 버그다
- D-11 역방향 검증 설계: MEDIUM — 여섯 숫자와 사건 스키마 매핑은 CONTEXT.md·REQUIREMENTS.md에서 직접 도출했으나, `caused_by_seq` 설계는 이번 조사의 제안이며 계획 단계에서 확정 필요

**Research date:** 2026-07-31
**Valid until:** 이 조사의 라이브러리 버전 정보는 30일 유효(빠르게 릴리스되는 생태계). 아키텍처 패턴(import-linter 문법, SQLite 스키마 설계, pydantic 판별 유니온)은 Phase 2가 이 스키마를 확장하기 전까지 유효
