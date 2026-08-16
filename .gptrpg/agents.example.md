# `agents.example.json`을 왜 이 값으로 채웠나 (G-11-2)

JSON 파일 자체에는 주석을 못 넣으므로, 이 값을 고른 이유는 옆 파일 대신
여기에 남긴다.

## 쓰는 법

```
cp .gptrpg/agents.example.json .gptrpg/agents.json
```

복사한 뒤 `uv run gptrpg agents show`로 값이 실제로 보이는지 확인한다.
`.gptrpg/agents.json`은 여전히 `.gitignore` 대상이다(운영자별 실제
설정이므로 저장소에 안 들어간다) — `.example.json`만 커밋된 참고값이다.

## 왜 이 두 모델인가

`action_classifier`/`master_gm` 두 값은 Phase 11이 실제 AI 호출로 직접 잰
결과다. 짐작이 아니다.

- **`action_classifier`가 `meta/llama-3.1-8b-instruct`(더 작은 모델)면**
  "굴릴 필요 없음"(no_check) 판정이 실전에서 거의 안 켜진다 — "문을 연다"
  처럼 교과서적인 예시 문장조차 `defend`로 잘못 분류했다. 근거·측정
  방법·전체 표: [`11-MODEL-FINDING.md`](../.planning/phases/11-rulebook-vocabulary/11-MODEL-FINDING.md)

- **`master_gm`이 `nvidia/nemotron-3-super-120b-a12b`(더 작은 모델)면**
  한국어 서사에 키릴 문자·영어 낱말·조어가 섞인다(실측 오염률 40%,
  큰 모델로 되돌리면 0%). 근거·측정 방법·전체 표:
  [`11-NARRATION-LANGUAGE-FINDING.md`](../.planning/phases/11-rulebook-vocabulary/11-NARRATION-LANGUAGE-FINDING.md)

**두 결함은 이 저장소의 자동 시험으로는 잡히지 않는다** — 시험은 전부 가짜
제공자를 쓰기 때문이다. 모델을 바꿔볼 때는 실제로 몇 문장 넣어 눈으로
확인해야 한다(위 두 문서의 측정 방법을 그대로 재사용하면 같은 기준으로
비교된다).

`meta/llama-3.1-8b-instruct`/`nvidia/nemotron-3-super-120b-a12b`로 설정한 채
서버나 CLI를 기동하면 이 사실이 stderr에 경고로 뜬다(막지는 않는다) —
`src/gptrpg/agents/model_recommendations.py`가 이 표를 코드로도 갖고 있다.
