/** Saved / corrected / exported notices: small cards at the bottom right (Ark Toast). */
import { Toast, Toaster, createToaster } from "@ark-ui/solid/toast";
import { OkIcon, WarnIcon } from "./Icons";

export const toaster = createToaster({ placement: "bottom-end", overlap: false, gap: 8, duration: 3200, max: 4 });

export function notify(title: string, description?: string, type: "success" | "error" | "info" = "success") {
  toaster.create({ title, description, type });
}

export function AppToaster() {
  return (
    <Toaster toaster={toaster} aria-label="Notices">
      {(t) => (
        <Toast.Root class="min-w-[280px] max-w-[min(420px,calc(100vw-32px))] rounded-[var(--radius-box)] border border-rule bg-card px-4 py-3 text-[14px] text-ink shadow-[var(--shadow-float)] translate-x-[var(--x)] translate-y-[var(--y)] scale-[var(--scale)] z-[var(--z-index)] h-[var(--height)] opacity-[var(--opacity)] will-change-[translate,opacity,scale] transition-[translate,scale,opacity,height] duration-300">
          <div class="flex items-start gap-2.5">
            {t().type === "error" ? <WarnIcon size={16} class="mt-0.5 shrink-0 text-bad" /> : <OkIcon size={16} class="mt-0.5 shrink-0 text-ok" />}
            <div class="min-w-0 flex-1">
              <Toast.Title class="font-[600]">{t().title}</Toast.Title>
              <Toast.Description class="text-[13px] text-muted">{t().description}</Toast.Description>
            </div>
            <Toast.CloseTrigger class="text-muted hover:text-ink" aria-label="Dismiss">
              ×
            </Toast.CloseTrigger>
          </div>
        </Toast.Root>
      )}
    </Toaster>
  );
}
