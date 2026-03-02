import { Select, createListCollection } from "@ark-ui/solid/select";
import { Switch } from "@ark-ui/solid/switch";
import { Tabs } from "@ark-ui/solid/tabs";
import { A, useNavigate, useSearchParams } from "@solidjs/router";
import { For, Show, createResource, createSignal } from "solid-js";
import { Portal } from "solid-js/web";
import { AppPage, PageHead } from "~/components/shell/AppPage";
import { auth, meta, org, rules } from "~/lib/endpoints";
import { now } from "~/lib/clock";
import { dateShort } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import { useSession, useSigned } from "~/lib/session";
import type { MemberOut, Role } from "~/lib/types";
import { ChevronIcon } from "~/ui/Icons";
import { button, card, field, floating, tag } from "~/ui/recipes";
import { Tip } from "~/ui/Tip";
import { Sheet } from "~/ui/Sheet";
import { ErrorSlip, SkeletonLines } from "~/ui/States";
import { notify } from "~/ui/Toast";

const ROLE_ITEMS = [
  { value: "importer", label: "Importer" },
  { value: "broker", label: "Licensed customs broker" },
  { value: "compliance", label: "Compliance lead" },
  { value: "admin", label: "Administrator" },
];
const roleCollection = createListCollection({ items: ROLE_ITEMS });

function RoleSelect(props: { value: Role; onChange: (r: Role) => void; label: string; disabled?: boolean }) {
  return (
    <Select.Root collection={roleCollection} value={[props.value]} onValueChange={(d) => d.value[0] && props.onChange(d.value[0] as Role)} disabled={props.disabled} positioning={{ gutter: 6 }}>
      <Select.Label class="sr-only">{props.label}</Select.Label>
      <Select.Control>
        <Select.Trigger class="inline-flex h-9 items-center gap-2 rounded-[var(--radius-btn)] border border-rule-2 bg-card px-2.5 text-[14px] hover:border-ink disabled:opacity-60">
          <Select.ValueText />
          <ChevronIcon size={12} />
        </Select.Trigger>
      </Select.Control>
      <Portal>
        <Select.Positioner class="z-50">
          <Select.Content class={floating({ class: "min-w-[220px] p-1" })}>
            <For each={ROLE_ITEMS}>
              {(r) => (
                <Select.Item item={r} class="flex cursor-pointer justify-between gap-3 rounded-[6px] px-2.5 py-2 text-[14px] data-[highlighted]:bg-paper-2">
                  <Select.ItemText>{r.label}</Select.ItemText>
                  <Select.ItemIndicator>✓</Select.ItemIndicator>
                </Select.Item>
              )}
            </For>
          </Select.Content>
        </Select.Positioner>
      </Portal>
      <Select.HiddenSelect />
    </Select.Root>
  );
}

function Toggle(props: { checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean }) {
  return (
    <Switch.Root checked={props.checked} onCheckedChange={(d) => props.onChange(d.checked)} disabled={props.disabled} class="inline-flex cursor-pointer items-center gap-3 data-[disabled]:cursor-default">
      <Switch.Control class="relative h-[22px] w-[38px] shrink-0 rounded-full bg-paper-3 transition-colors data-[state=checked]:bg-ink">
        <Switch.Thumb class="block h-[18px] w-[18px] translate-x-[2px] translate-y-[2px] rounded-full bg-card shadow-[var(--shadow-card)] transition-transform data-[state=checked]:translate-x-[18px]" />
      </Switch.Control>
      <Switch.Label class="text-[14px]">{props.label}</Switch.Label>
      <Switch.HiddenInput />
    </Switch.Root>
  );
}

export default function SettingsPage() {
  const signed = useSigned();
  const { can, me, reload } = useSession();
  const navigate = useNavigate();
  const [params] = useSearchParams<{ switch?: string }>();
  const [settings, { mutate: setSettings, refetch }] = createResource(signed(() => true), () => org.settings());
  const [members, { refetch: refetchMembers }] = createResource(signed(() => true), () => org.members());
  const [roles] = createResource(signed(() => true), () => org.roles().catch(() => []));
  const [invitations, { refetch: refetchInv }] = createResource(() => (can("members:manage") ? true : null), () => org.invitations());
  const [brokers] = createResource(signed(() => true), () => org.brokers().catch(() => []));
  const [ruleList, { refetch: refetchRules }] = createResource(signed(() => true), () => rules.list().catch(() => []));
  const [m] = createResource(signed(() => true), () => meta.get().catch(() => null));
  const originLabel = (code: string) => m()?.origins.find((o) => o.key === code)?.label ?? code;
  const expiresIn = (iso: string) => {
    const days = Math.ceil((Date.parse(iso) - now().getTime()) / 86_400_000);
    return days <= 0 ? "expired" : days === 1 ? "expires tomorrow" : `expires in ${days} days`;
  };
  const [inviting, setInviting] = createSignal(false);
  const [email, setEmail] = createSignal("");
  const [inviteRole, setInviteRole] = createSignal<Role>("importer");
  const [inviteLink, setInviteLink] = createSignal("");
  const [inviteError, setInviteError] = createSignal("");
  const [removing, setRemoving] = createSignal<MemberOut | null>(null);
  const [newRule, setNewRule] = createSignal({ kind: "keyword", value: "", label: "" });

  const canManage = () => can("settings:manage");
  const canPeople = () => can("members:manage");
  const describe = (role: Role) => roles()?.find((r) => r.role === role)?.description ?? "";

  const patchSettings = async (body: Parameters<typeof org.updateSettings>[0]) => {
    try {
      setSettings(await org.updateSettings(body));
      notify("Settings saved", "Recorded in the activity record.");
    } catch (e) {
      notify("Not saved", plainProblem(e).message, "error");
    }
  };
  const changeRole = async (m: MemberOut, role: Role) => {
    try {
      await org.updateMember(m.id, { role });
      notify(`${m.user.fullName} is now ${ROLE_ITEMS.find((r) => r.value === role)?.label.toLowerCase()}`);
      void refetchMembers();
    } catch (e) {
      notify("Role not changed", plainProblem(e).message, "error");
    }
  };
  const invite = async () => {
    setInviteError("");
    try {
      const inv = await org.invite(email().trim(), inviteRole());
      setInviteLink(inv.link ?? "");
      void refetchInv();
    } catch (e) {
      const p = plainProblem(e);
      setInviteError(p.fields.email ?? p.message);
    }
  };
  const remove = async () => {
    const m = removing();
    if (!m) return;
    try {
      await org.removeMember(m.id);
      notify(`${m.user.fullName} removed`, "Their past decisions stay in the record.");
      setRemoving(null);
      void refetchMembers();
    } catch (e) {
      notify("Not removed", plainProblem(e).message, "error");
    }
  };
  const addRule = async () => {
    const r = newRule();
    if (r.value.trim().length < 1 || r.label.trim().length < 3) return notify("Add a value and a label", undefined, "error");
    try {
      await rules.create({ kind: r.kind, value: r.value.trim(), label: r.label.trim() });
      setNewRule({ kind: "keyword", value: "", label: "" });
      void refetchRules();
      notify("Rule added", "Matching products now always go to the broker.");
    } catch (e) {
      notify("Rule not added", plainProblem(e).message, "error");
    }
  };

  const toggleRule = async (id: string, active: boolean) => {
    await rules.update(id, { active }).catch((e) => notify("Not changed", plainProblem(e).message, "error"));
    void refetchRules();
  };

  const f = field();
  const row = "flex flex-wrap items-center justify-between gap-3 border-b border-rule px-5 py-3.5 last:border-b-0 max-sm:px-4";
  const tabItem =
    "w-full cursor-pointer rounded-[8px] px-3 py-2 text-left text-[14px] font-[550] text-muted hover:bg-paper-2 hover:text-ink data-[selected]:bg-paper-2 data-[selected]:text-ink max-md:w-auto max-md:whitespace-nowrap";

  return (
    <AppPage title="Settings" place="none" width="default">
      <PageHead title="Settings" meta={<span>{me()?.activeOrg?.name}</span>} />
      <Tabs.Root defaultValue={params.switch && (me()?.orgs.length ?? 0) > 1 ? "switch" : "defaults"} orientation="vertical" class="grid grid-cols-[200px_minmax(0,1fr)] gap-8 max-md:grid-cols-1 max-md:gap-4">
        <Tabs.List class="flex flex-col gap-0.5 max-md:flex-row max-md:flex-wrap" aria-label="Settings">
          <Show when={(me()?.orgs.length ?? 0) > 1}>
            <Tabs.Trigger value="switch" class={tabItem}>
              Organisation
            </Tabs.Trigger>
          </Show>
          <Tabs.Trigger value="defaults" class={tabItem}>
            Defaults
          </Tabs.Trigger>
          <Tabs.Trigger value="people" class={tabItem}>
            People
          </Tabs.Trigger>
          <Tabs.Trigger value="broker" class={tabItem}>
            Broker
          </Tabs.Trigger>
          <Tabs.Trigger value="rules" class={tabItem}>
            Review rules
          </Tabs.Trigger>
          <Tabs.Trigger value="records" class={tabItem}>
            Records
          </Tabs.Trigger>
        </Tabs.List>

        <div class="min-w-0">
          <Show when={(me()?.orgs.length ?? 0) > 1}>
            <Tabs.Content value="switch">
              <ul class={card({ class: "overflow-hidden" })}>
                <For each={me()!.orgs}>
                  {(o) => (
                    <li class={row}>
                      <span>
                        <span class="block text-[14.5px] font-[600]">{o.name}</span>
                        <span class="text-[12.5px] text-muted">{o.roleLabel}</span>
                      </span>
                      <Show when={o.id !== me()!.activeOrg?.id} fallback={<span class={tag({ tone: "ink" })}>Current</span>}>
                        <button
                          type="button"
                          class={button({ tone: "outline", size: "sm" })}
                          onClick={async () => {
                            await auth.switchOrg(o.id);
                            await reload();
                            navigate("/home");
                          }}
                        >
                          Switch
                        </button>
                      </Show>
                    </li>
                  )}
                </For>
              </ul>
            </Tabs.Content>
          </Show>

          <Tabs.Content value="defaults">
            <Show when={!settings.error} fallback={<ErrorSlip error={settings.error} retry={refetch} />}>
              <Show when={settings()} fallback={<SkeletonLines lines={4} />}>
                {(st) => (
                  <dl class={card({ class: "overflow-hidden" })}>
                    <div class={row}>
                      <dt class="text-[14px] text-muted">Importing into</dt>
                      <dd class="text-[14px]">{st().into.map((c) => (c === "US" ? "United States" : "Canada")).join(" and ")}</dd>
                    </div>
                    <div class={row}>
                      <dt class="text-[14px] text-muted">Usually made in</dt>
                      <dd class="text-[14px]">{originLabel(st().madeIn)}</dd>
                    </div>
                    <div class={row}>
                      <dt class="text-[14px] text-muted">Ports</dt>
                      <dd class="text-[14px]">{st().ports.join(", ")}</dd>
                    </div>
                    <div class={row}>
                      <dt class="text-[14px] text-muted">Send every answer to the broker</dt>
                      <dd>
                        <Toggle checked={st().alwaysSendToBroker} disabled={!canManage()} onChange={(v) => void patchSettings({ alwaysSendToBroker: v })} label={st().alwaysSendToBroker ? "On" : "Off"} />
                      </dd>
                    </div>
                  </dl>
                )}
              </Show>
            </Show>
          </Tabs.Content>

          <Tabs.Content value="people">
            <Show when={canPeople()}>
              <div class="mb-3 flex justify-end">
                <button
                  type="button"
                  class={button({ size: "sm" })}
                  onClick={() => {
                    setInviteLink("");
                    setEmail("");
                    setInviting(true);
                  }}
                >
                  Invite
                </button>
              </div>
            </Show>
            <Show when={members()} fallback={<SkeletonLines lines={5} />}>
              <ul class={card({ class: "overflow-hidden" })}>
                <For each={members()}>
                  {(m) => (
                    <li class={row}>
                      <span class="min-w-0">
                        <span class="block text-[14.5px] font-[600]">
                          {m.user.fullName}
                          {m.viaBroker ? <span class="font-[450] text-muted"> · {m.viaBroker.split(" ")[0]}</span> : null}
                        </span>
                        <span class="text-[12.5px] text-muted">{m.title}</span>
                      </span>
                      <span class="flex items-center gap-3">
                        <Show
                          when={canPeople() && !m.viaBroker}
                          fallback={
                            <Tip label={describe(m.role)}>
                              <span class={tag({ tone: "ink" })}>{m.roleLabel}</span>
                            </Tip>
                          }
                        >
                          <RoleSelect value={m.role} label={`Role for ${m.user.fullName}`} onChange={(r) => void changeRole(m, r)} disabled={m.user.id === me()?.user.id} />
                        </Show>
                        <Show when={canPeople() && m.user.id !== me()?.user.id && !m.viaBroker}>
                          <button type="button" class={button({ tone: "ghost", size: "xs", class: "text-bad hover:text-bad" })} onClick={() => setRemoving(m)}>
                            Remove
                          </button>
                        </Show>
                      </span>
                    </li>
                  )}
                </For>
              </ul>
            </Show>
            <Show when={canPeople() && invitations()?.length}>
              <p class="label mb-2 mt-6">Invitations</p>
              <ul class={card({ class: "overflow-hidden" })}>
                <For each={invitations()}>
                  {(i) => (
                    <li class={row}>
                      <span class="text-[14px]">
                        {i.email} <span class="text-muted">· {i.roleLabel} · {expiresIn(i.expiresAt)}</span>
                      </span>
                      <button
                        type="button"
                        class={button({ tone: "ghost", size: "xs" })}
                        onClick={async () => {
                          await org.revokeInvitation(i.id).catch((e) => notify("Not withdrawn", plainProblem(e).message, "error"));
                          void refetchInv();
                        }}
                      >
                        Withdraw
                      </button>
                    </li>
                  )}
                </For>
              </ul>
            </Show>
          </Tabs.Content>

          <Tabs.Content value="broker">
            <For each={brokers() ?? []} fallback={<div class={card({ class: "px-5 py-6 text-[14px] text-muted" })}>No broker firm yet</div>}>
              {(e) => (
                <section class={card({ class: "overflow-hidden" })}>
                  <div class="border-b border-rule px-5 py-4">
                    <p class="text-[15px] font-[600]">{e.brokerOrg}</p>
                    <p class="text-[12.5px] text-muted">
                      {e.countriesLabel} · since {dateShort(e.startedOn)}
                    </p>
                  </div>
                  <ul>
                    <For each={e.people}>
                      {(p) => (
                        <li class={row}>
                          <span class="text-[14px]">
                            {p.user.fullName} <span class="text-muted">· {p.title}</span>
                          </span>
                          <Show when={p.user.licence}>
                            <span class="font-code text-[12px] text-muted">{p.user.licence}</span>
                          </Show>
                        </li>
                      )}
                    </For>
                  </ul>
                </section>
              )}
            </For>
          </Tabs.Content>

          <Tabs.Content value="rules">
            <ul class={card({ class: "overflow-hidden" })}>
              <For each={ruleList() ?? []}>
                {(r) => (
                  <li class={row}>
                    <span class="min-w-0">
                      <span class="block text-[14.5px]">{r.label}</span>
                      <span class="text-[12.5px] text-muted">
                        {r.kindLabel} · {r.matches} products
                      </span>
                    </span>
                    <Toggle checked={r.active} disabled={!can("rules:manage")} label={r.active ? "On" : "Off"} onChange={(v) => void toggleRule(r.id, v)} />
                  </li>
                )}
              </For>
            </ul>
            <Show when={can("rules:manage")}>
              <form
                class={card({ class: "mt-4 flex flex-wrap items-end gap-2 p-4" })}
                onSubmit={(e) => {
                  e.preventDefault();
                  void addRule();
                }}
              >
                <label class={f.label()}>
                  Kind
                  <select value={newRule().kind} onChange={(e) => setNewRule({ ...newRule(), kind: e.currentTarget.value })} class={f.input({ class: "mt-1 block w-auto font-[400]" })}>
                    <option value="keyword">Keyword</option>
                    <option value="heading">Heading</option>
                    <option value="chapter">Chapter</option>
                    <option value="material">Material</option>
                    <option value="value_over">Value over</option>
                    <option value="origin">Origin</option>
                  </select>
                </label>
                <label class={f.label()}>
                  Value
                  <input value={newRule().value} onInput={(e) => setNewRule({ ...newRule(), value: e.currentTarget.value })} class={f.input({ class: "mt-1 block w-[140px] font-[400]" })} placeholder="lithium" />
                </label>
                <label class={f.label({ class: "min-w-[200px] flex-1" })}>
                  Label
                  <input value={newRule().label} onInput={(e) => setNewRule({ ...newRule(), label: e.currentTarget.value })} class={f.input({ class: "mt-1 block font-[400]" })} placeholder="Anything with lithium cells" />
                </label>
                <button type="submit" class={button({ size: "md" })}>
                  Add
                </button>
              </form>
            </Show>
          </Tabs.Content>

          <Tabs.Content value="records">
            <Show when={settings()}>
              {(st) => (
                <dl class={card({ class: "overflow-hidden" })}>
                  <div class={`${row} items-start`}>
                    <dt class="text-[14px] text-muted">Kept for</dt>
                    <dd class="max-w-[440px] text-right text-[14px]">
                      {st().retentionYears} years
                      <Show when={st().retentionNote}>
                        <span class="mt-0.5 block text-[12.5px] text-muted">{st().retentionNote}</span>
                      </Show>
                    </dd>
                  </div>
                  <div class={`${row} items-start`}>
                    <dt class="text-[14px] text-muted">Deleting</dt>
                    <dd class="max-w-[440px] text-right text-[13.5px] text-ink-2">{st().deletingNote}</dd>
                  </div>
                  <Show when={can("audit:read")}>
                    <div class={row}>
                      <dt class="text-[14px] text-muted">Activity</dt>
                      <dd>
                        <A href="/activity" class={button({ tone: "outline", size: "sm" })}>
                          Open
                        </A>
                      </dd>
                    </div>
                  </Show>
                </dl>
              )}
            </Show>
          </Tabs.Content>
        </div>
      </Tabs.Root>

      <Sheet open={inviting()} onOpenChange={setInviting} title="Invite someone" description="The link works once, for seven days.">
        <Show
          when={!inviteLink()}
          fallback={
            <div>
              <p class="text-[14px]">Send this link to {email()}. It is shown once.</p>
              <p class="mt-2 break-all rounded-[var(--radius-btn)] bg-paper-2 px-3 py-2 font-code text-[12.5px]">{inviteLink()}</p>
              <button type="button" class={button({ size: "md", class: "mt-4" })} onClick={() => setInviting(false)}>
                Done
              </button>
            </div>
          }
        >
          <form
            class="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              void invite();
            }}
          >
            <label class={f.label({ class: "block" })}>
              Work email
              <input type="email" value={email()} onInput={(e) => setEmail(e.currentTarget.value)} aria-invalid={!!inviteError()} class={f.input({ class: "mt-1 font-[400]" })} />
            </label>
            <div class="flex items-center gap-3 text-[13px] font-[600] text-ink-2">
              Role <RoleSelect value={inviteRole()} label="Role for the invitation" onChange={setInviteRole} />
            </div>
            <p class="text-[13px] text-muted">{describe(inviteRole())}</p>
            <Show when={inviteError()}>
              <p role="alert" class="text-[14px] font-[600] text-bad">
                {inviteError()}
              </p>
            </Show>
            <div class="flex justify-end gap-2">
              <button type="button" class={button({ tone: "ghost" })} onClick={() => setInviting(false)}>
                Cancel
              </button>
              <button type="submit" class={button()}>
                Send
              </button>
            </div>
          </form>
        </Show>
      </Sheet>
      <Sheet open={!!removing()} onOpenChange={(o) => !o && setRemoving(null)} role="alertdialog" title={`Remove ${removing()?.user.fullName ?? ""}?`} description="Access ends now. Their past decisions stay in the record.">
        <div class="flex justify-end gap-2">
          <button type="button" class={button({ tone: "ghost" })} onClick={() => setRemoving(null)}>
            Cancel
          </button>
          <button type="button" class={button({ tone: "danger" })} onClick={() => void remove()}>
            Remove
          </button>
        </div>
      </Sheet>
    </AppPage>
  );
}
