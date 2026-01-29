import { fileURLToPath } from "node:url";
import solid from "vite-plugin-solid";
import { defineConfig } from "vitest/config";

// One copy of Solid and the router for components and @solidjs/testing-library alike: resolve the browser builds
// and let Vite transform every Solid library instead of loading some of them through Node.
export default defineConfig({
  plugins: [solid({ hot: false, dev: true })],
  resolve: {
    alias: { "~": fileURLToPath(new URL("./src", import.meta.url)) },
    conditions: ["development", "browser"],
  },
  test: {
    globals: true,
    environment: "node",
    include: ["tests/**/*.test.ts", "tests/**/*.test.tsx"],
    exclude: ["tests/router.tsx"],
    server: { deps: { inline: [/solid-js/, /@solidjs\//, /@ark-ui\//, /@zag-js\//] } },
  },
});
