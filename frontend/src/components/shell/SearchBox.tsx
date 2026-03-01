/**
 * The classify box: text (Ark Combobox with past questions and samples as suggestions), Into and From (Ark Select),
 * and a spec sheet or photo (Ark FileUpload).
 */
import { Combobox, createListCollection } from "@ark-ui/solid/combobox";
import { FileUpload } from "@ark-ui/solid/file-upload";
import { Select } from "@ark-ui/solid/select";
import { For, Show, createEffect, createMemo, createSignal, on, untrack } from "solid-js";
import { Portal } from "solid-js/web";
import { answers } from "~/lib/endpoints";
import { plainProblem } from "~/lib/problem";
import type { Country, EvidenceOut, Labelled } from "~/lib/types";
import { ChevronIcon, CloseIcon, PaperclipIcon, SearchIcon } from "~/ui/Icons";
import { button, floating } from "~/ui/recipes";

export interface ClassifyOptions {
  into: Country[];
  madeIn: string;
  evidence: EvidenceOut[];
}

export const INTO_CHOICES = [
  { value: "US,CA", label: "US + Canada" },
  { value: "US", label: "US" },
  { value: "CA", label: "Canada" },
];
export const DEFAULT_ORIGINS: Labelled[] = [
  { key: "CN", label: "China" },
  { key: "VN", label: "Vietnam" },
  { key: "MX", label: "Mexico" },
  { key: "DE", label: "Germany" },
  { key: "IT", label: "Italy" },
];

interface Props {
  id: string;
  mode: "classify" | "search";
  label: string;
  placeholder: string;
  value?: string;
  size?: "hero" | "compact";
  suggestions?: string[];
  origins?: Labelled[];
  into?: Country[];
  madeIn?: string;
  allowFiles?: boolean;
  busy?: boolean;
  onSubmit: (text: string, opts: ClassifyOptions) => void;
}

export function SearchBox(props: Props) {
  const [text, setText] = createSignal(untrack(() => props.value) ?? "");
  const [into, setInto] = createSignal(untrack(() => props.into ?? ["US", "CA"]).join(","));
  const [madeIn, setMadeIn] = createSignal(untrack(() => props.madeIn) ?? "CN");
  // A new question in the URL (or a new answer) updates the box.
  createEffect(on(() => props.value, (v) => v !== undefined && setText(v), { defer: true }));
  createEffect(on(() => props.madeIn, (v) => v && setMadeIn(v), { defer: true }));
  const [evidence, setEvidence] = createSignal<EvidenceOut[]>([]);
  const [uploadError, setUploadError] = createSignal("");
  const [uploading, setUploading] = createSignal(false);
  const hero = () => props.size === "hero";

  const items = createMemo(() => {
    const t = text().trim().toLowerCase();
    const all = [...new Set(props.suggestions ?? [])];
    return (t ? all.filter((s) => s.toLowerCase().includes(t) && s.toLowerCase() !== t) : all).slice(0, 6);
  });
  const collection = createMemo(() => createListCollection({ items: items() }));
  const intoCollection = createListCollection({ items: INTO_CHOICES });
  const originCollection = createMemo(() =>
    createListCollection({ items: (props.origins?.length ? props.origins : DEFAULT_ORIGINS).map((o) => ({ value: o.key, label: o.label })) }),
  );

  const submit = (value = text()) => {
    const v = value.trim();
    if (!v && props.mode === "classify" && !evidence().length) return;
    props.onSubmit(v, { into: into().split(",") as Country[], madeIn: madeIn(), evidence: evidence() });
  };

  const upload = async (files: File[]) => {
    setUploadError("");
    setUploading(true);
    try {
      for (const f of files) {
        const ev = await answers.uploadEvidence(f, f.type === "application/pdf" ? "spec_sheet" : "photo");
        setEvidence((e) => [...e, ev]);
      }
    } catch (e) {
      setUploadError(plainProblem(e).message);
    } finally {
      setUploading(false);
    }
  };

  const pick = "inline-flex h-8 items-center gap-1 whitespace-nowrap rounded-full bg-paper-2 px-3 text-[13px] font-[550] text-ink-2 hover:text-ink hover:bg-paper-3 cursor-pointer";

  return (
    <form
      role="search"
      class="w-full"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <div
        class={`relative flex flex-wrap items-center gap-2 rounded-[var(--radius-card)] border border-rule-2 bg-card shadow-[var(--shadow-card)] transition-[border-color,box-shadow] focus-within:border-ink focus-within:shadow-[0_0_0_4px_rgb(24_24_27/0.06)] ${
          hero() ? "min-h-[60px] py-2 pl-4 pr-2 max-sm:pl-3" : "min-h-[50px] py-1.5 pl-3.5 pr-1.5"
        }`}
      >
        <SearchIcon size={17} class="shrink-0 text-muted" />
        <Combobox.Root
          collection={collection()}
          inputValue={text()}
          onInputValueChange={(d) => setText(d.inputValue)}
          onValueChange={(d) => {
            const v = d.value[0];
            if (v) {
              setText(v);
              submit(v);
            }
          }}
          allowCustomValue
          inputBehavior="none"
          openOnClick={false}
          selectionBehavior="preserve"
          positioning={{ sameWidth: true, gutter: 6 }}
          class="min-w-0 flex-1"
        >
          <Combobox.Label class="sr-only">{props.label}</Combobox.Label>
          <Combobox.Control>
            <Combobox.Input
              id={props.id}
              placeholder={props.placeholder}
              autocomplete="off"
              enterkeyhint={props.mode === "classify" ? "go" : "search"}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !items().some((i) => i === text())) {
                  // No suggestion highlighted: Enter submits the question as typed.
                  const highlighted = (e.currentTarget as HTMLInputElement).getAttribute("aria-activedescendant");
                  if (!highlighted) {
                    e.preventDefault();
                    submit();
                  }
                }
              }}
              class={`w-full min-w-0 border-0 bg-transparent py-2 text-ink outline-none placeholder:text-muted focus-visible:shadow-none focus-visible:outline-none ${
                hero() ? "text-[17px] max-sm:text-[16px]" : "text-[15.5px]"
              }`}
            />
          </Combobox.Control>
          <Show when={items().length > 0}>
            <Portal>
              <Combobox.Positioner class="z-50">
                <Combobox.Content class={floating({ class: "max-h-[320px] overflow-auto py-1.5" })}>
                  <p class="px-3.5 pb-1 pt-1 text-[12px] font-[600] text-muted">
                    {props.mode === "classify" ? "Asked before" : "Suggestions"}
                  </p>
                  <For each={items()}>
                    {(item) => (
                      <Combobox.Item item={item} class="mx-1.5 cursor-pointer rounded-[6px] px-2.5 py-2 text-[14.5px] data-[highlighted]:bg-paper-2">
                        <Combobox.ItemText>{item}</Combobox.ItemText>
                      </Combobox.Item>
                    )}
                  </For>
                </Combobox.Content>
              </Combobox.Positioner>
            </Portal>
          </Show>
        </Combobox.Root>

        <Show when={props.mode === "classify"}>
          <div class={`flex shrink-0 items-center gap-1.5 ${hero() ? "max-sm:order-3 max-sm:w-full" : "max-md:hidden"}`}>
            <Select.Root collection={intoCollection} value={[into()]} onValueChange={(d) => d.value[0] && setInto(d.value[0])} positioning={{ gutter: 6 }}>
              <Select.Label class="sr-only">Importing into</Select.Label>
              <Select.Control>
                <Select.Trigger class={pick}>
                  <span class="font-[450] text-muted">Into</span>
                  <Select.ValueText />
                  <ChevronIcon size={12} class="text-muted" />
                </Select.Trigger>
              </Select.Control>
              <Portal>
                <Select.Positioner class="z-50">
                  <Select.Content class={floating({ class: "min-w-[180px] py-1" })}>
                    <For each={INTO_CHOICES}>
                      {(c) => (
                        <Select.Item item={c} class="mx-1 flex cursor-pointer items-center justify-between gap-4 rounded-[6px] px-2.5 py-2 text-[14px] data-[highlighted]:bg-paper-2">
                          <Select.ItemText>{c.label}</Select.ItemText>
                          <Select.ItemIndicator>✓</Select.ItemIndicator>
                        </Select.Item>
                      )}
                    </For>
                  </Select.Content>
                </Select.Positioner>
              </Portal>
              <Select.HiddenSelect />
            </Select.Root>
            <Select.Root collection={originCollection()} value={[madeIn()]} onValueChange={(d) => d.value[0] && setMadeIn(d.value[0])} positioning={{ gutter: 6 }}>
              <Select.Label class="sr-only">Made in</Select.Label>
              <Select.Control>
                <Select.Trigger class={pick}>
                  <span class="font-[450] text-muted">From</span>
                  <Select.ValueText />
                  <ChevronIcon size={12} class="text-muted" />
                </Select.Trigger>
              </Select.Control>
              <Portal>
                <Select.Positioner class="z-50">
                  <Select.Content class={floating({ class: "min-w-[160px] py-1" })}>
                    <For each={originCollection().items}>
                      {(c) => (
                        <Select.Item item={c} class="mx-1 flex cursor-pointer items-center justify-between gap-4 rounded-[6px] px-2.5 py-2 text-[14px] data-[highlighted]:bg-paper-2">
                          <Select.ItemText>{c.label}</Select.ItemText>
                          <Select.ItemIndicator>✓</Select.ItemIndicator>
                        </Select.Item>
                      )}
                    </For>
                  </Select.Content>
                </Select.Positioner>
              </Portal>
              <Select.HiddenSelect />
            </Select.Root>
            <Show when={props.allowFiles}>
              <FileUpload.Root
                maxFiles={2}
                maxFileSize={10 * 1024 * 1024}
                accept={["application/pdf", "image/jpeg", "image/png", "image/webp"]}
                onFileAccept={(d) => void upload(d.files)}
                onFileReject={() => setUploadError("We accept PDF spec sheets and JPEG, PNG or WebP photos up to 10 MB.")}
              >
                <FileUpload.Label class="sr-only">Attach a spec sheet or photo</FileUpload.Label>
                <FileUpload.Trigger class={pick} aria-label="Attach a spec sheet (PDF) or a photo">
                  <PaperclipIcon size={15} />
                  <span class="max-lg:hidden">{uploading() ? "Reading…" : "Spec or photo"}</span>
                </FileUpload.Trigger>
                <FileUpload.HiddenInput />
              </FileUpload.Root>
            </Show>
          </div>
        </Show>

        <button
          type="submit"
          disabled={props.busy}
          class={button({ size: hero() ? "lg" : "md", class: `rounded-[10px] ${hero() ? "max-sm:order-4 max-sm:ml-auto max-sm:h-10" : ""}` })}
        >
          {props.mode === "classify" ? "Classify" : "Search"}
        </button>
      </div>
      <Show when={evidence().length || uploadError()}>
        <div class="mt-2 flex flex-wrap items-center gap-2 text-[13.5px]">
          <For each={evidence()}>
            {(ev) => (
              <span class="inline-flex items-center gap-1.5 rounded-full bg-paper-2 px-2.5 py-1">
                <PaperclipIcon size={13} />
                <span class="font-code text-[12.5px]">{ev.fileName}</span>
                <span class="text-muted">· {ev.kindLabel}{ev.certain ? "" : ", details unclear"}</span>
                <button type="button" aria-label={`Remove ${ev.fileName}`} onClick={() => setEvidence((x) => x.filter((e) => e.id !== ev.id))}>
                  <CloseIcon size={11} />
                </button>
              </span>
            )}
          </For>
          <Show when={uploadError()}>
            <span role="alert" class="font-[600] text-bad">
              {uploadError()}
            </span>
          </Show>
        </div>
      </Show>
    </form>
  );
}
