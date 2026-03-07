/**
 * Correct one digit: the proposed code in cells, and the broker's code in a 10-cell Ark PinInput directly under it,
 * digit-aligned. Changed cells are marked; the proposed digits they replace are struck in red.
 */
import { PinInput } from "@ark-ui/solid/pin-input";
import { For, Show } from "solid-js";
import { digitsOf, redline } from "~/lib/format";
import { pin } from "~/ui/recipes";

const GROUP_END = new Set([3, 5, 7]);
const INDEXES = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];

export function CodePins(props: { proposed: string; value: string[]; onChange: (v: string[]) => void; invalid?: boolean; describedBy?: string; ref?: (el: HTMLInputElement) => void }) {
  const p = pin();
  const cells = () => redline(props.proposed, props.value);
  return (
    <div class="space-y-2">
      <div class="flex items-center gap-3 max-sm:flex-col max-sm:items-start max-sm:gap-1">
        <span class="w-[72px] shrink-0 text-[12.5px] font-[550] text-muted max-sm:w-auto">Proposed</span>
        <div class={p.root()} aria-label={`Proposed code ${props.proposed}`} role="img">
          <For each={cells()}>
            {(c) => (
              <>
                <span
                  class="grid h-[40px] w-[30px] shrink-0 place-items-center rounded-[6px] bg-paper-2 font-code text-[18px] text-ink-2 max-sm:h-[34px] max-sm:w-[24px] max-sm:text-[15px]"
                  classList={{ "strike-bad": c.changed }}
                  aria-hidden="true"
                >
                  {c.proposed}
                </span>
                <Show when={GROUP_END.has(c.index)}>
                  <span class={p.dot()} aria-hidden="true">
                    .
                  </span>
                </Show>
              </>
            )}
          </For>
        </div>
      </div>
      <PinInput.Root
        count={10}
        type="numeric"
        otp={false}
        placeholder=""
        value={props.value}
        // Only real changes: echoing the same value back makes the pin input refocus its cell and hold the focus.
        onValueChange={(d) => d.value.join("|") !== props.value.join("|") && props.onChange(d.value)}
        invalid={props.invalid}
        class="flex items-center gap-3 max-sm:flex-col max-sm:items-start max-sm:gap-1"
      >
        <PinInput.Label class="w-[72px] shrink-0 text-[12.5px] font-[550] text-muted max-sm:w-auto">Your code</PinInput.Label>
        <PinInput.Control
          class={p.root()}
          aria-describedby={props.describedBy}
          onPaste={(e: ClipboardEvent) => {
            const text = e.clipboardData?.getData("text") ?? "";
            const digits = digitsOf(text);
            if (digits.length >= 4) {
              e.preventDefault();
              props.onChange(digits.slice(0, 10).padEnd(10, " ").split("").map((c) => c.trim()));
            }
          }}
        >
          {/* Stable cells by index: re-creating them on each change would drop the focus. */}
          <For each={INDEXES}>
            {(i) => (
              <>
                <PinInput.Input
                  index={i}
                  ref={i === 0 ? props.ref : undefined}
                  class={p.cell()}
                  data-changed={cells()[i]?.changed ? "true" : "false"}
                  aria-label={`Digit ${i + 1} of your code`}
                />
                <Show when={GROUP_END.has(i)}>
                  <span class={p.dot()} aria-hidden="true">
                    .
                  </span>
                </Show>
              </>
            )}
          </For>
        </PinInput.Control>
        <PinInput.HiddenInput />
      </PinInput.Root>
    </div>
  );
}
