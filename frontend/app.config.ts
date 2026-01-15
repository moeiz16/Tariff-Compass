import { defineConfig } from "@solidjs/start/config";
import tailwindcss from "@tailwindcss/vite";

// SolidStart 1.5 on Vinxi 0.5 / Vite 6 (docs/adr/0001). The API is reached through the same-origin
// catch-all route in src/routes/api/[...path].ts, so cookies and CSRF work without CORS.
export default defineConfig({
  server: { preset: "node-server" },
  vite: { plugins: [tailwindcss()] },
});
