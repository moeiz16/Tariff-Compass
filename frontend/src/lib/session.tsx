/**
 * The signed-in session: who you are, which organisation you are working in and what your role lets you do.
 * `membership.permissions` from the API is the only source of truth; screens hide actions the role lacks and
 * never send requests it would refuse.
 */
import { useLocation, useNavigate } from "@solidjs/router";
import { createContext, createResource, onCleanup, onMount, useContext, type ParentProps, type Resource } from "solid-js";
import { setUnauthorizedHandler } from "./api";
import { syncFromHeader } from "./clock";
import { auth } from "./endpoints";
import type { Me, Role, SessionOut } from "./types";

interface SessionCtx {
  session: Resource<SessionOut>;
  me: () => Me | null;
  role: () => Role | null;
  can: (permission: string) => boolean;
  reload: () => Promise<unknown>;
  signOut: () => Promise<void>;
}

const Ctx = createContext<SessionCtx>();

export function SessionProvider(props: ParentProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [session, { refetch, mutate }] = createResource(async () => {
    const s = await auth.session();
    syncFromHeader(s.clock.now);
    return s;
  });

  const me = () => session()?.me ?? null;
  const can = (permission: string) => !!me()?.membership?.permissions.includes(permission);

  setUnauthorizedHandler((code) => {
    if (code !== "session_expired" && code !== "not_authenticated") return;
    mutate((s) => (s ? { ...s, me: null } : s));
    if (location.pathname !== "/signin") {
      navigate(`/signin?next=${encodeURIComponent(location.pathname + location.search)}&ended=1`, { replace: true });
    }
  });

  // Keep an active session alive: refresh at most every five minutes while the person is using the page.
  let active = false;
  const mark = () => (active = true);
  onMount(() => {
    for (const ev of ["keydown", "pointerdown"]) window.addEventListener(ev, mark, { passive: true });
    const timer = setInterval(() => {
      if (active && me()) void auth.refresh().catch(() => undefined);
      active = false;
    }, 5 * 60_000);
    onCleanup(() => {
      clearInterval(timer);
      for (const ev of ["keydown", "pointerdown"]) window.removeEventListener(ev, mark);
    });
  });
  onCleanup(() => setUnauthorizedHandler(null));

  const value: SessionCtx = {
    session,
    me,
    role: () => me()?.membership?.role ?? null,
    can,
    reload: () => refetch() as Promise<unknown>,
    signOut: async () => {
      await auth.logout().catch(() => undefined);
      mutate((s) => (s ? { ...s, me: null } : s));
      navigate("/", { replace: true });
    },
  };
  return <Ctx.Provider value={value}>{props.children}</Ctx.Provider>;
}

export function useSession(): SessionCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useSession outside SessionProvider");
  return ctx;
}

/** Pure check used by components and tests: does this permission list allow the action? */
export function allows(permissions: readonly string[] | undefined | null, permission: string): boolean {
  return !!permissions?.includes(permission);
}

/** The scopes each permission opens in the query strip. */
export const SCOPE_PERMISSION: Record<string, string> = {
  answer: "classify:read",
  rulings: "rulings:read",
  tariff: "tariff:read",
  products: "products:read",
  review: "review:read",
  watch: "watch:read",
  lab: "lab:read",
};
