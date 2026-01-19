// @refresh reload
import { createHandler, StartServer } from "@solidjs/start/server";

// The page shell. The theme is applied before first paint so night reading never flashes white.
const THEME = `try{var t=localStorage.getItem("tc-theme");if(t==="dark"||t==="light")document.documentElement.dataset.theme=t}catch(e){}`;

export default createHandler(() => (
  <StartServer
    document={({ assets, children, scripts }) => (
      <html lang="en-CA" data-theme="light">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <meta name="description" content="Tariff Compass: US and Canadian tariff codes with the customs rulings that back them and every duty they carry." />
          <meta name="theme-color" content="#ffffff" />
          <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
          {/* eslint-disable-next-line solid/no-innerhtml -- a fixed, build-time string with no user input */}
          <script innerHTML={THEME} />
          {assets}
        </head>
        <body>
          <div id="app">{children}</div>
          {scripts}
        </body>
      </html>
    )}
  />
));
