/**
 * Dialogs are sheets that drop from the query strip, never centred modals (Ark Dialog, sheet recipe).
 * Focus moves into the sheet on open and returns to the trigger on close.
 */
import { Dialog } from "@ark-ui/solid/dialog";
import type { JSX } from "solid-js";
import { Portal } from "solid-js/web";
import { sheet } from "./recipes";

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
            <Dialog.Title class={s.title()}>{props.title}</Dialog.Title>
            {props.description ? <Dialog.Description class={s.description()}>{props.description}</Dialog.Description> : null}
            <div class="mt-4">{props.children}</div>
          </Dialog.Content>
        </Dialog.Positioner>
      </Portal>
    </Dialog.Root>
  );
}
