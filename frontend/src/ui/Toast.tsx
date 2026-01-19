/** Saved / corrected / exported notices: small mono slips at the bottom left (Ark Toast). */
import { Toast, Toaster, createToaster } from "@ark-ui/solid/toast";

export const toaster = createToaster({ placement: "bottom-start", overlap: false, gap: 8, duration: 3200, max: 4 });

export function notify(title: string, description?: string, type: "success" | "error" | "info" = "success") {
  toaster.create({ title, description, type });
}

export function AppToaster() {
  return (
    <Toaster toaster={toaster} aria-label="Notices">
      {(t) => (
        <Toast.Root
          class="min-w-[260px] max-w-[min(440px,calc(100vw-32px))] rounded-[var(--radius-btn)] border-[1.5px] border-ink bg-paper px-3.5 py-2.5 font-code text-[13px] text-ink shadow-[var(--shadow-hard)] data-[state=open]:animate-[tc-slip_240ms_var(--ease-dock)_both] data-[type=error]:border-bad translate-x-[var(--x)] translate-y-[var(--y)] scale-[var(--scale)] z-[var(--z-index)] h-[var(--height)] opacity-[var(--opacity)] will-change-[translate,opacity,scale] transition-[translate,scale,opacity,height] duration-300"
        >
          <div class="flex items-start gap-3">
            <div class="min-w-0 flex-1">
              <Toast.Title class="font-[650]">{t().title}</Toast.Title>
              <Toast.Description class="text-muted">{t().description}</Toast.Description>
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
