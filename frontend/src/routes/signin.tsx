import { Title } from "@solidjs/meta";
import { A, useNavigate, useSearchParams } from "@solidjs/router";
import { For, Match, Show, Switch, createSignal } from "solid-js";
import { ThemeButton } from "~/components/shell/QueryStrip";
import { ApiProblem } from "~/lib/api";
import { auth } from "~/lib/endpoints";
import { plainProblem } from "~/lib/problem";
import { useSession } from "~/lib/session";
import type { Me, Role } from "~/lib/types";
import { Brand, CompassMark } from "~/ui/Compass";
import { MailIcon } from "~/ui/Icons";
import { button } from "~/ui/recipes";

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

  const stepNo = () => ({ email: 1, password: 2, org: 3 })[step()];

  return (
    <>
      <Title>Sign in · Tariff Compass</Title>
      <header class="flex items-center justify-between px-8 pt-5 max-md:px-4">
        <A href="/" class="no-underline" aria-label="Tariff Compass front page">
          <Brand />
        </A>
        <div class="flex items-center gap-4">
          <ThemeButton />
          <A href="/" class="text-[15.5px] font-[650] text-ink-2 no-underline hover:text-ink max-sm:hidden">
            Try a sample without signing in
          </A>
        </div>
      </header>
      <main id="main" class="mx-auto max-w-[780px] px-4 pb-20 pt-[clamp(32px,10vh,120px)] text-center">
        <CompassMark size={56} class="mx-auto" state={busy() ? "seek" : "still"} />
        <h1 class="mt-6 text-[38px] font-[800] tracking-[-0.02em]">Sign in</h1>
        <p class="mt-2 text-[18px] text-ink-2">Importers and brokers use the same sign-in. One question at a time, like a search.</p>
        <Show when={params.ended}>
          <p role="status" class="mx-auto mt-4 max-w-[560px] rounded-[var(--radius-btn)] border border-rule px-3 py-2 text-[15px] text-ink-2">
            Your session ended. Sign in again and you'll come back where you were.
          </p>
        </Show>

        <Switch>
          <Match when={step() !== "org"}>
            <form onSubmit={submit} class="mx-auto mt-8 max-w-[640px] text-left" novalidate>
              <div class="flex items-center gap-2 rounded-[var(--radius-box)] border-[1.5px] border-ink bg-paper py-1.5 pl-4 pr-1.5 shadow-[var(--shadow-soft)] focus-within:shadow-[0_0_0_4px_var(--color-hi)]">
                <MailIcon size={18} class="shrink-0 text-muted" />
                <Show
                  when={step() === "password"}
                  fallback={
                    <>
                      <label for="email" class="sr-only">
                        Your work email
                      </label>
                      <input
                        id="email"
                        type="email"
                        autocomplete="username"
                        value={email()}
                        onInput={(e) => setEmail(e.currentTarget.value)}
                        placeholder="Your work email"
                        aria-invalid={!!error()}
                        aria-describedby={error() ? "signin-error" : undefined}
                        class="h-12 min-w-0 flex-1 bg-transparent text-[18px] outline-none placeholder:text-muted focus-visible:shadow-none focus-visible:outline-none"
                        autofocus
                      />
                    </>
                  }
                >
                  <label for="password" class="sr-only">
                    Password for {email()}
                  </label>
                  <input
                    ref={input}
                    id="password"
                    type="password"
                    autocomplete="current-password"
                    value={password()}
                    onInput={(e) => setPassword(e.currentTarget.value)}
                    placeholder={`Password for ${email()}`}
                    aria-invalid={!!error()}
                    aria-describedby={error() ? "signin-error" : undefined}
                    class="h-12 min-w-0 flex-1 bg-transparent text-[18px] outline-none placeholder:text-muted focus-visible:shadow-none focus-visible:outline-none"
                  />
                </Show>
                <button type="submit" class={button({ size: "lg" })} disabled={busy()}>
                  {step() === "email" ? "Continue" : "Sign in"}
                </button>
              </div>
              <ol class="mt-3 flex justify-between text-[14.5px] text-muted" aria-label="Steps">
                <For each={["Email", "Password or sign-in link", "Your organisation"]}>
                  {(s, i) => (
                    <li aria-current={stepNo() === i() + 1 ? "step" : undefined} classList={{ "text-ink font-[650]": stepNo() === i() + 1 }}>
                      <b>{i() + 1}</b> {s}
                    </li>
                  )}
                </For>
              </ol>
              <Show when={error()}>
                <p id="signin-error" role="alert" class="mt-4 rounded-[var(--radius-box)] border-[1.5px] border-dashed border-ink bg-paper-2 px-4 py-3 text-[15.5px]">
                  {error()}
                </p>
              </Show>
              <Show when={step() === "password"}>
                <p class="mt-4 text-center text-[15px] text-ink-2">
                  <button type="button" class="underline underline-offset-4" onClick={() => setStep("email")}>
                    Use a different email
                  </button>
                </p>
              </Show>
            </form>
            <p class="mx-auto mt-8 max-w-[600px] text-[15.5px] leading-[1.6] text-ink-2">
              Prefer no password?{" "}
              <button type="button" class="font-[700] text-ink underline underline-offset-4" onClick={() => setLinkSent(true)}>
                Email me a sign-in link
              </button>
              . Sessions end after 30 minutes idle and 12 hours at most, and every sign-in is recorded in your organisation's activity record.
            </p>
            <Show when={linkSent()}>
              <p role="status" class="mt-2 text-[14.5px] text-muted">
                If that address has an account, a sign-in link is on its way. It works once, for 15 minutes.
              </p>
            </Show>
          </Match>
          <Match when={step() === "org"}>
            <section class="mx-auto mt-8 max-w-[640px] text-left" aria-labelledby="org-h">
              <h2 id="org-h" class="text-[18px] font-[750]">
                3 · Which organisation are you working in?
              </h2>
              <ul class="mt-3 border-t border-rule">
                <For each={me()?.orgs ?? []}>
                  {(o) => (
                    <li class="border-b border-rule">
                      <button type="button" class="flex w-full items-center justify-between gap-4 py-3 text-left hover:bg-paper-2" onClick={() => void chooseOrg(o.id)}>
                        <span>
                          <span class="block text-[17px] font-[700]">{o.name}</span>
                          <span class="text-[14px] text-muted">
                            {o.roleLabel}
                            {o.viaBroker ? ` · through ${o.viaBroker}` : ""}
                          </span>
                        </span>
                        <span aria-hidden="true">→</span>
                      </button>
                    </li>
                  )}
                </For>
              </ul>
            </section>
          </Match>
        </Switch>

        <Show when={session()?.demoSignIn && session()!.demoPeople.length && step() !== "org"}>
          <section class="mx-auto mt-14 max-w-[720px] border-t-[1.5px] border-ink pt-5 text-left" aria-labelledby="demo-h">
            <h2 id="demo-h" class="text-[15px] font-[750]">
              Sample organisation: sign in as one of its people
            </h2>
            <p class="mt-1 text-[14.5px] text-muted">Each role sees what its job needs. The data is a labelled sample.</p>
            <ul class="mt-3 grid grid-cols-2 gap-x-6 max-sm:grid-cols-1">
              <For each={session()!.demoPeople}>
                {(p) => (
                  <li class="border-b border-rule">
                    <button type="button" disabled={busy()} class="flex w-full items-baseline justify-between gap-3 py-3 text-left hover:bg-paper-2" onClick={() => void demo(p.role)}>
                      <span>
                        <span class="block text-[16.5px] font-[700]">{p.fullName}</span>
                        <span class="block text-[14px] text-ink-2">
                          {p.roleLabel} · {p.orgName}
                        </span>
                      </span>
                      <span class="text-[14px] font-[650] text-muted">Sign in →</span>
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
