# Deferred Items — Phase 12.3

範위 밖(out-of-scope) 발견 — 고치지 않고 기록만 남긴다(실행자 스코프 경계 규칙).

## 12.3-11에서 발견

- **`tests/test_clock_condition_web.py::test_condition_advance_segment_index_ignores_any_number_embedded_in_why`
  — 시간 의존 flaky 시험.** 전체 회귀(`.venv/bin/python -m pytest -q --tb=short`) 중
  1회 실패, 즉시 재실행하면 통과. 원인: 이 시험이 `"999" not in json.dumps(...)`로
  이벤트 JSON에 우연히 `999`가 없어야 통과하는데, 이벤트의 ISO 타임스탬프
  밀리초 필드가 우연히 `.999Z`로 끝나면(1000분의 1 확률) 실패한다 — 시험이
  검증하려는 것(`trigger` 문자열 안에 숫자가 안 새는가)과 무관한 우연의
  일치다. `src/gptrpg/` 아래를 12.3-11이 한 줄도 안 고쳤으므로(`git diff
  --name-only -- src/gptrpg`가 빈 출력) 이 계획이 만든 결함이 아니다 — 이
  계획의 범위(화면 쪽 안전한 맥락 결함)를 벗어난 사전 존재 시험 품질
  문제라 고치지 않는다. 다음에 이 파일을 여는 계획이 참고할 것: 타임스탬프
  생성을 시험 안에서 고정하거나, 검증 방식을 `trigger` 필드만 정확히
  비교하는 쪽으로 바꾸면 이 우연이 사라진다.
