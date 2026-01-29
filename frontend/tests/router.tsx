import { MemoryRouter, Route, createMemoryHistory } from "@solidjs/router";
import type { JSX } from "solid-js";

/** Mount a component inside a memory router built from the app's own copy of @solidjs/router. */
export function inRouter(view: () => JSX.Element, path = "/") {
  const history = createMemoryHistory();
  history.set({ value: path });
  return () => (
    <MemoryRouter history={history}>
      <Route path="*" component={view} />
    </MemoryRouter>
  );
}
