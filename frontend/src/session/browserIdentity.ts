/**
 * 브라우저 신원 — 쿠키가 구워지기 전(만들기 완성 전)에 이 브라우저를
 * 가리키는 두 값을 `localStorage`에 안정적으로 둔다(Phase 12.3-04,
 * 12.3-CONTEXT.md §Claude's Discretion 「쿠키가 구워지기 전의 신원」).
 *
 * 서명 쿠키(`gptrpg_character`, `src/gptrpg/web/cookie_auth.py`)는 만들기가
 * 완성된(`/creation/complete`) 뒤에야 생긴다 — 그 전까지는 이 모듈이 신원의
 * 유일한 출처다. **서버는 이 값을 신뢰 근거로 쓰지 않는다**(T-12.3-01) —
 * 화면 판단(「내 차례인가」 등)도 서버가 내려준 값과의 비교일 뿐이고,
 * 완성 시점의 위조 방지는 서버의 `_prepare_create_character`(브라우저
 * 연속성 대조)가 이미 한다. 이 모듈이 새 권한 판단을 만들지 않는다.
 * **이 값은 비밀값도 자격증명도 아니다** — 없는 암호학적 보증을 흉내
 * 내려고 안전한 맥락에서만 있는 API를 붙잡지 않는다(아래 `newOpaqueId`).
 *
 * **안전한 맥락(secure context)에 기대지 않는다(Phase 12.3-11).** README가
 * 참가자에게 나눠 주는 링크는 평문 http + 이 기계의 LAN·tailscale
 * 주소이고, 이 조건은 브라우저가 「안전한 맥락」으로 안 쳐 준다 — 즉
 * 이것이 예외가 아니라 **정상 운용 조건**이다. 이 모듈이 부르는 브라우저
 * API(`crypto.getRandomValues`)는 그 조건에서도 있다는 것을 실측했다.
 *
 * **표시 이름은 절대 여기서 다루지 않는다.** `getCreationCharacterId`가
 * 돌려주는 값은 사람에게 보이지 않는 내부 식별자다 — 표시 이름의 유일한
 * 출처는 룰북의 `provides_display_name` 항목이다(예:
 * `dungeonworld_like.py`의 "name" 단계). 사람에게 이름을 두 번 묻지 않는다.
 */

const BROWSER_ID_PREFIX = "gptrpg.browser.";
const CHARACTER_ID_PREFIX = "gptrpg.character.";

/**
 * `localStorage`가 없거나(사생활 보호 모드 등) 던지면 이 지도로 떨어진다 —
 * 모듈이 다시 로드되지 않는 한(=탭을 새로고침해도) 이 탭 안에서는 안정적인
 * 값을 계속 돌려준다. **탭을 닫으면 자기 캐릭터로 못 돌아온다**는 한계는
 * `COPY.characterIdentityLimit`(Phase 8 D-01)가 이미 같은 자리에서 말하고
 * 있다 — 화면이 아예 안 열리는 것이 그 한계보다 더 나쁘다.
 */
const memoryFallback = new Map<string, string>();

function readValue(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeValue(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // 사생활 보호 모드 등 — 조용히 넘어간다. memoryFallback이 이 탭 안의
    // 안정성을 대신 지킨다.
  }
}

function getOrCreate(key: string, create: () => string): string {
  const stored = readValue(key);
  if (stored !== null) {
    return stored;
  }
  const cached = memoryFallback.get(key);
  if (cached !== undefined) {
    return cached;
  }
  const value = create();
  memoryFallback.set(key, value);
  writeValue(key, value);
  return value;
}

/**
 * 새 불투명 식별자를 만든다 — 32글자 16진수 문자열(16바이트).
 *
 * **이 값은 비밀값도 자격증명도 아니다.** 서버는 이 값을 신뢰 근거로
 * 쓰지 않고(T-12.3-01), 필요한 성질은 「한 세션의 브라우저 몇 개 사이에서
 * 안 겹친다」뿐이다.
 *
 * **`crypto.randomUUID()`가 아니라 `crypto.getRandomValues`를 부르는
 * 이유(Phase 12.3-11).** `randomUUID`는 「안전한 맥락(secure context)」
 * 에서만 있다 — 주소가 HTTPS이거나 호스트가 `localhost`/`127.0.0.1`일
 * 때뿐이다. 이 저장소의 README가 참가자에게 나눠 주라고 지시하는 링크는
 * 평문 http + 이 기계의 LAN·tailscale 주소이고, 그 형태는 안전한 맥락이
 * **아니다** — 즉 이 조건은 예외가 아니라 **정상 운용 조건**이다.
 * `crypto.getRandomValues`는 실제 크로미움(151)으로 그 주소에서 직접
 * 측정해 있다는 것을 확인했다 — 이 API는 안전한 맥락 제한을 안 받는다.
 * 그래서 「없으면 다른 걸 쓴다」는 갈래를 두지 않고 호출 자체를 이것으로
 * 갈아 끼운다 — 코드 경로가 하나로 줄고, 특정 환경에서만 도는 줄이 새로
 * 안 생긴다.
 *
 * 값의 모양(32글자 16진수)은 `MAX_ID_LEN`(64, `../config.ts`)과
 * `getCreationCharacterId`의 `pc-` + 여덟 글자 규칙을 그대로 지킨다.
 * 이 값은 UUID 규격 문자열이 아니다 — 이 저장소에 이 값을 UUID로 파싱하는
 * 코드는 없다.
 */
function newOpaqueId(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let id = "";
  for (const byte of bytes) {
    id += byte.toString(16).padStart(2, "0");
  }
  return id;
}

/**
 * 이 브라우저의 신원 — **세션마다 따로 둔다.** 한 브라우저가 두 세션에서
 * 같은 식별자를 쓰면 한쪽 세션의 값으로 다른 쪽을 추측할 수 있다
 * (T-12.3-16) — 그래서 저장 키를 세션별로 가른다. `newOpaqueId()`가 돌려주는
 * 32글자 16진수 문자열은 항상 `MAX_ID_LEN`(64) 이하다.
 */
export function getBrowserId(sessionId: string): string {
  return getOrCreate(`${BROWSER_ID_PREFIX}${sessionId}`, newOpaqueId);
}

/**
 * 이 브라우저가 만들고 있는 캐릭터의 내부 식별자 — **사람에게 보이지
 * 않는다.** 표시 이름은 룰북의 `provides_display_name` 항목(`name` 단계
 * 등)이 정하는 값 하나뿐이다 — 이 식별자를 이름으로 보여주거나 이름을
 * 다시 묻지 않는다. `pc-` + `getBrowserId`의 앞 여덟 글자이므로 항상
 * `MAX_ID_LEN`(64) 이하다.
 */
export function getCreationCharacterId(sessionId: string): string {
  return getOrCreate(
    `${CHARACTER_ID_PREFIX}${sessionId}`,
    () => `pc-${getBrowserId(sessionId).slice(0, 8)}`,
  );
}
