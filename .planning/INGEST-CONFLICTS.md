## Conflict Detection Report

수집 문서 5건 · 모드 `new` · 우선순위 `ADR > SPEC > PRD > DOC`
잠금 ADR 1건 (`docs/GPTRPG-M0-decisions.md`) · 사용자가 5건 전부 포함하도록 명시 선택

### BLOCKERS (0)

없음. 잠금 ADR이 1건뿐이므로 LOCKED-vs-LOCKED 모순이 성립하지 않고, UNKNOWN 또는 낮은 신뢰도 분류도 없다(5건 모두 medium 이상, `docs/GPTRPG-design-plan-v1-archive.md`는 high).

잠금 ADR 내부의 뒤집힌 결정(D5 원칙 2 원본, D20 "첫 캠페인 무료", D20 "유저 룰북 수익화 금지", D22 프리젠 30초 경로, D25 초안, D31 "상시 주입", D33 "전체 3초")은 경쟁 변형으로 올리지 않았다. 문서가 스스로 규약을 정하고 있기 때문이다 — "결정이 뒤집히면 기존 항목을 지우지 말고 **취소선 + 사유**를 남긴다"(`docs/GPTRPG-M0-decisions.md` 문서 목적란). 후행 항목을 권위로, 선행 항목을 이력으로 기록했다.

### WARNINGS (3)

[WARNING] v1 아카이브에 대체 표기가 없다 — 대체 사실이 전적으로 외부 진술에 의존
  Found: `docs/GPTRPG-design-plan-v1-archive.md`가 SPEC(신뢰도 high)으로 분류되었고 문서 본문 어디에도 superseded / status / 폐기 표기가 없다. 파일명의 `v1-archive`가 유일한 단서다.
  Found: `docs/GPTRPG-design-plan.md:4`가 이 파일을 `이전 버전`으로 지목하고, 같은 문서 부록 A(`:1034-1057`)가 v1에서 뒤집힌 항목 18건을 열거한다.
  Impact: 두 문서는 같은 SPEC 등급이라 **기본 우선순위로는 서로를 이길 수 없다.** 둘을 가르는 것은 우선순위가 아니라 대체이며, 그 대체 주장을 하는 쪽이 이득을 보는 후속 문서 자신뿐이다. 아카이브 파일만 따로 열어 본 사람이나 도구는 폐기된 설계를 유효한 명세로 읽는다.
  → `docs/GPTRPG-design-plan-v1-archive.md` 머리에 `상태: 폐기 · GPTRPG-design-plan.md(v2)로 대체됨` 한 줄을 넣거나, 이후 수집에서 이 파일을 제외한다. 지금 회차에서는 잠금 ADR이 뒤집힌 항목 하나하나를 독립적으로 재확인하므로 `ADR > SPEC` 규칙만으로도 해소되며(아래 INFO 참조), 이 경고는 문서 자체의 자기 기술 결함에 대한 것이다.

[WARNING] v1에만 있고 유지·폐기 진술이 어디에도 없는 구현 계약 2건
  Found: `docs/GPTRPG-design-plan-v1-archive.md §2.6.3`의 `AgentResult<T>` 응답 래퍼(success / data / error_code / error_message / latency_ms / token_usage / fallback_suggestion)와 타임아웃 정책(동기 호출 2초 Light · 5초 Medium · 15초 Heavy) · 재시도 정책(`MODEL_ERROR` 지수 백오프 최대 2회, `VALIDATION_FAILED` 재시도 없음).
  Found: `docs/GPTRPG-design-plan-v1-archive.md` 핸드오프 §2.1의 하트비트 5초 간격 · 3회 실패 시 재연결 · GM 스트리밍 중 재연결 시 마지막 완료 청크부터 재생성(멱등성 보장).
  Found: `docs/GPTRPG-design-plan.md` 부록 A의 폐기 목록과 유지 목록 어느 쪽에도 이 항목들이 없다. `docs/GPTRPG-M0-decisions.md` §5 지적 사항 대장에도 대응 항목이 없다.
  Impact: 폐기도 유지도 아닌 상태다. D33이 15초 타임아웃과 초과 시 화면 동작을 확정했으므로 Heavy 값은 정합하지만, Light 2초 / Medium 5초와 재시도 정책은 D17의 4개 에이전트 구성 위에서 재검토된 적이 없다. `error_code`의 `LOW_CONFIDENCE`는 D16이 신뢰도 임계값을 폐기하면서 근거를 잃었는데도 계약에 남아 있다. 우선순위로는 판정할 수 없다 — 반대 진술이 존재하지 않으므로 이길 상대가 없다.
  → M1 착수 전에 이 두 묶음의 생존 여부를 결정한다. `INTEL_DIR/constraints.md`에는 `[미결]`로 표시해 두었고 폐기 항목과 섞이지 않게 분리했다.

[WARNING] 원가 수치의 산출 전제가 D31과 어긋난다 — 아무도 다시 계산하지 않았다
  Found: `docs/GPTRPG-cost-analysis.md §1` 턴당 프롬프트 구성이 **「최근 대화 20턴 ~6,000 토큰」**을 전제로 입력 약 14,500을 잡고, 여기서 턴당 $0.039 → 1인 1시간당 $0.30이 나온다.
  Found: `docs/GPTRPG-M0-decisions.md §2 D31`(잠금)은 매 턴 주입을 **「최근 대화 몇 턴, 초기값 10턴」**으로 확정하고 엔티티 장부 상시 주입을 폐기했다. `docs/GPTRPG-design-plan.md §3.8`도 10턴으로 적는다.
  Found: `docs/superpowers/specs/2026-07-30-m0-closeout-design.md §6`의 파일별 변경 목록은 원가 문서에 대해 **§7 레이턴시 절 표기만** 바꾸도록 지시했다. §1은 갱신 대상이 아니었다.
  Impact: 우선순위는 **규칙**만 해소한다(ADR > DOC이므로 10턴이 이긴다). 그러나 **숫자**는 해소하지 못한다 — 10턴 기준으로 재계산한 원가를 적은 문서가 하나도 없기 때문이다. $0.30 / $0.20 / $3.6은 D19·D20과 `docs/GPTRPG-design-plan.md §9.1`에도 그대로 전재되어 있다. 이 수치들은 가설 H5의 멈출 조건($1 초과)과 무료 티어 원가 판단의 입력값이며, H5는 프로젝트를 멈출 수 있는 진짜 킬 조건 둘 중 하나다.
  → 원가 문서 §1 프롬프트 구성표를 D31의 4항목 기준으로 재작성하고 파생 수치를 다시 계산하거나, 최소한 §1에 "이 표는 D31 이전 전제이며 실측으로 대체된다"를 명시한다. M0 실측 항목에 「주입할 최근 턴 수」가 이미 올라 있으므로 실측 후 일괄 보정도 가능하다.

### INFO (7)

[INFO] 인용 그래프에 순환 2건 — 권위 그래프는 비순환이므로 게이트하지 않음
  Note: 교차 참조 그래프에 순환이 있다. `GPTRPG-M0-decisions.md → GPTRPG-design-plan.md → GPTRPG-M0-decisions.md`, 그리고 `GPTRPG-M0-decisions.md → GPTRPG-design-plan.md → GPTRPG-cost-analysis.md → GPTRPG-M0-decisions.md`. 탐색 깊이는 상한 50을 크게 밑돈다.
  Note: 그러나 우선순위 해소가 실제로 타는 것은 **권위 간선**이며 그쪽은 비순환이고 뿌리가 하나다. `docs/GPTRPG-cost-analysis.md:283` "권위는 `GPTRPG-M0-decisions.md`에 있다" / `docs/GPTRPG-design-plan.md:5` "결정 근거: `GPTRPG-M0-decisions.md`" / `docs/superpowers/specs/2026-07-30-m0-closeout-design.md:270` "권위는 `GPTRPG-M0-decisions.md`에 둔다". 반대 방향의 두 간선은 권위 위임이 아니라 다른 성격이다 — `docs/GPTRPG-M0-decisions.md:5`는 기획 명세서를 **갱신 대상 산출물**로 지목하고, `:528`은 원가 문서를 **상세 자료**로 가리킨다. 권한을 넘기는 문장이 아니다.
  Note: 즉 "A는 B를 보라, B는 A를 보라"로 결정 내용이 어디에도 없는 권위 공백형 순환이 아니라, 동반 문서 간의 정상적인 상호 인용이다. 순환 규칙을 문자 그대로 적용하면 5건 중 3건의 합성을 중단해야 하고 사용자가 고칠 수 있는 방법도 없으므로(동반 문서에서 상호 인용을 제거하라는 요구가 된다) BLOCKER로 올리지 않고 합성을 진행했다. **이 판단은 규칙의 문자 그대로의 적용에서 벗어난 것이므로 명시적으로 남긴다.**

[INFO] 자동 해소: 잠금 ADR > 폐기된 v1 SPEC (18개 항목)
  Note: `docs/GPTRPG-design-plan-v1-archive.md`의 항목들이 `docs/GPTRPG-design-plan.md`(v2)와 정면으로 어긋나지만 둘은 같은 SPEC 등급이라 우선순위로는 판정되지 않는다. 그러나 어긋나는 항목 하나하나를 잠금 ADR이 독립적으로 판정하므로 `ADR > SPEC` 규칙으로 해소된다 — 룰북별 전용 어댑터(D5) / 첫 타깃 D&D 5e(D4) / 서브에이전트 10개(D17) / 스포트라이트 토큰·이니셔티브 강제 정렬(D10) / 3초 리액션 팝업(D10) / AFK 타임아웃 강제 스킵(D10) / confidence 0.9 임계값(D16) / E2E 3초(D33) / 엔티티 장부 상시 주입(D31) / 적 데이터 표현 부재(D32) / 세션 중심 설계(D2) / 13클래스 드롭다운 온보딩(D22) / 시나리오의 룰북 종속(D8) / SRD "우회"(D29) / 유저 룰북 수익화 금지(D29) / 할루시네이션 완벽 방어(D12) / 검증 기준 13개(D30) / Provably Fair 우선순위 하향(D14). 잠금 ADR이 이겼고 v1 항목은 `INTEL_DIR/constraints.md` B절에 `[폐기]`로 격리했다.
  Note: 15×15 그리드 · A* · 서버 권위 Fog of War는 **폐기가 아니라 M4로 연기**다(D13⑥ · D17 · D32). 폐기와 연기를 섞지 않도록 별도 표기했다.
  Note: 반대로 v2 부록 A는 v1의 판단 11건을 명시적으로 유지한다(Pending & Commit / 문장 청크 전송 / 이벤트 기반 압축 트리거 / 자주 조회되는 필드 컬럼 분리 등). 이 항목들은 `[유지]`로 남겼다.

[INFO] 자동 해소: 중복 출처 — 종결 설계안은 독립 결정을 기여하지 않음
  Note: `docs/superpowers/specs/2026-07-30-m0-closeout-design.md`가 ADR(locked=false)로 분류되어 D31·D32·D33을 담고 있으나, 같은 세 결정이 잠금 ADR `docs/GPTRPG-M0-decisions.md §2`에도 있다. 대조 결과 내용이 일치하며 잠금 ADR 쪽이 상위집합이다 — D31의 「초기값 10턴」·「미룸」·「폐기한 대안」 문단, D32의 원칙 3 연장 서술이 잠금 ADR에만 있다. 모순은 없다.
  Note: 이 문서는 스스로 성격을 밝힌다 — §0 "M0 설계 단계를 닫기 위한 **변경 명세**", §6 파일별 변경 목록(이미 적용됨), §7 "권위는 `GPTRPG-M0-decisions.md`에 둔다". 즉 독립 출처가 아니라 이미 반영된 변경 지시서다. `LOCKED > 비LOCKED` 규칙과 문서 자신의 권위 위임이 같은 방향을 가리키므로 잠금 ADR을 단일 출처로 삼았고, `INTEL_DIR/decisions.md`의 D31~D33에는 중복 출처를 병기했다.

[INFO] 사용자가 종결 설계안의 수집 제외 지시 2건을 명시적으로 무효화함
  Note: `docs/superpowers/specs/2026-07-30-m0-closeout-design.md §7`은 재수집 시 지킬 것으로 두 가지를 지시한다 — ① `docs/GPTRPG-design-plan-v1-archive.md`를 다시 제외한다("v1이 들어오면 뒤집힌 결정들이 경쟁 후보로 되살아난다") ② 이 설계안 자신도 수집 대상이 아니다("결정의 출처가 두 곳이 된다").
  Note: 사용자가 두 파일 모두에 대해 경고를 받은 뒤 5건 전부 포함을 선택했다. 문서의 지시가 아니라 사용자의 선택이 우선한다. 다만 문서가 경고한 위험 자체는 실재하므로 두 위험을 각각 구조로 차단했다 — v1은 `constraints.md` B절에 `[폐기]` 표기로 격리해 경쟁 후보로 부활하지 못하게 했고, 종결 설계안은 위 INFO대로 중복 출처로 접어 결정의 출처를 한 곳으로 유지했다.
  Note: `--mode new` 조건과 `.planning/` 제거 조건은 이번 회차에서 충족되었다.

[INFO] 자동 해소: 마일스톤 로드맵 표 — 잠금 ADR이 기획 명세서보다 완전함
  Note: `docs/GPTRPG-M0-decisions.md §3`의 M2 항목은 "공개방 매칭 · 톤 필터 · 신고·차단 · 성인 인증 · 솔로 모드 · 비동기 PbP · 다이스풀/Year Zero 판정 방식 · 테이블 생성"이나 `docs/GPTRPG-design-plan.md §11`의 M2는 "솔로 모드 · 비동기 · 낯선 사람 매칭 + 신고·차단·성인 인증 · 다이스풀/Year Zero"로 **톤 필터와 테이블 생성이 빠져 있다.** 모순이 아니라 누락이며(테이블/절차 생성은 같은 문서 §4.8이 M2로 적는다), `ADR > SPEC`로 잠금 ADR 표를 권위로 채택했다.
  Note: M0·M1·M3·M4 행은 두 문서가 일치한다. 특히 두 표 모두 M0에 **킬 크리테리아 실험**을 포함하며, 이는 직전 회차에서 문제였던 상태 불일치가 해소되었음을 뜻한다.

[INFO] 자동 해소: 기획 명세서 헤더의 결정 건수가 낡음
  Note: `docs/GPTRPG-design-plan.md:5`가 "결정 근거: `GPTRPG-M0-decisions.md` (**결정 30건**, 각 항목의 사유와 폐기 이력)"으로 적으나 잠금 ADR은 D1~D33으로 33건이다. D31~D33이 추가될 때 헤더가 갱신되지 않았다. 내용상의 모순은 없다 — 기획 명세서 본문 §3.8 · §4.9 · §3.6이 D31·D32·D33을 이미 반영하고 있다. 잠금 ADR을 권위로 33건을 채택했다.

[INFO] 문서 상태 표기가 두 문서에서 일치 — "완료"가 아님이 양쪽에 명시됨
  Note: `docs/GPTRPG-M0-decisions.md:9` `상태: 설계 확정 · 실험 미실시`, `docs/GPTRPG-design-plan.md:3` `작성: 2026-07-30 (마일스톤 0 설계 종결 시점 · 실험 전)`. 두 표기가 같은 방향으로 정렬되어 있다.
  Note: 잠금 ADR `:11-13`이 못박는다 — "**'완료'가 아니다.** 마일스톤 0은 설계와 킬 크리테리아 실험 두 부분이고, 끝난 것은 설계뿐이다. 실험이 가설 H1(재미)과 H5(원가)의 판정을 들고 있으며 이 둘은 진짜 킬 조건이다 — 프로젝트가 여기서 멈출 수 있다."
  Note: 용어 잔재 — `docs/GPTRPG-M0-decisions.md §3`이 "커널"을 "판정 방식"으로 통일한다고 선언했으나 같은 문서의 D6 표 머리글·원칙 2·D7 3층 구조에는 "커널" 표기가 남아 있다. 기획 명세서는 전부 "판정 방식"이다. 의미 충돌은 없다.
