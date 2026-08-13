"""모델 출력에서 JSON 배열을 뽑아 파싱하는 강건 파서 — 여러 판단 에이전트가 공유한다.

`action_classifier.py`에 있던 정규식 세 개와 파싱 함수 본문을 한 글자도
바꾸지 않고 이 파일로 옮겼다(이 모듈은 `agents` 안에서 아무것도 import하지
않는 잎(leaf)이다). 3단계 파싱 규약은 그대로다: ① 원문 그대로 먼저 시도
② `<think>` 블록 제거 + 코드펜스 벗기기 후 재시도 ③ 그래도 실패하면 빈 목록.
"""

import json
import re

THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
"""공개 이름(10-01) — 서사 경로(`agents/narration_guard.py`)가 이 정규식을 그대로
가져다 쓴다. 정규식 본문은 한 글자도 바뀌지 않았다 — 이름만 `_THINK_BLOCK`에서
`THINK_BLOCK`으로 올랐다(leaf 성질은 그대로 유지)."""
_CODE_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_JSON_ARRAY = re.compile(r"\[.*\]", re.DOTALL)


def try_parse_json_array(raw_text: str) -> list:
    """모델 출력에서 JSON 배열을 뽑아 파싱한다.

    「JSON 배열로만 응답하라」는 지시를 실제 모델은 종종 어긴다 — 특히
    추론형 모델(예: NIM의 Nemotron 계열)은 `<think>...</think>` 추론 과정이나
    마크다운 코드펜스, 설명 문장을 JSON 앞뒤에 덧붙인다. 애매한 문장일수록
    모델이 더 오래 "생각"하고 더 많은 부가 텍스트를 낸다 — 원문 그대로
    `json.loads`만 시도하면 이 경우 예외 없이 조용히 빈 목록으로 떨어져,
    "모델이 후보를 못 찾았다"와 "모델 출력을 못 읽었다"가 구분 없이
    뒤섞인다.

    ① 원문 그대로 먼저 시도한다 — 지시를 그대로 따르는 모델은 여기서
    끝난다(기존 동작 그대로, 회귀 없음). ② 실패하거나 리스트가 아니면
    `<think>` 블록을 지우고 마크다운 코드펜스를 벗긴 뒤 첫 `[`부터 마지막
    `]`까지를 다시 시도한다. ③ 그래도 리스트가 아니면 빈 목록으로
    취급한다 — 빈 목록은 정상적인 "무브 없음"/"판단 없음" 결과와 똑같이
    처리된다.
    """
    try:
        parsed = json.loads(raw_text)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    text = THINK_BLOCK.sub("", raw_text)
    fence_match = _CODE_FENCE.search(text)
    if fence_match:
        text = fence_match.group(1)
    array_match = _JSON_ARRAY.search(text)
    if array_match:
        text = array_match.group(0)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []
