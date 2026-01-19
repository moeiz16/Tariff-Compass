/** Tooltips: ink fill, paper text (GRI explanations, keyboard hints). */
import { Tooltip } from "@ark-ui/solid/tooltip";
import type { JSX } from "solid-js";
import { Portal } from "solid-js/web";

export function Tip(props: { label: string; children: JSX.Element; placement?: "top" | "bottom" | "left" | "right" }) {
  return (
    <Tooltip.Root openDelay={250} closeDelay={80} positioning={{ placement: props.placement ?? "top" }}>
      <Tooltip.Trigger
        asChild={(p) => (
          <span {...p()} tabIndex={0} class="inline-flex">
            {props.children}
          </span>
        )}
      />
      <Portal>
        <Tooltip.Positioner>
          <Tooltip.Content class="z-50 max-w-[300px] rounded-[var(--radius-btn)] bg-ink px-2.5 py-1.5 text-[13px] leading-snug text-paper">
            {props.label}
          </Tooltip.Content>
        </Tooltip.Positioner>
      </Portal>
    </Tooltip.Root>
  );
}
