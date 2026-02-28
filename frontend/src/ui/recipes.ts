/**
 * Slot recipes for Ark UI parts, written with tailwind-variants on the @theme tokens (DESIGN.md §8).
 * Ark exposes data-scope / data-part / data-state, so states are styled here without extra script.
 */
import { tv } from "tailwind-variants";

export const button = tv({
  base: "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-btn)] border font-[600] no-underline transition-colors disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer select-none",
  variants: {
    tone: {
      ink: "border-ink bg-ink text-card hover:bg-ink-2 hover:border-ink-2",
      outline: "border-rule-2 bg-card text-ink hover:bg-paper-2",
      ghost: "border-transparent bg-transparent text-ink-2 hover:bg-paper-2 hover:text-ink",
      quiet: "border-transparent bg-transparent text-ink-2 underline underline-offset-4 decoration-rule-2 hover:decoration-ink hover:text-ink",
      danger: "border-bad bg-card text-bad hover:bg-bad-soft",
    },
    size: {
      lg: "h-11 px-5 text-[15px]",
      md: "h-10 px-4 text-[14.5px]",
      sm: "h-9 px-3.5 text-[14px]",
      xs: "h-8 px-3 text-[13px]",
    },
  },
  compoundVariants: [{ tone: "quiet", class: "h-auto px-0" }],
  defaultVariants: { tone: "ink", size: "md" },
});

/** A card: the one object a screen opens on, and every group of rows. */
export const card = tv({
  base: "rounded-[var(--radius-card)] border border-rule bg-card shadow-[var(--shadow-card)]",
});

/** Floating layers (menus, popovers, hover cards, listboxes): a card with a soft shadow. */
export const floating = tv({
  base: "rounded-[var(--radius-box)] border border-rule bg-card text-ink shadow-[var(--shadow-float)] outline-none anim-pop",
});

/** Filter toggles (Ark ToggleGroup items). */
export const chip = tv({
  base: "inline-flex h-8 items-center gap-1.5 whitespace-nowrap rounded-full border border-rule bg-card px-3 text-[13.5px] font-[550] text-ink-2 cursor-pointer hover:border-rule-2 hover:text-ink data-[state=on]:border-ink data-[state=on]:bg-ink data-[state=on]:text-card",
});

/** Badges: a dot or icon plus a word (status is never colour alone). */
export const tag = tv({
  base: "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-[3px] text-[12.5px] font-[600] leading-[1.35]",
  variants: {
    tone: {
      ok: "bg-ok-soft text-ok",
      warn: "bg-warn-soft text-warn",
      bad: "bg-bad-soft text-bad",
      ink: "bg-paper-2 text-ink",
      muted: "bg-paper-2 text-muted",
      hi: "bg-hi-soft text-ink font-code",
    },
  },
  defaultVariants: { tone: "ink" },
});

export const field = tv({
  slots: {
    root: "flex flex-col gap-1.5",
    label: "text-[13px] font-[600] text-ink-2",
    input:
      "h-10 w-full rounded-[var(--radius-btn)] border border-rule-2 bg-card px-3 text-[15px] text-ink placeholder:text-muted focus:border-ink outline-none data-[invalid]:border-bad aria-[invalid=true]:border-bad",
    textarea:
      "min-h-[92px] w-full rounded-[var(--radius-btn)] border border-rule-2 bg-card px-3 py-2.5 text-[15px] leading-[1.5] text-ink placeholder:text-muted focus:border-ink outline-none aria-[invalid=true]:border-bad",
    help: "text-[12.5px] text-muted",
    error: "text-[13px] font-[600] text-bad",
  },
});

export const table = tv({
  slots: {
    frame: "w-full overflow-x-auto",
    root: "w-full border-collapse text-left",
    head: "border-b border-rule text-[12.5px] font-[600] text-muted",
    th: "px-4 py-2.5 align-bottom font-[600] whitespace-nowrap",
    row: "border-b border-rule align-middle last:border-b-0",
    td: "px-4 py-3",
  },
});

export const tabs = tv({
  slots: {
    list: "relative flex items-end gap-5 overflow-x-auto no-scrollbar border-b border-rule",
    trigger:
      "relative inline-flex items-center gap-1.5 whitespace-nowrap pb-2.5 pt-1 text-[14.5px] font-[550] text-muted no-underline cursor-pointer hover:text-ink data-[selected]:text-ink aria-[current=page]:text-ink",
    count: "rounded-full bg-paper-2 px-1.5 text-[11.5px] font-[600] text-ink-2",
    indicator: "absolute -bottom-px h-[2px] rounded-full bg-ink transition-[left,width] duration-200",
  },
});

export const segment = tv({
  slots: {
    root: "relative inline-flex rounded-[var(--radius-btn)] bg-paper-2 p-[3px]",
    item: "relative z-[1] cursor-pointer rounded-[6px] px-3 py-1 text-[13.5px] font-[550] text-ink-2 data-[state=checked]:text-ink data-[state=checked]:font-[600] data-[focus-visible]:outline data-[focus-visible]:outline-2 data-[focus-visible]:outline-ink",
    indicator:
      "absolute z-0 rounded-[6px] bg-card shadow-[var(--shadow-card)] left-[var(--left)] top-[var(--top)] w-[var(--width)] h-[var(--height)] transition-[left,width] duration-200",
  },
});

export const radioCard = tv({
  slots: {
    root: "flex flex-col gap-1.5",
    item: "flex cursor-pointer items-center gap-2.5 rounded-[var(--radius-btn)] border border-rule bg-card px-3 py-2 text-[14.5px] hover:border-rule-2 data-[state=checked]:border-ink data-[state=checked]:font-[600]",
    control:
      "grid h-4 w-4 shrink-0 place-items-center rounded-full border-[1.5px] border-rule-2 data-[state=checked]:border-ink data-[state=checked]:after:block data-[state=checked]:after:h-2 data-[state=checked]:after:w-2 data-[state=checked]:after:rounded-full data-[state=checked]:after:bg-ink",
  },
});

export const checkbox = tv({
  slots: {
    root: "inline-flex cursor-pointer items-center gap-2.5 text-[14.5px]",
    control:
      "grid h-[18px] w-[18px] shrink-0 place-items-center rounded-[5px] border-[1.5px] border-rule-2 bg-card text-[12px] data-[state=checked]:border-ink data-[state=checked]:bg-ink data-[state=checked]:text-card",
  },
});

/** Centred dialogs for short confirmations (send for review, ask, invite, sign). */
export const sheet = tv({
  slots: {
    backdrop: "backdrop fixed inset-0 z-40 bg-ink/20 dark:bg-black/60",
    positioner: "fixed inset-0 z-50 flex items-start justify-center overflow-y-auto px-4 pt-[12vh] max-sm:items-end max-sm:px-0 max-sm:pt-0",
    content:
      "anim-pop w-full max-w-[520px] rounded-[var(--radius-card)] border border-rule bg-card p-6 text-ink shadow-[var(--shadow-float)] outline-none max-sm:rounded-b-none max-sm:p-5",
    title: "text-[19px] font-[600] tracking-[-0.01em]",
    description: "mt-1 text-[14.5px] text-muted",
  },
});

/** Right-hand drawers for detail (a ruling, a decision); a bottom sheet on phones. */
export const drawer = tv({
  slots: {
    backdrop: "backdrop fixed inset-0 z-40 bg-ink/15 dark:bg-black/55",
    positioner: "fixed inset-y-0 right-0 z-50 flex w-full justify-end max-sm:inset-x-0 max-sm:top-auto",
    content:
      "drawer-panel flex h-dvh w-full flex-col border-l border-rule bg-card text-ink shadow-[var(--shadow-float)] outline-none max-sm:h-[92dvh] max-sm:rounded-t-[16px] max-sm:border-l-0",
    head: "flex items-start gap-3 border-b border-rule px-6 py-4 max-sm:px-4",
    title: "min-w-0 flex-1 text-[18px] font-[600] tracking-[-0.01em]",
    body: "min-h-0 flex-1 overflow-y-auto px-6 py-5 max-sm:px-4",
    foot: "flex flex-wrap items-center gap-2 border-t border-rule bg-card px-6 py-3.5 max-sm:px-4",
  },
});

export const pin = tv({
  slots: {
    root: "flex flex-nowrap items-center gap-[3px]",
    cell: "h-[40px] w-[30px] shrink-0 rounded-[6px] border border-rule-2 bg-card text-center font-code text-[18px] font-[500] text-ink outline-none data-[changed=true]:border-ink data-[changed=true]:bg-hi-soft focus:border-ink focus:ring-2 focus:ring-ink/15 max-sm:h-[34px] max-sm:w-[24px] max-sm:text-[15px]",
    dot: "font-code text-[16px] text-muted max-sm:text-[13px]",
  },
});
