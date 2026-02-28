/**
 * Short confirmations as centred dialogs (Ark Dialog, sheet recipe); a bottom sheet on phones.
 * Focus moves into the dialog on open and returns to the trigger on close.
 */
import { Dialog } from "@ark-ui/solid/dialog";
import type { JSX } from "solid-js";
import { Portal } from "solid-js/web";
import { CloseIcon } from "./Icons";
import { drawer, sheet } from "./recipes";

export function Sheet(props: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: JSX.Element;
  children: JSX.Element;
  role?: "dialog" | "alertdialog";
  initialFocus?: () => HTMLElement | null;
}) {
  const s = sheet();
  return (
    <Dialog.Root
      open={props.open}
      onOpenChange={(d) => props.onOpenChange(d.open)}
      role={props.role ?? "dialog"}
      initialFocusEl={props.initialFocus}
      lazyMount
      unmountOnExit
    >
      <Portal>
        <Dialog.Backdrop class={s.backdrop()} />
        <Dialog.Positioner class={s.positioner()}>
          <Dialog.Content class={s.content()}>
            <div class="flex items-start gap-3">
              <Dialog.Title class={`${s.title()} min-w-0 flex-1`}>{props.title}</Dialog.Title>
              <Dialog.CloseTrigger class="grid h-8 w-8 shrink-0 place-items-center rounded-full text-muted hover:bg-paper-2 hover:text-ink" aria-label="Close">
                <CloseIcon size={12} />
              </Dialog.CloseTrigger>
            </div>
            {props.description ? <Dialog.Description class={s.description()}>{props.description}</Dialog.Description> : null}
            <div class="mt-4">{props.children}</div>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
}

/** A right-hand drawer for detail (a ruling, a decision). A bottom sheet on phones. */

export function Drawer(props: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: JSX.Element;
  /** Accessible name when the title is not plain text. */
  label?: string;
  meta?: JSX.Element;
  width?: number;
  footer?: JSX.Element;
  children: JSX.Element;
}) {
  const d = drawer();
  return (
    <Dialog.Root open={props.open} onOpenChange={(e) => props.onOpenChange(e.open)} lazyMount unmountOnExit>
      <Portal>
        <Dialog.Backdrop class={d.backdrop()} />
        <Dialog.Positioner class={d.positioner()}>
          <Dialog.Content class={d.content()} style={{ "max-width": `${props.width ?? 560}px` }} aria-label={props.label}>
            <header class={d.head()}>
              <div class="min-w-0 flex-1">
                <Dialog.Title class={d.title()}>{props.title}</Dialog.Title>
                {props.meta ? <div class="mt-1 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[13px] text-muted">{props.meta}</div> : null}
              </div>
              <Dialog.CloseTrigger class="grid h-8 w-8 shrink-0 place-items-center rounded-full text-muted hover:bg-paper-2 hover:text-ink" aria-label="Close">
                <CloseIcon size={12} />
              </Dialog.CloseTrigger>
            </header>
            <div class={d.body()}>{props.children}</div>
            {props.footer ? <footer class={d.foot()}>{props.footer}</footer> : null}
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
}
