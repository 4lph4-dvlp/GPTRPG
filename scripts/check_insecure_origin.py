#!/usr/bin/env python3
"""이 기계의 **루프백이 아닌** 주소로 캐릭터 만들기 화면이 실제로 뜨는지,
진짜 헤드리스 크로미움으로 열어 확인한다(Phase 12.3-11, 6차 검증 gap).

**왜 이 스크립트가 있는가.** README §실험 당일 실행 절차가 참가자 넷에게
나눠 주라고 지시하는 링크는 평문 http + 이 기계의 LAN·tailscale 주소
(`http://192.168.0.20:8000/?session=…` 꼴)다. 이 형태는 브라우저가 말하는
「안전한 맥락(secure context)」이 **아니다** — 안전한 맥락은 주소가
HTTPS이거나 호스트가 `localhost`/`127.0.0.1`일 때뿐이다. 안전한 맥락에서만
있는 브라우저 API(예: `crypto.randomUUID`)를 화면 코드가 부르면, 참가자가
실제로 여는 주소에서는 그 함수가 아예 없어 첫 렌더가 예외로 끊긴다.

**다섯 라운드의 코드 검증과 자동 시험이 왜 이 결함을 못 잡았는가.**
전부 `127.0.0.1`로만 화면을 열었다 — 유일하게 안전한 맥락이 성립하는
주소다. 그래서 이 실패 경로는 다섯 라운드 내내 한 번도 실행된 적이 없다.
이 스크립트는 그 공백을 메운다 — **루프백이 아닌 주소**로, **진짜
브라우저**를 헤드리스로 붙여, 자바스크립트가 다 돈 뒤의 DOM을 읽는다.

**종료 코드 세 개의 뜻 — `2`는 `0`이 아니다.**

- `0` — 통과. 루프백이 아닌 주소에서 화면이 실제로 그려졌다(`캐릭터 만들기`를
  찾았다).
- `1` — 실패. 화면이 안 그려졌다(`#app`이 비어 있거나 다른 내용이다).
- `2` — **확인 불가.** 크로미움이 없거나, 이 기계에 루프백이 아닌 IPv4
  주소가 없거나(또는 `--host`로 루프백 주소를 줬거나), 화면 빌드가
  실패했거나, 서버가 뜨지 않았다. **`2`를 `0`으로 접지 않는다** — 확인을
  못 한 상황이 통과로 보이는 것이 정확히 이번 결함이 여섯 라운드를 살아남은
  이유이기 때문이다. 루프백 주소(`127.0.0.1`)로는 이 확인이 원리적으로
  성립하지 않으므로, `--host 127.0.0.1`을 줘도 스스로 `2`로 거절한다.

새 꾸러미를 하나도 안 쓴다 — 표준 라이브러리와 이 기계에 이미 있는
크로미움(`/usr/bin/chromium`)만 부른다.

사용법:

    .venv/bin/python scripts/check_insecure_origin.py [--host <IP>] [--port <포트>] [--skip-build]
"""

from __future__ import annotations

import argparse
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PORT = 8973
STARTUP_TIMEOUT_S = 20
DOM_DUMP_TIMEOUT_S = 60
VIRTUAL_TIME_BUDGET_MS = 8000
# `frontend/src/labels.ts`의 COPY.creationTitle과 같은 문자열이어야 한다 —
# 갈리면 이 확인이 통과 기준을 잃는다.
CREATION_TITLE = "캐릭터 만들기"

CHROMIUM_CANDIDATES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")


def find_non_loopback_ipv4(explicit_host: str | None) -> str | None:
    """이 기계의 루프백이 아닌 IPv4 주소를 찾는다.

    `explicit_host`가 주어지면 그 값을 검사만 한다(찾지 않는다). 루프백
    주소(`127.`로 시작)면 `None`을 돌려줘 호출자가 종료 코드 2로 끝나게
    한다 — 루프백으로는 이 확인이 원리적으로 성립하지 않는다.
    """
    if explicit_host is not None:
        if explicit_host.startswith("127."):
            return None
        return explicit_host
    # 패킷을 실제로 안 보내는 관례적 방법 — UDP 소켓을 "연결"만 하고
    # 커널이 고를 발신 인터페이스의 주소를 읽는다.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("1.1.1.1", 1))
        addr = sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()
    if not addr or addr.startswith("127."):
        return None
    return addr


def find_chromium() -> str | None:
    for candidate in CHROMIUM_CANDIDATES:
        found = shutil.which(candidate)
        if found is not None:
            return found
    return None


def build_frontend() -> bool:
    """`npm run build`를 `frontend/`에서 돌린다.

    기본 동작이 「빌드한다」인 이유: `frontend/dist`는 소스와 따로 논다.
    고친 뒤 빌드를 잊으면 이 확인이 **옛 화면을 검사하고 통과해 버린다** —
    그 침묵이 이번 gap이 여섯 라운드를 살아남은 모양 그대로다.
    """
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=REPO_ROOT / "frontend",
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("빌드 실패:", file=sys.stderr)
        print(result.stdout, file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return False
    return True


def wait_for_server(host: str, port: int, timeout_s: float) -> bool:
    import time

    deadline = time.monotonic() + timeout_s
    url = f"http://{host}:{port}/"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:  # noqa: S310 - 로컬 서버
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            pass
        time.sleep(0.5)
    return False


def dump_dom(chromium: str, url: str) -> str | None:
    """`chromium --headless --dump-dom`으로 자바스크립트가 다 돈 뒤의 DOM을 읽는다.

    「HTML을 받았다」가 아니라 「화면이 그려졌다」를 보는 것이 이 확인의
    핵심이다 — `curl`이나 `urllib`으로 받은 원본 HTML은 빈 `#app`
    껍데기뿐이라 아무것도 증명하지 못한다.
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
                url,
            ],
            capture_output=True,
            text=True,
            timeout=DOM_DUMP_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        print(f"크로미움이 {url}을(를) 여는 데 실패했다:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return None
    return result.stdout


def extract_app_div(dom: str) -> str:
    """진단 출력용 — DOM에서 `<div id="app">…</div>` 부분만 잘라낸다."""
    start = dom.find('<div id="app"')
    if start == -1:
        return "(#app을 DOM에서 찾지 못했다)"
    # 대응하는 닫는 태그를 정확히 찾는 파서가 아니라, 사람이 읽을 진단
    # 출력이면 충분하므로 넉넉하게 잘라낸다.
    snippet = dom[start : start + 2000]
    end = snippet.find("</html>")
    if end != -1:
        snippet = snippet[:end]
    return snippet


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=None, help="검사할 루프백 아닌 IPv4 주소(생략하면 스스로 찾는다)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"서버 포트(기본 {DEFAULT_PORT})")
    parser.add_argument("--skip-build", action="store_true", help="화면 재빌드를 건너뛴다(기본값: 빌드한다)")
    args = parser.parse_args()

    host = find_non_loopback_ipv4(args.host)
    if host is None:
        if args.host is not None:
            print(
                f"'{args.host}'는 루프백 주소다 — 이 확인은 루프백으로는 원리적으로 "
                "성립하지 않는다(안전한 맥락이 항상 참이 되어 실패 경로가 실행되지 않는다). "
                "종료 코드 2.",
                file=sys.stderr,
            )
        else:
            print(
                "이 기계에는 루프백이 아닌 IPv4 주소가 없어 이 확인을 수행할 수 없다. "
                "종료 코드 2.",
                file=sys.stderr,
            )
        # 확인 불가를 통과(0)와 절대 안 섞는다 — 이 조항 하나가 다섯 라운드의
        # 침묵을 만든 원인이라 명시적으로 sys.exit(2)를 부른다.
        sys.exit(2)

    chromium = find_chromium()
    if chromium is None:
        print(
            "헤드리스로 띄울 크로미움 계열 브라우저를 찾지 못했다"
            f"({', '.join(CHROMIUM_CANDIDATES)} 전부 없음). "
            "설치하거나 PATH를 맞춘 뒤 다시 시도할 것. 종료 코드 2.",
            file=sys.stderr,
        )
        sys.exit(2)

    if not args.skip_build:
        if not build_frontend():
            print("화면 빌드에 실패해 이 확인을 계속할 수 없다. 종료 코드 2.", file=sys.stderr)
            sys.exit(2)

    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = str(Path(tmp_dir) / "check_insecure_origin.db")
        server_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "gptrpg.web.app:app",
                "--host",
                "0.0.0.0",  # noqa: S104 - README §A-5가 지시하는 실제 운용 형태와 같은 노출이다
                "--port",
                str(args.port),
            ],
            cwd=REPO_ROOT,
            env={**__import__("os").environ, "GPTRPG_DB": db_path},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            if not wait_for_server(host, args.port, STARTUP_TIMEOUT_S):
                print(
                    f"서버가 {STARTUP_TIMEOUT_S}초 안에 http://{host}:{args.port}/ 에서 "
                    "응답하지 않았다. 종료 코드 2.",
                    file=sys.stderr,
                )
                sys.exit(2)

            probe_url = f"http://{host}:{args.port}/?session=insecure-origin-probe"
            control_url = f"http://127.0.0.1:{args.port}/?session=insecure-origin-control"

            probe_dom = dump_dom(chromium, probe_url)
            control_dom = dump_dom(chromium, control_url)

            if probe_dom is None or control_dom is None:
                print("크로미움 실행 자체가 실패했다. 종료 코드 2.", file=sys.stderr)
                sys.exit(2)

            control_ok = CREATION_TITLE in control_dom
            probe_ok = CREATION_TITLE in probe_dom

            print(f"[대조군] http://127.0.0.1:{args.port}/ (루프백, 안전한 맥락) → "
                  f"{'통과 — ' + CREATION_TITLE + ' 찾음' if control_ok else '실패'}")
            print(f"[본 검사] http://{host}:{args.port}/ (루프백 아님, 참가자가 여는 형태) → "
                  f"{'통과 — ' + CREATION_TITLE + ' 찾음' if probe_ok else '실패'}")

            if not control_ok:
                # 루프백에서도 안 그려지면 이번 결함이 아니라 서버·빌드가
                # 통째로 망가진 것이다 — 다른 문구로 알려야 사람이 안 헤맨다.
                print(
                    "대조군(127.0.0.1)조차 실패했다 — 이것은 안전한 맥락 결함이 아니라 "
                    "서버나 빌드가 통째로 망가진 것이다. #app 내용:",
                    file=sys.stderr,
                )
                print(extract_app_div(control_dom), file=sys.stderr)
                return 1

            if probe_ok:
                print(f"통과 — {host}에서 '{CREATION_TITLE}'가 실제로 그려졌다.")
                return 0

            print(
                f"실패 — {host}(루프백 아님, 참가자 링크와 같은 형태)에서 화면이 "
                "그려지지 않았다. #app 내용:",
                file=sys.stderr,
            )
            print(extract_app_div(probe_dom), file=sys.stderr)
            return 1
        finally:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()
                server_proc.wait(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
