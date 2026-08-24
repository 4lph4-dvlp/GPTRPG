#!/usr/bin/env python3
"""폰이나 좁은 창에서 놀이 화면의 **서사 칸이 실제로 살아 있는지**, 진짜
헤드리스 크로미움으로 실제 `styles.css`를 얹어 확인한다(Phase 12.3-15,
`12.3-UAT.md` `G-12.3-29`).

**왜 이 스크립트가 있는가.** 사람이 폰으로 놀이 화면을 열었더니 이야기가
나오는 칸이 아예 없었다. 세로 골격(`@media (max-width: 1080px)`)의 세 행
중 가운데 행(서사)만 최소 높이가 0이라, 위(상태)·아래(대화) 두 칸이
가져가고 남은 것을 서사가 혼자 뒤집어쓴다 — 실측 `390×844 → 0px`.

**왜 기존 시험이 못 잡았는가.** 이 저장소의 화면 시험(vitest)은 node에서
도는 **순수 함수 시험**이고 jsdom·RTL이 없다 — **배치(layout)를 잴 수 있는
도구가 애초에 없다.** 그래서 이 규칙은 저장소 첫 커밋(7821dc0,
2026-08-05)부터 1년 가까이 살아 있었고 어떤 시험에도 안 걸렸다. `12.3-11`이
「127.0.0.1로만 열어 본다」는 공백을 `check_insecure_origin.py`로 메운 것과
정확히 같은 모양의 공백이다.

**무엇을 어떻게 재는가.** 진짜 헤드리스 크로미움에 실제 `frontend/src/styles.css`를
얹고, **크기를 픽셀로 못 박은 `srcdoc` iframe** 안에서 세 칸의 높이를
`getBoundingClientRect()`로 직접 잰다. iframe을 쓰는 이유 — **헤드리스 창은
요청한 크기를 그대로 안 준다**(`--window-size=390,844`로 열어도 실측
뷰포트는 다른 값이 된다. 크로미움이 창 너비에 하한을 두고, 브라우저 껍데기가
높이를 먹는다). iframe은 지정한 픽셀이 곧 그 문서의 뷰포트라 `dvh` 단위가
정확히 계산되고, 한 번 띄운 브라우저 안에서 네 형태를 연달아 잴 수 있다.
`srcdoc` iframe은 부모와 같은 출처로 취급되어 부모 스크립트가
`contentDocument`를 그대로 읽을 수 있다 — `file://` 문서끼리의 접근을 막는
제약에 안 걸리므로 크로미움에 추가 플래그가 필요 없다.

이 확인은 CSS만 본다 — `npm run build`도 서버도 필요 없다.
`check_insecure_origin.py`가 자바스크립트 동작(빈 화면 여부)을 보느라
반드시 빌드해야 하는 것과 의도적으로 다르다. 그래서 몇 초 만에 돈다.

**종료 코드 세 개의 뜻 — `2`는 `0`이 아니다.**

- `0` — 통과. 네 형태(1440×900 대조군 · 960×1080 · 390×844 · 844×390)
  전부에서 서사 칸이 뷰포트 높이의 4분의 1 이상이고, 골격이 안 넘치고,
  조작 칸(`select`/`input[type="number"]`)이 44px 이상이다.
- `1` — 실패. 어느 형태에서 서사가 죽었거나, 골격이 화면 밖으로 넘쳤거나,
  조작 칸이 44px보다 얇다.
- `2` — **확인 불가.** 크로미움이 없음 · `styles.css`가 없음 · 크로미움
  실행 자체가 실패함 · 측정값을 못 읽음 · **고정판이 실제 화면과 갈림**
  (아래 `check_fixture_still_mirrors_source` 참조). **`2`를 `0`으로 접지
  않는다** — 확인을 못 한 상황이 통과로 보이는 것이 정확히 이 결함군이
  1년 가까이 살아남은 이유다.

새 꾸러미를 하나도 안 쓴다 — 표준 라이브러리와 이 기계에 이미 있는
크로미움(`/usr/bin/chromium`)만 부른다. 크로미움을 찾는 방법은
`check_insecure_origin.py`의 것을 그대로 import해서 쓴다(아래 참조) — 두
확인이 같은 방법으로 브라우저를 찾는 것 자체가 이 import의 값어치다.

사용법:

    .venv/bin/python scripts/check_narrow_viewport.py
"""

from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# 스크립트로 실행하면 파이썬이 이 파일의 디렉터리(scripts/)를 sys.path[0]에
# 자동으로 넣으므로 별도 경로 조작 없이 바로 import된다. 이 import가
# 안전한 두 가지 이유: (1) check_insecure_origin.py의 실행부가
# `if __name__ == "__main__":`으로 막혀 있어 import만으로는 서버를 띄우거나
# 어떤 부작용도 안 일으킨다. (2) find_chromium/CHROMIUM_CANDIDATES는 상수와
# 순수 함수라 두 확인이 항상 같은 방법으로 같은 브라우저를 찾는다.
from check_insecure_origin import CHROMIUM_CANDIDATES, find_chromium  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
CSS_PATH = REPO_ROOT / "frontend" / "src" / "styles.css"

DOM_DUMP_TIMEOUT_S = 60
VIRTUAL_TIME_BUDGET_MS = 8000
# 서사 칸의 최소 비율 — 「0보다 크다」로 잡으면 1px도 통과하므로, 서사가
# 이 화면의 본체라는 것(PROJECT.md 핵심 가치 「이야기가 어떻게 끝나는지
# 보고 싶어서 다시 접속한다」)에 맞춰 세로의 4분의 1을 최소선으로 잡는다.
MIN_STORY_HEIGHT_RATIO = 0.25
# --touch-target-min (frontend/src/styles.css의 :root 토큰)과 같은 값.
TOUCH_TARGET_MIN_PX = 44
# 문서 전체 높이가 뷰포트를 이만큼(픽셀) 넘게 넘치면 실패로 본다 — 부동소수
# 반올림 오차를 흡수하기 위한 여유다.
OVERFLOW_TOLERANCE_PX = 1

# 내 줄과 남의 줄의 배경색이 갈리는지는 형태와 무관한 단언(G-12.3-27)이라
# 네 형태 전부에서 반복할 필요가 없다 — 폰 세로 한 형태에서만 본다.
MINE_LINE_COLOR_CHECK_SHAPE = "390x844"

# 네 형태. 1440×900은 넓은 창의 대조군(3컬럼이 그대로인지 본다). 960×1080은
# 1920×1080 화면의 절반 폭(사장님이 실제로 보고한 형태). 390×844는 폰
# 세로. 844×390은 폰 가로 — 세로 높이가 가장 모자란 형태라 픽셀 바닥의
# 함정이 가장 먼저 드러난다.
SHAPES = [
    {"name": "1440x900", "width": 1440, "height": 900},
    {"name": "960x1080", "width": 960, "height": 1080},
    {"name": "390x844", "width": 390, "height": 844},
    {"name": "844x390", "width": 844, "height": 390},
]

# 사람이 실제로 손가락으로 누르는 조작 요소 목록(12.3-16 Task 2) —
# 자바스크립트(측정)와 파이썬(judge의 사유 문장) 양쪽이 이 하나의 목록을
# 돈다. 대상마다 코드를 복사하면 다음에 하나 늘 때 한쪽만 늘어난다.
# 세 번째 칸(checkHeight)이 44px 하한을 거는지를 가른다 — `.composer`
# (조작부 전체 상자)에는 안 걸고, 실제로 손가락이 닿는 낱개 조작
# 요소에만 건다. 여럿을 돌려주는 선택자(`.candidate`·`.proposal .btn`)는
# 전부 재고, 그중 하나라도 못 닿으면 실패다.
TOUCH_TARGETS: list[tuple[str, str, bool]] = [
    (".composer", "조작부 전체", False),
    (".composer__input", "말 쓰는 칸", True),
    (".composer__row .btn", "보내기 단추", True),
    (".proposal .btn", "제안 카드의 다시 쓰기 단추", True),
    (".candidate", "GM 제안 후보 버튼", True),
    ("select", "능력치 배치 칸", True),
    ('input[type="number"]', "점수 숫자칸", True),
]

# 고정판이 흉내 내는 실제 화면 클래스 이름들 — 이 이름들이 소스에서
# 사라지면 고정판은 더 이상 실제 화면을 안 비춘다(T-12.3-67). ChatPane과
# CreationPane 둘 다 12.3-16에서 세 층(chat__head는 ChatPane 전용 —
# CreationPane은 그 자리에 turnLabel을 쓴다)·composer·proposal을 새로
# 흉내 내기 시작했으므로 여기 함께 늘렸다.
REQUIRED_SOURCE_CLASS_NAMES: dict[str, list[str]] = {
    "frontend/src/panes/StatusPane.tsx": ["pane--status"],
    "frontend/src/panes/StoryPane.tsx": ["pane--story"],
    "frontend/src/panes/ChatPane.tsx": [
        "pane--chat",
        "chat__head",
        "chat",
        "composer",
        "proposal",
        "chat-line--mine",
    ],
    "frontend/src/panes/CreationPane.tsx": [
        "chat-line--mine",
        "chat",
        "composer",
        "proposal",
    ],
}

# `className=` 속성값(단순 문자열이든 `{조건 ? "a" : "b"}` 삼항식이든) 안에서
# 이름 하나를 낱말 경계로 찾는다. `className=` 뒤 `{...}`나 `"..."`
# 구간만 본다 — 그래서 주석에 이름만 적혀 있어도 통과하던 구멍(단순
# `class_name not in text`)이 막힌다. 경계는 "앞뒤가 낱말 문자(밑줄
# 포함)도 하이픈도 아닌 자리"다 — 그래서 `chat`은 `chat-line`·
# `chat__head`·`pane--chat`의 부분 문자열로는 안 걸리고, `className="chat"`
# 같은 완전한 토큰에만 걸린다.
_CLASS_NAME_ATTR_RE = re.compile(r'className=(?:\{[^}]*\}|"[^"]*")', re.DOTALL)


def _class_name_present_in_jsx(text: str, class_name: str) -> bool:
    boundary = r"(?<![\w-])" + re.escape(class_name) + r"(?![\w-])"
    return any(
        re.search(boundary, match.group(0)) is not None
        for match in _CLASS_NAME_ATTR_RE.finditer(text)
    )


def check_fixture_still_mirrors_source() -> list[str]:
    """고정판이 흉내 내는 클래스 이름들이 실제 소스에 아직 있는지 본다.

    하나라도 없으면 마크업이 바뀐 것이고, 이 스크립트의 고정판은 더 이상
    실제 화면을 안 비춘다 — 그때 통과(0)를 찍으면 그물이 조용히
    헐거워진다. 이 조항이 막는 것은 **이름이 사라지는** 종류의 드리프트뿐이다
    (`className=` 문맥에서 낱말 경계로 찾는다). **중첩 구조가 바뀌는**
    종류의 드리프트는 원리적으로 못 잡는다 — 이름은 다 살아 있는데 고정판이
    그 이름들을 실제 화면과 다른 순서·다른 부모자식 관계로 담는 경우다
    (12.3-16이 닫은 결함이 정확히 이 종류였다: `.composer`·`.proposal`
    이름은 있었지만 고정판이 그것들을 아예 안 담고 있었다).
    """
    missing: list[str] = []
    for rel_path, class_names in REQUIRED_SOURCE_CLASS_NAMES.items():
        path = REPO_ROOT / rel_path
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            missing.append(f"{rel_path} — 파일을 못 읽음({exc})")
            continue
        for class_name in class_names:
            if not _class_name_present_in_jsx(text, class_name):
                missing.append(f"{rel_path} — '{class_name}' 클래스를 못 찾음")
    return missing


def build_inner_html(css_uri: str) -> str:
    """실제 화면과 같은 클래스 이름의 골격을 담은 고정판(fixture) 문서.

    상태 칸에 일부러 900px짜리 블록을 넣는 이유: 상태 칸의 높이는
    룰북·캐릭터·자원 축에 따라 얼마든지 자란다(폰에서 실측 506px). 실제
    내용을 흉내 내면 그 흉내가 낡는 순간 그물이 조용히 헐거워지므로,
    흉내 내지 않고 「상태 칸이 아무리 커져도 서사가 안 죽는가」를 직접
    시험한다 — 이 고정판은 실제보다 일부러 더 가혹하다.

    대화판(`.pane--chat`)도 같은 원칙이다 — `ChatPane.tsx`의 세 층
    (`.chat__head` → `.chat` → `.composer`) 그대로를 담되, `.composer`
    안에는 놀이 중 가장 잦고 가장 높은 상태(GM 제안 카드 — 후보 버튼
    둘 + 다시 쓰기 하나)를 넣는다. 실제 내용을 흉내 내지 말고 가장
    가혹한 상태를 넣는다는 원칙은 상태 칸 900px 블록과 같다(12.3-16).
    """
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<link rel="stylesheet" href="{css_uri}">
</head>
<body>
<div class="shell">
  <aside class="pane pane--status">
    <div style="height: 900px;"></div>
    <select><option>선택</option></select>
    <input type="number" value="1">
  </aside>
  <main class="pane pane--story"></main>
  <section class="pane pane--chat">
    <div class="chat__head">
      <p class="t-caps">모두의 행동</p>
    </div>
    <div class="chat">
      <div class="chat-line">
        <div class="chat-line__who">남</div>
        <div class="chat-line__text">남의 말</div>
      </div>
      <div class="chat-line chat-line--mine">
        <div class="chat-line__who">나</div>
        <div class="chat-line__text">내 말</div>
      </div>
    </div>
    <div class="composer">
      <div class="proposal">
        <p class="t-caps">어느 쪽인가요</p>
        <button type="button" class="candidate">후보 1</button>
        <button type="button" class="candidate">후보 2</button>
        <button type="button" class="btn btn--ghost btn--wide">다시 쓰기</button>
      </div>
      <form class="composer__row">
        <input class="composer__input" type="text" placeholder="무엇을 하나요?">
        <button type="submit" class="btn btn--primary">보내기</button>
      </form>
      <div class="composer__status">상태 문구</div>
    </div>
  </section>
</div>
</body>
</html>"""


def build_host_html(css_uri: str) -> str:
    """네 형태를 순서대로 재는 바깥 문서.

    iframe을 하나 만들어 onload에서 재고, 지우고, 다음 것으로 넘어간다
    (한 번에 하나씩 — 동시에 네 개를 띄우면 레이아웃 계산 시점이 서로
    간섭할 수 있다). 다 잰 값은 `<pre id="measured">`에 JSON으로 담는다.
    """
    inner_html_json = json.dumps(build_inner_html(css_uri))
    shapes_json = json.dumps(SHAPES)
    tolerance_json = json.dumps(OVERFLOW_TOLERANCE_PX)
    # 선택자만 넘긴다 — 44px 하한을 거는지(checkHeight)는 judge()가 대상
    # 이름으로 다시 갈라 결정하는 판정 규율이라 여기선 안 쓴다. 자바스크립트는
    # 대상마다 높이를 항상 재 두고, python judge()가 TOUCH_TARGETS의 세
    # 번째 칸을 보고 그 값을 쓸지 말지를 정한다.
    touch_target_selectors_json = json.dumps([selector for selector, _name, _check in TOUCH_TARGETS])
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body>
<pre id="measured">PENDING</pre>
<script>
(function () {{
  var SHAPES = {shapes_json};
  var INNER_HTML = {inner_html_json};
  var OVERFLOW_TOLERANCE_PX = {tolerance_json};
  var TOUCH_TARGET_SELECTORS = {touch_target_selectors_json};
  var results = [];

  // 「닿을 수 있는가」를 위치가 아니라 스크롤 경로 유무로 판정한다. 조상을
  // el에서 shell까지 거슬러 오르며: overflow-y가 auto|scroll인 조상을
  // 만나면 그 조상이 스크롤 경로이므로 비교 기준 상자를 그 조상 자신의
  // 상자로 바꿔 계속 오르고(그 안의 내용은 화면 밖에 있어도 손가락으로
  // 스크롤하면 닿는다), hidden|clip인 조상을 만나면 지금 비교 기준
  // 상자가 그 조상 상자를 OVERFLOW_TOLERANCE_PX보다 크게 벗어났는지
  // 본다 — 벗어났으면 그만큼은 스크롤로도 영영 안 닿는다. 이 구분이
  // 왜 필요한가: 상태 칸의 select/입력칸은 부모(.pane--status)가
  // overflow-y: auto라 화면 밖에 있어도 통과해야 하는데, 단순히
  // 「뷰포트를 넘었는가」로만 재면 그것을 거짓 빨강으로 찍는다. 반대로
  // 조작부(.composer)는 조상(.pane)이 overflow: hidden이라 넘친 만큼이
  // 정말로 안 닿는다 — 그 둘을 가르는 것은 위치가 아니라 스크롤 경로다.
  // 다 오른 뒤에는 마지막 비교 기준 상자의 아래끝이 뷰포트 안에 있는지
  // 본다.
  function reachable(win, shell, el) {{
    var ownBottom = el.getBoundingClientRect().bottom;
    var box = el.getBoundingClientRect();
    var current = el;
    while (current !== shell) {{
      var parent = current.parentElement;
      if (parent === null) {{ break; }}
      var overflowY = win.getComputedStyle(parent).overflowY;
      if (overflowY === "auto" || overflowY === "scroll") {{
        box = parent.getBoundingClientRect();
      }} else if (overflowY === "hidden" || overflowY === "clip") {{
        var parentBox = parent.getBoundingClientRect();
        if (
          box.top < parentBox.top - OVERFLOW_TOLERANCE_PX ||
          box.bottom > parentBox.bottom + OVERFLOW_TOLERANCE_PX
        ) {{
          return {{ bottom: ownBottom, blockedBy: parent.className }};
        }}
      }}
      current = parent;
    }}
    if (box.bottom > win.innerHeight + OVERFLOW_TOLERANCE_PX) {{
      return {{ bottom: ownBottom, blockedBy: "viewport" }};
    }}
    return {{ bottom: ownBottom, blockedBy: null }};
  }}

  function measure(shape, done) {{
    var iframe = document.createElement("iframe");
    iframe.style.border = "none";
    iframe.style.width = shape.width + "px";
    iframe.style.height = shape.height + "px";
    iframe.onload = function () {{
      var doc = iframe.contentDocument;
      var win = iframe.contentWindow;
      var shellEl = doc.querySelector(".shell");
      var statusEl = doc.querySelector(".pane--status");
      var storyEl = doc.querySelector(".pane--story");
      var chatEl = doc.querySelector(".pane--chat");
      var otherLineEl = doc.querySelector(".chat-line:not(.chat-line--mine)");
      var mineLineEl = doc.querySelector(".chat-line--mine");

      // 사람이 실제로 누르는 것 전부(TOUCH_TARGETS, 12.3-16 Task 2)를 같은
      // 목록으로 돈다 — 여럿을 돌려주는 선택자(.candidate·.proposal .btn)는
      // querySelectorAll로 전부 재고, 대상별로 [{{bottom, blockedBy, height}}]
      // 배열을 담는다. 44px 하한을 그 값에 걸지는 judge()(python)가
      // TOUCH_TARGETS의 checkHeight 칸을 보고 정한다 — 여기선 항상 잰다.
      var targets = {{}};
      TOUCH_TARGET_SELECTORS.forEach(function (selector) {{
        var elements = doc.querySelectorAll(selector);
        var entries = [];
        elements.forEach(function (el) {{
          var reach = reachable(win, shellEl, el);
          entries.push({{
            bottom: reach.bottom,
            blockedBy: reach.blockedBy,
            height: el.getBoundingClientRect().height
          }});
        }});
        targets[selector] = entries;
      }});

      results.push({{
        name: shape.name,
        innerWidth: win.innerWidth,
        innerHeight: win.innerHeight,
        statusHeight: statusEl.getBoundingClientRect().height,
        storyHeight: storyEl.getBoundingClientRect().height,
        chatHeight: chatEl.getBoundingClientRect().height,
        scrollHeight: doc.documentElement.scrollHeight,
        otherLineBg: win.getComputedStyle(otherLineEl).backgroundColor,
        mineLineBg: win.getComputedStyle(mineLineEl).backgroundColor,
        targets: targets
      }});
      document.body.removeChild(iframe);
      done();
    }};
    document.body.appendChild(iframe);
    iframe.srcdoc = INNER_HTML;
  }}

  function next(i) {{
    if (i >= SHAPES.length) {{
      document.getElementById("measured").textContent = JSON.stringify(results);
      return;
    }}
    measure(SHAPES[i], function () {{ next(i + 1); }});
  }}

  next(0);
}})();
</script>
</body>
</html>"""


def dump_dom(chromium: str, url: str) -> str | None:
    """`chromium --headless --dump-dom`으로 자바스크립트가 다 돈 뒤의 DOM을 읽는다.

    실패·시간 초과·실행 불가는 전부 `None`으로 접는다 — 호출자가 종료 코드
    2로 끝내도록 하기 위함이다(파이썬 기본 종료 코드 1로 새어 나가면
    「확인해 봤더니 실패」와 「확인을 못 함」이 섞인다).
    """
    try:
        result = subprocess.run(
            [
                chromium,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--dump-dom",
                f"--virtual-time-budget={VIRTUAL_TIME_BUDGET_MS}",
                "--window-size=1600,1200",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=DOM_DUMP_TIMEOUT_S,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        print(f"크로미움을 실행하지 못했다: {exc}", file=sys.stderr)
        return None
    if result.returncode != 0:
        print("크로미움이 고정판을 여는 데 실패했다:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return None
    return result.stdout


def extract_measurements(dom: str) -> list[dict] | None:
    match = re.search(r'<pre id="measured">(.*?)</pre>', dom, re.DOTALL)
    if match is None:
        print("DOM에서 <pre id=\"measured\">를 못 찾았다.", file=sys.stderr)
        return None
    raw = html.unescape(match.group(1)).strip()
    if raw == "PENDING":
        print(
            "측정이 끝나기 전에 읽었다(PENDING으로 남음) — virtual-time-budget이 "
            "모자랐을 수 있다.",
            file=sys.stderr,
        )
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"측정값을 JSON으로 못 읽었다: {exc}", file=sys.stderr)
        return None
    if not isinstance(data, list) or len(data) != len(SHAPES):
        print(
            f"형태 {len(SHAPES)}개가 다 안 왔다(받은 개수: "
            f"{len(data) if isinstance(data, list) else '알 수 없음'}).",
            file=sys.stderr,
        )
        return None
    return data


def judge(measurement: dict) -> tuple[bool, list[str]]:
    """형태 하나의 측정값을 판정한다. (통과 여부, 실패 사유 목록)을 돌려준다."""
    reasons: list[str] = []
    viewport_height = measurement["innerHeight"]

    # ① 서사 칸이 뷰포트 높이의 4분의 1 이상이다 — 서사는 이 화면의
    # 본체이고, 어느 형태에서도 세로의 4분의 1은 받아야 읽을 수 있다.
    min_story_height = viewport_height * MIN_STORY_HEIGHT_RATIO
    if measurement["storyHeight"] < min_story_height:
        reasons.append(
            f"서사 칸이 {measurement['storyHeight']:.1f}px로 최소선 "
            f"{min_story_height:.1f}px(뷰포트의 25%)보다 낮다"
        )

    # ② 골격이 화면 밖으로 안 넘친다 — G-12.3-29 missing이 직접 경고한
    # 함정(서사 행에 픽셀 바닥만 줘서 전체가 넘치는 것)을 이 줄이 막는다.
    if measurement["scrollHeight"] > viewport_height + OVERFLOW_TOLERANCE_PX:
        reasons.append(
            f"문서 높이({measurement['scrollHeight']:.1f}px)가 뷰포트"
            f"({viewport_height}px)를 넘었다"
        )

    # ③ 사람이 실제로 누르는 것 전부(TOUCH_TARGETS, 12.3-16 Task 2)가
    # 「44px 이상이고 스크롤로 닿는다」다 — 높이만 재면 조상이 잘라 버려
    # 화면에 한 픽셀도 안 보이는 요소도 원래 크기 그대로를 보고한다.
    # 「손가락으로 누를 수 있다」를 확인하겠다는 단언이 「누를 수 없는
    # 것」을 통과시키던 구멍(G-12.3-28)을 여기서 닫는다 — 높이 단언과
    # 닿을 수 있음 단언(reachable())을 같은 목록 위에서 함께 돈다.
    # checkHeight가 거짓인 대상(`.composer` 자체)에는 44px 하한을 안
    # 건다 — 조작부 상자 자체가 아니라 그 안의 낱개 조작 요소가 눌리는
    # 것이다.
    for selector, human_name, check_height in TOUCH_TARGETS:
        entries = measurement["targets"][selector]
        for index, entry in enumerate(entries):
            which = f"{index + 1}번째 " if len(entries) > 1 else ""
            if entry["blockedBy"] is not None:
                reasons.append(
                    f"{human_name}({selector}) {which}아래끝 {entry['bottom']:.1f}px가 "
                    f"'{entry['blockedBy']}'에 잘려 화면({viewport_height}px) 밖이다 — "
                    "스크롤로도 못 닿는다"
                )
            if check_height and entry["height"] < TOUCH_TARGET_MIN_PX:
                reasons.append(
                    f"{human_name}({selector}) {which}높이가 {entry['height']:.1f}px로 "
                    f"{TOUCH_TARGET_MIN_PX}px보다 낮다"
                )

    # ④ 내 줄의 본문 배경이 남의 줄과 다르다(G-12.3-27). 배경색으로 잡는
    # 이유 — 이름표 글자색은 오늘도 이미 다르다(그것이 사장님이 본 「이름만
    # 노랗다」다). 갈려야 하는 것은 줄 전체이고, 그것을 픽셀 근처에서 잴 수
    # 있는 가장 단순한 신호가 줄의 배경이다.
    if measurement["name"] == MINE_LINE_COLOR_CHECK_SHAPE:
        if measurement["otherLineBg"] == measurement["mineLineBg"]:
            reasons.append(
                "내 줄과 남의 줄의 배경색이 같다"
                f"({measurement['mineLineBg']}) — 누가 말했는지 한눈에 안 갈린다"
            )

    return (len(reasons) == 0, reasons)


def main() -> int:
    missing_class_names = check_fixture_still_mirrors_source()
    if missing_class_names:
        print(
            "고정판이 흉내 내는 클래스 이름이 실제 소스에서 사라졌다 — 화면 "
            "마크업이 바뀌어 이 고정판은 더 이상 실제 화면을 안 비춘다. "
            "종료 코드 2.",
            file=sys.stderr,
        )
        for line in missing_class_names:
            print(f"  - {line}", file=sys.stderr)
        return 2

    if not CSS_PATH.is_file():
        print(f"{CSS_PATH}가 없다. 종료 코드 2.", file=sys.stderr)
        return 2

    chromium = find_chromium()
    if chromium is None:
        print(
            "헤드리스로 띄울 크로미움 계열 브라우저를 찾지 못했다"
            f"({', '.join(CHROMIUM_CANDIDATES)} 전부 없음). 종료 코드 2.",
            file=sys.stderr,
        )
        return 2

    css_uri = CSS_PATH.as_uri()

    with tempfile.TemporaryDirectory() as tmp_dir:
        host_path = Path(tmp_dir) / "host.html"
        host_path.write_text(build_host_html(css_uri), encoding="utf-8")

        dom = dump_dom(chromium, host_path.as_uri())
        if dom is None:
            print("크로미움 실행 자체가 실패했다. 종료 코드 2.", file=sys.stderr)
            return 2

        measurements = extract_measurements(dom)
        if measurements is None:
            return 2

    any_failed = False
    for measurement in measurements:
        passed, reasons = judge(measurement)
        status = "통과" if passed else "실패"
        print(
            f"{measurement['name']} · 상태 {measurement['statusHeight']:.1f}px · "
            f"서사 {measurement['storyHeight']:.1f}px · "
            f"대화 {measurement['chatHeight']:.1f}px · "
            f"문서높이 {measurement['scrollHeight']:.1f}px · {status}"
        )
        if not passed:
            any_failed = True
            for reason in reasons:
                print(f"  - {reason}", file=sys.stderr)

    return 1 if any_failed else 0


if __name__ == "__main__":
    sys.exit(main())
