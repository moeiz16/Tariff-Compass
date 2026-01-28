/**
 * Park UI-style slot recipes for Ark UI parts, written with tailwind-variants on the @theme tokens.
 * Ark exposes data-scope / data-part / data-state, so states are styled here without extra script.
 */
import { tv } from "tailwind-variants";

export const button = tv({
  base: "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-[var(--radius-btn)] border-[1.5px] border-ink font-[650] no-underline transition-colors disabled:cursor-not-allowed disabled:opacity-50 cursor-pointer select-none",
  variants: {
    tone: {
      ink: "bg-ink text-paper hover:bg-ink-2",
      ghost: "bg-transparent text-ink hover:bg-paper-2",
      quiet: "border-transparent bg-transparent text-ink-2 underline underline-offset-4 decoration-rule hover:decoration-ink px-0",
      danger: "border-bad bg-transparent text-bad hover:bg-paper-2",
    },
    size: {
      lg: "h-[46px] px-5 text-[15.5px]",
      md: "h-10 px-4 text-[14.5px]",
      sm: "h-9 px-3.5 text-[14px]",
      xs: "h-[30px] px-2.5 text-[13px] border",
    },
  },
  compoundVariants: [{ tone: "quiet", class: "h-auto px-0" }],
  defaultVariants: { tone: "ink", size: "md" },
});

/** Floating layers share one recipe: 1.5 px ink rule and a hard 4 px ink offset, no blur. */
export const floating = tv({
  base: "rounded-[var(--radius-box)] border-[1.5px] border-ink bg-paper text-ink shadow-[var(--shadow-hard)] outline-none",
});

export const chip = tv({
  base: "inline-flex h-[30px] items-center gap-1.5 whitespace-nowrap rounded-[var(--radius-btn)] border border-rule bg-paper px-[11px] text-[13.5px] font-[550] text-ink-2 cursor-pointer data-[state=on]:border-ink data-[state=on]:bg-paper-2 data-[state=on]:font-[650] data-[state=on]:text-ink hover:border-ink",
});

/** Kind / verdict tags: icon + word, bordered in the state's colour (status is never colour alone). */
export const tag = tv({
  base: "inline-flex items-center gap-1.5 whitespace-nowrap rounded-[var(--radius-btn)] border px-2 py-[3px] text-[13px] font-[650] leading-none",
  variants: {
    tone: {
      ok: "border-ok text-ok",
      warn: "border-warn text-warn",
      bad: "border-bad text-bad",
      ink: "border-ink text-ink",
      muted: "border-rule text-muted",
      hi: "border-transparent bg-hi text-hi-ink font-code text-[12.5px]",
    },
  },
  defaultVariants: { tone: "ink" },
});

export const field = tv({
  slots: {
    root: "flex flex-col gap-1.5",
    label: "text-[13px] font-[650] text-ink-2",
    input:
      "h-11 w-full rounded-[var(--radius-btn)] border-[1.5px] border-rule bg-paper px-3 text-[15.5px] text-ink placeholder:text-muted focus:border-ink outline-none data-[invalid]:border-bad",
    textarea:
      "min-h-[92px] w-full rounded-[var(--radius-box)] border-[1.5px] border-ink bg-paper px-3.5 py-2.5 text-[15.5px] leading-[1.5] text-ink placeholder:text-muted outline-none data-[invalid]:border-bad",
    help: "text-[12.5px] text-muted",
    error: "text-[13px] font-[600] text-bad",
  },
});

export const table = tv({
  slots: {
    frame: "w-full overflow-x-auto",
    root: "w-full border-collapse text-left",
    head: "border-b-[1.5px] border-ink text-[13px] font-[650] text-ink-2",
    th: "px-3 py-2.5 align-bottom font-[650] whitespace-nowrap",
    row: "border-b border-rule align-top",
    td: "px-3 py-3",
  },
});

export const tabs = tv({
  slots: {
    list: "relative flex items-end gap-1 overflow-x-auto no-scrollbar",
    trigger:
      "relative inline-flex items-baseline gap-1.5 whitespace-nowrap px-2.5 pb-3 pt-1.5 text-[16.5px] text-muted no-underline hover:text-ink data-[selected]:font-[700] data-[selected]:text-ink aria-[current=page]:font-[700] aria-[current=page]:text-ink",
    count: "font-code text-[12px] font-[600] text-ink-2",
    indicator: "absolute bottom-0 h-1 bg-hi transition-[left,width] duration-300",
  },
});

export const segment = tv({
  slots: {
    root: "relative inline-flex rounded-[var(--radius-btn)] border-[1.5px] border-ink bg-paper p-0 overflow-hidden",
    item: "relative z-[1] cursor-pointer px-3.5 py-1.5 text-[14.5px] font-[600] text-ink data-[state=checked]:text-paper border-l border-rule first:border-l-0 data-[focus-visible]:outline data-[focus-visible]:outline-3 data-[focus-visible]:outline-hi",
    indicator: "absolute z-0 bg-ink left-[var(--left)] top-[var(--top)] w-[var(--width)] h-[var(--height)] transition-[left,width] duration-200",
  },
});

export const radioCard = tv({
  slots: {
    root: "flex flex-col gap-2",
    item: "flex cursor-pointer items-center gap-2.5 rounded-[var(--radius-btn)] border border-rule bg-paper px-3 py-2 text-[14.5px] data-[state=checked]:border-ink data-[state=checked]:border-[1.5px] data-[state=checked]:font-[650]",
    control:
      "grid h-4 w-4 place-items-center rounded-full border-[1.5px] border-ink data-[state=checked]:after:block data-[state=checked]:after:h-2 data-[state=checked]:after:w-2 data-[state=checked]:after:rounded-full data-[state=checked]:after:bg-ink",
  },
});

export const checkbox = tv({
  slots: {
    root: "inline-flex cursor-pointer items-center gap-2.5 text-[15px]",
    control:
      "grid h-[18px] w-[18px] place-items-center rounded-[3px] border-[1.5px] border-ink bg-paper data-[state=checked]:bg-ink data-[state=checked]:text-paper",
  },
});

export const sheet = tv({
  slots: {
    backdrop: "fixed inset-0 z-40 bg-ink/10 dark:bg-black/40",
    positioner: "fixed inset-x-0 top-[72px] z-50 flex justify-center px-4 max-md:top-[56px]",
    content:
      "anim-sheet w-full max-w-[680px] rounded-[var(--radius-box)] border-[1.5px] border-ink bg-paper p-6 text-ink shadow-[var(--shadow-hard)] outline-none max-md:p-4",
    title: "text-[22px] font-[750] leading-tight tracking-[-0.01em]",
    description: "mt-2 text-[16px] text-ink-2",
  },
});

export const pin = tv({
  slots: {
    root: "flex flex-nowrap items-center gap-[3px]",
    cell: "h-[38px] w-[30px] shrink-0 rounded-[3px] border-[1.5px] border-ink bg-paper text-center font-code text-[19px] font-[600] text-ink outline-none data-[changed=true]:bg-hi data-[changed=true]:text-hi-ink focus:ring-[3px] focus:ring-hi max-sm:h-[32px] max-sm:w-[24px] max-sm:text-[15px]",
    dot: "font-code text-[18px] text-muted max-sm:text-[14px]",
  },
});
