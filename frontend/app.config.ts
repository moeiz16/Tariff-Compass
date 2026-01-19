import { defineConfig } from "@solidjs/start/config";
import tailwindcss from "@tailwindcss/vite";

// SolidStart 1.5 on Vinxi 0.5 / Vite 6 (docs/adr/0001). The app renders in the browser (ssr: false): every screen
// reads the signed-in session and the demo clock from the API, so there is nothing useful to render on the server.
// The API is reached through the same-origin catch-all route in src/routes/api/[...path].ts, so cookies and CSRF
// work without CORS. VITE_TC_MOCK=1 swaps the API for in-browser fixtures that follow docs/API_CONTRACT.md.
export default defineConfig({
  ssr: false,
  server: { preset: "node-server" },
  vite: { plugins: [tailwindcss()] },
});
