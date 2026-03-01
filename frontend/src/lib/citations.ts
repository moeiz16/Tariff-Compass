/**
 * Citations open in the ruling drawer: one ruling at a time, from a numbered chip or a row in the Rulings layer.
 * `[` and `]` move focus between the chips in reading order.
 */
import { createSignal } from "solid-js";

export function createCitationState(initial: number | null = null) {
  const [open, setOpen] = createSignal<number | null>(initial);
  return {
    open,
    isOpen: (n: number) => open() === n,
    show: (n: number) => setOpen(n),
    toggle: (n: number) => setOpen((o) => (o === n ? null : n)),
    close: () => setOpen(null),
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
