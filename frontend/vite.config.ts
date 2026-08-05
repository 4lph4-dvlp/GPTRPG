import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/**
 * `gptrpg.web.app`이 `frontend/dist`를 그대로 정적 마운트하므로 outDir 기본값을
 * 바꾸지 않는다. `/api`는 서버가 쥐고 있으니 개발 서버에서만 8000으로 넘긴다 —
 * 빌드 산출물은 같은 오리진에서 서빙되어 프록시가 필요 없다.
 */
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
