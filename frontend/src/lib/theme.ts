/** Light is the default ("paper and ink"); dark is "night reading". The choice is remembered per browser. */
import { createSignal } from "solid-js";

export type Theme = "light" | "dark";
const KEY = "tc-theme";

function initial(): Theme {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* storage can be unavailable (private windows); the default still works */
  }
  return "light";
}

const [theme, setThemeSignal] = createSignal<Theme>(typeof document === "undefined" ? "light" : initial());
export { theme };

export function applyTheme(t: Theme = theme()): void {
  if (typeof document !== "undefined") document.documentElement.dataset.theme = t;
}

export function setTheme(t: Theme): void {
  setThemeSignal(t);
  applyTheme(t);
  try {
    localStorage.setItem(KEY, t);
  } catch {
    /* ignore */
  }
}

export function toggleTheme(): void {
  setTheme(theme() === "light" ? "dark" : "light");
}
