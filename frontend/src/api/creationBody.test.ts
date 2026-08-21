/**
 * 만들기 POST 본문에 브라우저 식별자가 실제로 실리는지 확인한다.
 *
 * 왜 이 시험이 있나: `fixPartySize`가 `browser_id`를 빼먹은 채로 판 12.3을
 * 통과했다. 뒤쪽 시험 1369개가 전부 초록이었는데도 못 잡았다 — 뒤쪽 시험은
 * HTTP 경로를 올바른 식별자로 직접 부르기 때문에, 화면이 필수 값을
 * 빠뜨리는 것은 뒤쪽에서 보이지 않는다. 서버는 값이 없으면 빈 문자열로
 * 채우고, 화면이 뜨는 순간 방장이 잡히므로 방장 본인도 403으로 막혔다.
 *
 * `fetch`를 대역으로 갈아 끼워 실제로 나가는 본문을 본다. RTL 없음
 * (`browserIdentity.test.ts`와 같은 관례).
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { claimCreationHost, fixPartySize } from "./client.ts";

/** 마지막으로 나간 요청 본문 — 각 시험이 여기를 본다. */
let lastBody: Record<string, unknown> | null = null;

beforeEach(() => {
  lastBody = null;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_url: string, init?: RequestInit) => {
      lastBody = JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>;
      return new Response(JSON.stringify({ seq: 1, you_are_host: true }), {
        status: 200,
        headers: { "content-type": "application/json" },
      });
    }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("만들기 POST 본문", () => {
  it("인원 확정이 브라우저 식별자를 싣는다 — 빠지면 방장 본인이 403을 맞는다", async () => {
    await fixPartySize("s1", 3, "dungeonworld-like", "browser-abc");

    expect(lastBody).not.toBeNull();
    expect(lastBody?.browser_id).toBe("browser-abc");
    expect(lastBody?.player_character_count).toBe(3);
    expect(lastBody?.rulebook_id).toBe("dungeonworld-like");
  });

  it("방장 잡기도 같은 식별자를 싣는다 — 두 호출이 같은 사람으로 보여야 관문이 통과한다", async () => {
    await claimCreationHost("s1", "browser-abc", "pc-browser-");

    expect(lastBody?.browser_id).toBe("browser-abc");
  });

  it("방장 잡기(재실 신호)가 캐릭터 식별자도 싣는다 — 빠지면 첫 지목이 영원히 안 일어난다(12.3-06)." +
    " 서버의 ClaimHostRequest.character_id는 기본값이 있는 관대한 칸이라 빠져도 조용히 통과하므로," +
    " 이 시험이 화면이 실제로 이 값을 보내는지 확인하는 유일한 가드다", async () => {
    await claimCreationHost("s1", "browser-abc", "pc-browser-");

    expect(lastBody?.browser_id).toBe("browser-abc");
    expect(lastBody?.character_id).toBe("pc-browser-");
  });
});
