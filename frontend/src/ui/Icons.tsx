/** Small line icons. Every status icon is paired with a word wherever it appears. */
import type { JSX } from "solid-js";

type P = { class?: string; size?: number; title?: string };
const svg = (p: P, viewBox: string, children: JSX.Element, extra: JSX.SvgSVGAttributes<SVGSVGElement> = {}) => (
  <svg
    viewBox={viewBox}
    width={p.size ?? 16}
    height={p.size ?? 16}
    class={p.class}
    aria-hidden={p.title ? undefined : "true"}
    role={p.title ? "img" : undefined}
    fill="none"
    stroke="currentColor"
    {...extra}
  >
    {p.title ? <title>{p.title}</title> : null}
    {children}
  </svg>
);

export const SearchIcon = (p: P) =>
  svg(p, "0 0 20 20", <><circle cx="8.5" cy="8.5" r="6" stroke-width="2" /><path d="M13 13l5 5" stroke-width="2" stroke-linecap="round" /></>);
export const OkIcon = (p: P) =>
  svg(p, "0 0 20 20", <><circle cx="10" cy="10" r="8.2" stroke-width="2" /><path d="M6 10.2l2.6 2.6L14.2 7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" /></>);
export const AskIcon = (p: P) =>
  svg(p, "0 0 20 20", <><path d="M10 1.8l8.2 8.2-8.2 8.2L1.8 10z" stroke-width="2" stroke-linejoin="round" /><path d="M8 7.8a2.1 2.1 0 1 1 2.8 2c-.6.3-.8.6-.8 1.2v.5" stroke-width="2" stroke-linecap="round" /><circle cx="10" cy="14" r=".6" fill="currentColor" /></>);
export const WarnIcon = (p: P) =>
  svg(p, "0 0 20 20", <><path d="M10 2.5l8 14.5H2z" stroke-width="2" stroke-linejoin="round" /><path d="M10 8v4" stroke-width="2" stroke-linecap="round" /><circle cx="10" cy="14.6" r=".6" fill="currentColor" /></>);
export const InForceIcon = (p: P) => svg(p, "0 0 12 12", <circle cx="6" cy="6" r="5" fill="currentColor" stroke="none" />);
export const ModifiedIcon = (p: P) =>
  svg(p, "0 0 12 12", <><circle cx="6" cy="6" r="4.6" stroke-width="1.6" /><path d="M6 1.4a4.6 4.6 0 0 1 0 9.2z" fill="currentColor" stroke="none" /></>);
export const RevokedIcon = (p: P) => svg(p, "0 0 12 12", <><circle cx="6" cy="6" r="4.6" stroke-width="1.6" /><path d="M2.8 9.2l6.4-6.4" stroke-width="1.6" /></>);
export const ContrastIcon = (p: P) => svg(p, "0 0 12 12", <circle cx="6" cy="6" r="4.6" stroke-width="1.6" stroke-dasharray="2 1.6" />);
export const SameIcon = (p: P) => svg(p, "0 0 12 12", <path d="M2 6.3l2.6 2.5L10 3.4" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />);
export const CloseIcon = (p: P) => svg(p, "0 0 12 12", <path d="M3 3l6 6M9 3l-6 6" stroke-width="1.8" stroke-linecap="round" />);
export const ApproxIcon = (p: P) => svg(p, "0 0 12 12", <path d="M2 4.6c1.3-1.2 2.7-1.2 4 0s2.7 1.2 4 0M2 8c1.3-1.2 2.7-1.2 4 0s2.7 1.2 4 0" stroke-width="1.5" stroke-linecap="round" />);
export const MoonIcon = (p: P) => svg(p, "0 0 20 20", <path d="M16 12.5A7 7 0 0 1 7.5 4a7 7 0 1 0 8.5 8.5z" stroke-width="1.8" stroke-linejoin="round" />);
export const SunIcon = (p: P) =>
  svg(p, "0 0 20 20", <><circle cx="10" cy="10" r="3.6" stroke-width="1.8" /><path d="M10 1.8v2.2M10 16v2.2M1.8 10h2.2M16 10h2.2M4.2 4.2l1.6 1.6M14.2 14.2l1.6 1.6M4.2 15.8l1.6-1.6M14.2 5.8l1.6-1.6" stroke-width="1.6" stroke-linecap="round" /></>);
export const ChevronIcon = (p: P) => svg(p, "0 0 16 16", <path d="M4 6l4 4 4-4" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />);
export const PassIcon = (p: P) => svg(p, "0 0 16 16", <path d="M3 8.4l3.2 3.1L13 4.6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />);
export const FailIcon = (p: P) => svg(p, "0 0 16 16", <path d="M4 4l8 8M12 4l-8 8" stroke-width="2" stroke-linecap="round" />);
export const PaperclipIcon = (p: P) =>
  svg(p, "0 0 20 20", <path d="M14.5 9.5l-5.3 5.3a3.2 3.2 0 0 1-4.5-4.5l6-6a2.1 2.1 0 0 1 3 3l-6 6a1 1 0 0 1-1.5-1.5l5.3-5.3" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />);
export const MailIcon = (p: P) => svg(p, "0 0 20 20", <><rect x="2.5" y="4.5" width="15" height="11" rx="1.5" stroke-width="1.6" /><path d="M3 5.5l7 5.2 7-5.2" stroke-width="1.6" stroke-linejoin="round" /></>);
