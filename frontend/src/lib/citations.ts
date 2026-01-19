/**
 * Inline citation drawers: which drawers are open, and keyboard movement between chips.
 * Several drawers can be open at once; each opens under the paragraph that cites it.
 */
import { createSignal } from "solid-js";

export function createCitationState(initial: number[] = []) {
  const [open, setOpen] = createSignal<number[]>([...initial]);
  return {
    open,
    isOpen: (n: number) => open().includes(n),
    toggle: (n: number) => setOpen((o) => (o.includes(n) ? o.filter((x) => x !== n) : [...o, n].sort((a, b) => a - b))),
    show: (n: number) => setOpen((o) => (o.includes(n) ? o : [...o, n].sort((a, b) => a - b))),
    close: (n: number) => setOpen((o) => o.filter((x) => x !== n)),
    closeAll: () => setOpen([]),
  };
}
export type CitationState = ReturnType<typeof createCitationState>;

/** `[` and `]` move focus between citation chips in reading order. */
export function moveBetweenChips(e: KeyboardEvent, root: ParentNode = document): boolean {
  if (e.key !== "[" && e.key !== "]") return false;
  const target = e.target as HTMLElement | null;
  if (target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable)) return false;
  const chips = Array.from(root.querySelectorAll<HTMLElement>("[data-cite-chip]"));
  if (!chips.length) return false;
  const at = chips.indexOf(document.activeElement as HTMLElement);
  const next = e.key === "]" ? (at < 0 ? 0 : Math.min(chips.length - 1, at + 1)) : at < 0 ? chips.length - 1 : Math.max(0, at - 1);
  chips[next]?.focus();
  e.preventDefault();
  return true;
}
