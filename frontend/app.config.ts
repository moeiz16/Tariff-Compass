import { defineConfig } from "@solidjs/start/config";
import tailwindcss from "@tailwindcss/vite";

// SolidStart 1.5 on Vinxi 0.5 / Vite 6 (docs/adr/0001). The app renders in the browser (ssr: false): every screen
// reads the signed-in session and the demo clock from the API, so there is nothing useful to render on the server.
// The API is reached through the same-origin catch-all route in src/routes/api/[...path].ts, so cookies and CSRF
// work without CORS. VITE_TC_MOCK=1 swaps the API for in-browser fixtures that follow docs/API_CONTRACT.md.

// Security headers on every page and asset the web server sends, the prerendered front page included. Scripts come
// only from this origin plus the page shell's two inline scripts (the theme and the asset manifest); styles may be
// inline because components set style attributes; the API is same-origin through /api, so nothing else connects.
// The API's own responses keep its stricter headers (the proxy passes them through).
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "frame-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const SECURITY_HEADERS = {
  "Content-Security-Policy": CSP,
  "X-Frame-Options": "DENY",
  "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "same-origin",
  "Cross-Origin-Opener-Policy": "same-origin",
  "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
};

export default defineConfig({
  ssr: false,
  server: { preset: "node-server", routeRules: { "/**": { headers: SECURITY_HEADERS } } },
  vite: { plugins: [tailwindcss()] },
});
