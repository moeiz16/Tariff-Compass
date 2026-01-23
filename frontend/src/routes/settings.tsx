import { Select, createListCollection } from "@ark-ui/solid/select";
import { Switch } from "@ark-ui/solid/switch";
import { A, useNavigate, useSearchParams } from "@solidjs/router";
import { For, Show, createResource, createSignal, type JSX } from "solid-js";
import { Portal } from "solid-js/web";
import { AppPage } from "~/components/shell/AppPage";
import { auth, org, rules } from "~/lib/endpoints";
import { dateShort } from "~/lib/format";
import { plainProblem } from "~/lib/problem";
import { useSession } from "~/lib/session";
import type { MemberOut, Role } from "~/lib/types";
import { ChevronIcon } from "~/ui/Icons";
import { button, floating } from "~/ui/recipes";
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
        <Select.Trigger class="inline-flex h-9 items-center gap-2 rounded-[var(--radius-btn)] border border-rule bg-paper px-2.5 text-[14.5px] hover:border-ink disabled:opacity-60">
          <Select.ValueText />
          <ChevronIcon size={12} />
        </Select.Trigger>
      </Select.Control>
      <Portal>
        <Select.Positioner class="z-50">
          <Select.Content class={floating({ class: "min-w-[220px] py-1" })}>
            <For each={ROLE_ITEMS}>
              {(r) => (
                <Select.Item item={r} class="flex cursor-pointer justify-between gap-3 px-3 py-2 text-[14.5px] data-[highlighted]:bg-paper-2">
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
      <Switch.Control class="relative h-[24px] w-[42px] rounded-full border-[1.5px] border-ink bg-paper transition-colors data-[state=checked]:bg-ink">
        <Switch.Thumb class="block h-[16px] w-[16px] translate-x-[3px] translate-y-[2.5px] rounded-full bg-ink transition-transform data-[state=checked]:translate-x-[20px] data-[state=checked]:bg-paper" />
      </Switch.Control>
      <Switch.Label class="text-[15.5px]">{props.label}</Switch.Label>
      <Switch.HiddenInput />
    </Switch.Root>
  );
}

function Block(props: { id: string; title: string; children: JSX.Element; aside?: JSX.Element }) {
  return (
    <section id={props.id} aria-labelledby={`${props.id}-h`} class="border-t-[1.5px] border-ink py-8">
      <div class="flex flex-wrap items-baseline justify-between gap-3">
        <h2 id={`${props.id}-h`} class="text-[24px] font-[750] tracking-[-0.01em]">
          {props.title}
        </h2>
        {props.aside}
      </div>
      <div class="mt-4">{props.children}</div>
    </section>
  );
}

export default function SettingsPage() {
  const { can, me, reload } = useSession();
  const navigate = useNavigate();
  const [params] = useSearchParams<{ switch?: string }>();
  const [settings, { mutate: setSettings, refetch }] = createResource(() => org.settings());
  const [members, { refetch: refetchMembers }] = createResource(() => org.members());
  const [roles] = createResource(() => org.roles().catch(() => []));
  const [invitations, { refetch: refetchInv }] = createResource(() => (can("members:manage") ? true : null), () => org.invitations());
  const [brokers] = createResource(() => org.brokers().catch(() => []));
  const [ruleList, { refetch: refetchRules }] = createResource(() => rules.list().catch(() => []));
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

  const NAV = [
    ["defaults", "Defaults"],
    ["people", "People and roles"],
    ["broker", "Your broker"],
    ["rules", "Always-review rules"],
    ["records", "Records"],
  ];

  return (
    <AppPage title="Settings" scope="none" placeholder="Search rulings: a product, a code, a ruling number" boxLabel="Search the rulings" onSearch={(q) => navigate(`/rulings?q=${encodeURIComponent(q)}`)}>
      <div class="gm py-8">
        <nav aria-label="Settings sections" class="max-[960px]:mb-4">
          <ul class="sticky top-4 space-y-3 text-[16.5px] max-[960px]:static max-[960px]:flex max-[960px]:flex-wrap max-[960px]:gap-x-4 max-[960px]:gap-y-1 max-[960px]:space-y-0">
            <For each={NAV}>
              {([id, label]) => (
                <li>
                  <a href={`#${id}`} class="text-ink-2 no-underline hover:text-ink">
                    {label}
                  </a>
                </li>
              )}
            </For>
            <Show when={can("audit:read")}>
              <li>
                <A href="/activity" class="font-[700] text-ink no-underline hover:underline">
                  Activity record
                </A>
              </li>
            </Show>
          </ul>
        </nav>
        <div class="gm-body max-w-[1000px]">
          <p class="text-[15px] text-ink-2">{me()?.activeOrg?.name} · settings</p>
          <h1 class="mt-1 text-[clamp(32px,3.6vw,44px)] font-[800] tracking-[-0.025em]">Settings</h1>

          <Show when={params.switch && (me()?.orgs.length ?? 0) > 1}>
            <Block id="switch" title="Switch organisation">
              <ul>
                <For each={me()!.orgs}>
                  {(o) => (
                    <li class="flex items-center justify-between border-b border-rule py-2.5">
                      <span>
                        <b>{o.name}</b> <span class="text-muted">· {o.roleLabel}</span>
                      </span>
                      <Show when={o.id !== me()!.activeOrg?.id} fallback={<span class="text-[14px] text-muted">Current</span>}>
                        <button
                          type="button"
                          class={button({ tone: "ghost", size: "sm" })}
                          onClick={async () => {
                            await auth.switchOrg(o.id);
                            await reload();
                            navigate("/home");
                          }}
                        >
                          Work in {o.name}
                        </button>
                      </Show>
                    </li>
                  )}
                </For>
              </ul>
            </Block>
          </Show>

          <Block id="defaults" title="Defaults for new questions">
            <Show when={!settings.error} fallback={<ErrorSlip error={settings.error} retry={refetch} />}>
              <Show when={settings()} fallback={<SkeletonLines lines={4} />}>
                {(s) => (
                  <dl class="grid grid-cols-[220px_minmax(0,1fr)] gap-x-6 gap-y-3 text-[16px] max-sm:grid-cols-1">
                    <dt class="text-muted">Importing into</dt>
                    <dd>{s().into.map((c) => (c === "US" ? "United States" : "Canada")).join(" and ")}</dd>
                    <dt class="text-muted">Usually made in</dt>
                    <dd>{s().madeIn}</dd>
                    <dt class="text-muted">Ports</dt>
                    <dd>{s().ports.join(", ")}</dd>
                    <dt class="text-muted">Always send to a broker</dt>
                    <dd>
                      <Toggle checked={s().alwaysSendToBroker} disabled={!canManage()} onChange={(v) => void patchSettings({ alwaysSendToBroker: v })} label={s().alwaysSendToBroker ? "Every answer goes to the broker" : "Only the always-review rules and unsure answers"} />
                    </dd>
                  </dl>
                )}
              </Show>
            </Show>
          </Block>

          <Block
            id="people"
            title="People and roles"
            aside={
              <Show when={canPeople()}>
                <button type="button" class={button({ tone: "ghost", size: "sm" })} onClick={() => { setInviteLink(""); setEmail(""); setInviting(true); }}>
                  Invite someone
                </button>
              </Show>
            }
          >
            <Show when={members()} fallback={<SkeletonLines lines={5} />}>
              <div class="overflow-x-auto">
                <table class="w-full min-w-[640px] border-collapse text-left">
                  <thead>
                    <tr class="border-b-[1.5px] border-ink text-[14px] text-ink-2">
                      <th class="py-2 pr-3 font-[650]">Person</th>
                      <th class="py-2 pr-3 font-[650]">Role</th>
                      <th class="py-2 pr-3 font-[650]">Can</th>
                      <Show when={canPeople()}>
                        <th class="py-2 font-[650]"><span class="sr-only">Actions</span></th>
                      </Show>
                    </tr>
                  </thead>
                  <tbody>
                    <For each={members()}>
                      {(m) => (
                        <tr class="border-b border-rule align-top">
                          <td class="py-3 pr-3 text-[15.5px]">
                            {m.user.fullName}
                            {m.viaBroker ? ` · ${m.viaBroker.split(" ")[0]}` : ""}
                            <span class="block text-[13.5px] text-muted">{m.title}</span>
                          </td>
                          <td class="py-3 pr-3 text-[15px]">
                            <Show when={canPeople() && !m.viaBroker} fallback={m.roleLabel}>
                              <RoleSelect value={m.role} label={`Role for ${m.user.fullName}`} onChange={(r) => void changeRole(m, r)} disabled={m.user.id === me()?.user.id} />
                            </Show>
                          </td>
                          <td class="py-3 pr-3 text-[15px] text-ink-2">{describe(m.role)}</td>
                          <Show when={canPeople()}>
                            <td class="py-3 text-right">
                              <Show when={m.user.id !== me()?.user.id && !m.viaBroker}>
                                <button type="button" class="text-[14px] text-bad underline underline-offset-4" onClick={() => setRemoving(m)}>
                                  Remove
                                </button>
                              </Show>
                            </td>
                          </Show>
                        </tr>
                      )}
                    </For>
                  </tbody>
                </table>
              </div>
            </Show>
            <Show when={canPeople() && invitations()?.length}>
              <h3 class="mt-6 text-[15px] font-[750]">Invitations waiting</h3>
              <ul class="mt-2">
                <For each={invitations()}>
                  {(i) => (
                    <li class="flex flex-wrap items-center justify-between gap-2 border-b border-rule py-2 text-[15px]">
                      <span>
                        {i.email} · {i.roleLabel} <span class="text-muted">· expires {dateShort(i.expiresAt)}</span>
                      </span>
                      <button
                        type="button"
                        class="text-[14px] underline underline-offset-4"
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
          </Block>

          <Block id="broker" title="Your broker">
            <For each={brokers() ?? []} fallback={<p class="text-[15.5px] text-ink-2">No broker firm is engaged yet.</p>}>
              {(e) => (
                <div class="text-[16px]">
                  <p>
                    <b>{e.brokerOrg}</b> handles {e.countriesLabel} for {e.importerOrg}, since {dateShort(e.startedOn)}.
                  </p>
                  <ul class="mt-2">
                    <For each={e.people}>
                      {(p) => (
                        <li class="border-b border-rule py-2 text-[15px]">
                          {p.user.fullName} <span class="text-muted">· {p.title}</span>
                          <Show when={p.user.licence}>
                            <span class="ml-2 font-code text-[13px] text-ink-2">{p.user.licence}</span>
                          </Show>
                        </li>
                      )}
                    </For>
                  </ul>
                </div>
              )}
            </For>
          </Block>

          <Block id="rules" title="Always-review rules">
            <p class="text-[15.5px] text-ink-2">Products matching a rule go to the broker even when the classifier is sure.</p>
            <ul class="mt-3">
              <For each={ruleList() ?? []}>
                {(r) => (
                  <li class="flex flex-wrap items-center justify-between gap-3 border-b border-rule py-2.5">
                    <span class="text-[15.5px]">
                      {r.label} <span class="text-[13.5px] text-muted">· {r.kindLabel.toLowerCase()} · {r.matches} products now</span>
                    </span>
                    <Toggle
                      checked={r.active}
                      disabled={!can("rules:manage")}
                      label={r.active ? "On" : "Off"}
                      onChange={(v) => void toggleRule(r.id, v)}
                    />
                  </li>
                )}
              </For>
            </ul>
            <Show when={can("rules:manage")}>
              <form
                class="mt-4 flex flex-wrap items-end gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  void addRule();
                }}
              >
                <label class="text-[13px] font-[650] text-ink-2">
                  Kind
                  <select value={newRule().kind} onChange={(e) => setNewRule({ ...newRule(), kind: e.currentTarget.value })} class="mt-1 block h-10 rounded-[var(--radius-btn)] border-[1.5px] border-ink bg-paper px-2 text-[15px] font-[400] text-ink">
                    <option value="keyword">Keyword</option>
                    <option value="heading">Heading</option>
                    <option value="chapter">Chapter</option>
                    <option value="material">Material</option>
                    <option value="value_over">Value over</option>
                    <option value="origin">Origin</option>
                  </select>
                </label>
                <label class="text-[13px] font-[650] text-ink-2">
                  Value
                  <input value={newRule().value} onInput={(e) => setNewRule({ ...newRule(), value: e.currentTarget.value })} class="mt-1 block h-10 w-[150px] rounded-[var(--radius-btn)] border-[1.5px] border-ink bg-paper px-2 text-[15px] font-[400] text-ink" placeholder="lithium" />
                </label>
                <label class="min-w-[220px] flex-1 text-[13px] font-[650] text-ink-2">
                  Label
                  <input value={newRule().label} onInput={(e) => setNewRule({ ...newRule(), label: e.currentTarget.value })} class="mt-1 block h-10 w-full rounded-[var(--radius-btn)] border-[1.5px] border-ink bg-paper px-2 text-[15px] font-[400] text-ink" placeholder="Anything with lithium cells" />
                </label>
                <button type="submit" class={button({ size: "md" })}>
                  Add rule
                </button>
              </form>
            </Show>
          </Block>

          <Block id="records" title="Records">
            <Show when={settings()}>
              {(s) => (
                <div class="space-y-2 text-[16px] leading-[1.6]">
                  <p>{s().retentionNote ?? `Each binder is kept ${s().retentionYears} years after the product's latest entry (19 CFR 163.4).`}</p>
                  <p class="text-ink-2">{s().deletingNote}</p>
                  <Show when={can("audit:read")}>
                    <p>
                      Every sensitive action is in the{" "}
                      <A href="/activity" class="underline underline-offset-4">
                        activity record
                      </A>
                      , chained so any change to an old entry shows.
                    </p>
                  </Show>
                </div>
              )}
            </Show>
          </Block>
        </div>
      </div>

      <Sheet open={inviting()} onOpenChange={setInviting} title="Invite someone" description="They get a link that works once, for seven days. Their role decides what they can see and do.">
        <Show
          when={!inviteLink()}
          fallback={
            <div>
              <p class="text-[15.5px]">Send this link to {email()}. It is shown only once.</p>
              <p class="mt-2 break-all rounded-[var(--radius-btn)] border border-rule bg-paper-2 px-3 py-2 font-code text-[13px]">{inviteLink()}</p>
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
            <label class="block text-[13px] font-[650] text-ink-2">
              Work email
              <input type="email" value={email()} onInput={(e) => setEmail(e.currentTarget.value)} aria-invalid={!!inviteError()} class="mt-1 h-11 w-full rounded-[var(--radius-btn)] border-[1.5px] border-ink bg-paper px-3 text-[15.5px] font-[400] text-ink" />
            </label>
            <div class="flex items-center gap-3 text-[13px] font-[650] text-ink-2">
              Role <RoleSelect value={inviteRole()} label="Role for the invitation" onChange={setInviteRole} />
            </div>
            <p class="text-[14px] text-muted">{describe(inviteRole())}</p>
            <Show when={inviteError()}>
              <p role="alert" class="text-[14px] font-[600] text-bad">
                {inviteError()}
              </p>
            </Show>
            <div class="flex gap-2">
              <button type="submit" class={button()}>
                Send invitation
              </button>
              <button type="button" class={button({ tone: "ghost" })} onClick={() => setInviting(false)}>
                Not yet
              </button>
            </div>
          </form>
        </Show>
      </Sheet>
      <Sheet open={!!removing()} onOpenChange={(o) => !o && setRemoving(null)} role="alertdialog" title={`Remove ${removing()?.user.fullName ?? ""}?`} description="They lose access right away. Their past decisions stay in every binder and in the activity record.">
        <div class="flex gap-2">
          <button type="button" class={button({ tone: "danger" })} onClick={() => void remove()}>
            Remove
          </button>
          <button type="button" class={button({ tone: "ghost" })} onClick={() => setRemoving(null)}>
            Keep them
          </button>
        </div>
      </Sheet>
    </AppPage>
  );
}
