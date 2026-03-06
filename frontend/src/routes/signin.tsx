import { Title } from "@solidjs/meta";
import { A, useNavigate, useSearchParams } from "@solidjs/router";
import { For, Match, Show, Switch, createSignal } from "solid-js";
import { PublicBar } from "~/components/landing/Public";
import { ApiProblem } from "~/lib/api";
import { auth } from "~/lib/endpoints";
import { plainProblem } from "~/lib/problem";
import { useSession } from "~/lib/session";
import type { Me, Role } from "~/lib/types";
import { initials } from "~/lib/format";
import { CompassMark } from "~/ui/Compass";
import { ChevronIcon } from "~/ui/Icons";
import { button, card } from "~/ui/recipes";

type Step = "email" | "password" | "org";

export default function SignIn() {
  const { session, reload } = useSession();
  const navigate = useNavigate();
  const [params] = useSearchParams<{ next?: string; ended?: string }>();
  const [step, setStep] = createSignal<Step>("email");
  const [email, setEmail] = createSignal("");
  const [password, setPassword] = createSignal("");
  const [error, setError] = createSignal("");
  const [busy, setBusy] = createSignal(false);
  const [me, setMe] = createSignal<Me | null>(null);
  const [linkSent, setLinkSent] = createSignal(false);
  let input!: HTMLInputElement;

  const next = () => (params.next && params.next.startsWith("/") && !params.next.startsWith("//") ? params.next : "/home");
  const finish = async () => {
    await reload();
    navigate(next(), { replace: true });
  };
  const afterSignIn = async (m: Me) => {
    if (m.orgs.length > 1) {
      setMe(m);
      setStep("org");
      return;
    }
    await finish();
  };

  const submit = async (e: Event) => {
    e.preventDefault();
    setError("");
    if (step() === "email") {
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(email().trim())) {
        setError("Enter your work email, like name@company.com.");
        return;
      }
      setStep("password");
      queueMicrotask(() => input?.focus());
      return;
    }
    if (step() === "password") {
      setBusy(true);
      try {
        await afterSignIn(await auth.login(email().trim(), password()));
      } catch (err) {
        const p = plainProblem(err);
        const tries = err instanceof ApiProblem ? err.problem.triesLeft : undefined;
        if (p.code === "invalid_credentials")
          setError(`That password didn't match.${tries !== undefined ? ` ${tries} ${tries === 1 ? "try" : "tries"} left before we pause sign-in for this email for 15 minutes.` : ""}`);
        else if (p.code === "sign_in_paused" && err instanceof ApiProblem)
          setError(`Too many tries. Sign-in for this email is paused for ${Math.ceil((err.problem.retryAfterSeconds ?? 900) / 60)} minutes.`);
        else setError(p.message);
      } finally {
        setBusy(false);
      }
    }
  };

  const demo = async (role: Role) => {
    setBusy(true);
    setError("");
    try {
      await afterSignIn(await auth.demo(role));
    } catch (err) {
      setError(plainProblem(err).message);
    } finally {
      setBusy(false);
    }
  };

  const chooseOrg = async (orgId: string) => {
    setBusy(true);
    try {
      await auth.switchOrg(orgId);
      await finish();
    } catch (err) {
      setError(plainProblem(err).message);
    } finally {
      setBusy(false);
    }
  };

  const field =
    "h-11 w-full rounded-[var(--radius-btn)] border border-rule-2 bg-card px-3.5 text-[15px] text-ink outline-none placeholder:text-muted focus:border-ink aria-[invalid=true]:border-bad";

  return (
    <>
      <Title>Sign in · Tariff Compass</Title>
      <PublicBar
        right={
          <A href="/" class={button({ tone: "ghost", size: "sm" })}>
            Try a sample
          </A>
        }
      />
      <main id="main" class="mx-auto max-w-[420px] px-4 pb-20 pt-[clamp(24px,8vh,88px)]">
        <div class="text-center">
          <CompassMark size={40} class="mx-auto text-ink" state={busy() ? "seek" : "still"} />
          <h1 class="page-title mt-4">{step() === "org" ? "Choose an organisation" : "Sign in"}</h1>
        </div>
        <Show when={params.ended}>
          <p role="status" class="mt-4 rounded-[var(--radius-btn)] bg-paper-2 px-3 py-2 text-center text-[13.5px] text-ink-2">
            Your session ended. Sign in to pick up where you were.
          </p>
        </Show>

        <Switch>
          <Match when={step() !== "org"}>
            <form onSubmit={submit} class={card({ class: "mt-6 p-6 max-sm:p-5" })} novalidate>
              <Show
                when={step() === "password"}
                fallback={
                  <>
                    <label for="email" class="text-[13px] font-[600] text-ink-2">
                      Work email
                    </label>
                    <input
                      id="email"
                      type="email"
                      autocomplete="username"
                      value={email()}
                      onInput={(e) => setEmail(e.currentTarget.value)}
                      placeholder="name@company.com"
                      aria-invalid={!!error()}
                      aria-describedby={error() ? "signin-error" : undefined}
                      class={`${field} mt-1.5`}
                      autofocus
                    />
                  </>
                }
              >
                <div class="flex items-baseline justify-between gap-3">
                  <label for="password" class="text-[13px] font-[600] text-ink-2">
                    Password
                  </label>
                  <button type="button" class="truncate text-[12.5px] text-muted underline underline-offset-4 hover:text-ink" onClick={() => setStep("email")}>
                    {email()}
                  </button>
                </div>
                <input
                  ref={input}
                  id="password"
                  type="password"
                  autocomplete="current-password"
                  value={password()}
                  onInput={(e) => setPassword(e.currentTarget.value)}
                  aria-invalid={!!error()}
                  aria-describedby={error() ? "signin-error" : undefined}
                  class={`${field} mt-1.5`}
                />
              </Show>
              <Show when={error()}>
                <p id="signin-error" role="alert" class="mt-2.5 text-[13.5px] font-[550] text-bad">
                  {error()}
                </p>
              </Show>
              <button type="submit" class={button({ size: "lg", class: "mt-4 w-full" })} disabled={busy()}>
                {step() === "email" ? "Continue" : "Sign in"}
              </button>
              <p class="mt-3 text-center text-[13px] text-muted">
                <Show when={!linkSent()} fallback={<span role="status">If that address has an account, a link is on its way.</span>}>
                  <button type="button" class="underline underline-offset-4 hover:text-ink" onClick={() => setLinkSent(true)}>
                    Email me a sign-in link
                  </button>
                </Show>
              </p>
            </form>
          </Match>
          <Match when={step() === "org"}>
            <ul class={card({ class: "mt-6 overflow-hidden" })}>
              <For each={me()?.orgs ?? []}>
                {(o) => (
                  <li class="border-b border-rule last:border-b-0">
                    <button type="button" class="flex w-full items-center justify-between gap-4 px-5 py-3.5 text-left hover:bg-paper-2" onClick={() => void chooseOrg(o.id)}>
                      <span>
                        <span class="block text-[15px] font-[600]">{o.name}</span>
                        <span class="text-[12.5px] text-muted">
                          {o.roleLabel}
                          {o.viaBroker ? ` · through ${o.viaBroker}` : ""}
                        </span>
                      </span>
                      <ChevronIcon size={15} class="-rotate-90 text-muted" />
                    </button>
                  </li>
                )}
              </For>
            </ul>
          </Match>
        </Switch>

        <Show when={session()?.demoSignIn && session()!.demoPeople.length && step() !== "org"}>
          <section class="mt-8" aria-labelledby="demo-h">
            <p id="demo-h" class="label text-center">
              Or try as
            </p>
            <ul class={card({ class: "mt-3 overflow-hidden" })}>
              <For each={session()!.demoPeople}>
                {(p) => (
                  <li class="border-b border-rule last:border-b-0">
                    <button type="button" disabled={busy()} class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-paper-2" onClick={() => void demo(p.role)}>
                      <span class="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-paper-2 text-[12px] font-[650] text-ink-2">{initials(p.fullName)}</span>
                      <span class="min-w-0 flex-1">
                        <span class="block text-[14.5px] font-[600]">{p.fullName}</span>
                        <span class="block text-[12.5px] text-muted">
                          {p.roleLabel} · {p.orgName}
                        </span>
                      </span>
                      <ChevronIcon size={15} class="-rotate-90 text-muted" />
                    </button>
                  </li>
                )}
              </For>
            </ul>
          </section>
        </Show>
      </main>
    </>
  );
}
