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
export const MenuIcon = (p: P) => svg(p, "0 0 20 20", <path d="M3.5 6h13M3.5 10h13M3.5 14h13" stroke-width="1.7" stroke-linecap="round" />);
export const ArrowRightIcon = (p: P) => svg(p, "0 0 16 16", <path d="M3 8h10M9 4l4 4-4 4" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />);
export const InfoIcon = (p: P) =>
  svg(p, "0 0 20 20", <><circle cx="10" cy="10" r="7.6" stroke-width="1.6" /><path d="M10 9v4.6" stroke-width="1.7" stroke-linecap="round" /><circle cx="10" cy="6.4" r=".9" fill="currentColor" stroke="none" /></>);
export const CopyIcon = (p: P) =>
  svg(p, "0 0 20 20", <><rect x="6.5" y="6.5" width="10" height="10" rx="2" stroke-width="1.6" /><path d="M13.5 6.5V5a1.5 1.5 0 0 0-1.5-1.5H5A1.5 1.5 0 0 0 3.5 5v7A1.5 1.5 0 0 0 5 13.5h1.5" stroke-width="1.6" /></>);
export const DocIcon = (p: P) =>
  svg(p, "0 0 20 20", <><path d="M5 2.8h6.5L15.5 7v10.2H5z" stroke-width="1.6" stroke-linejoin="round" /><path d="M11.2 2.8V7h4.3M7.6 10.5h5M7.6 13.5h5" stroke-width="1.5" stroke-linecap="round" /></>);
export const StackIcon = (p: P) =>
  svg(p, "0 0 20 20", <><rect x="2.8" y="12.5" width="14.4" height="4" rx="1" stroke-width="1.6" /><rect x="2.8" y="7.5" width="10" height="4" rx="1" stroke-width="1.6" /><rect x="2.8" y="2.5" width="6" height="4" rx="1" stroke-width="1.6" /></>);
export const UserCheckIcon = (p: P) =>
  svg(p, "0 0 20 20", <><circle cx="8" cy="6.5" r="3.2" stroke-width="1.6" /><path d="M2.5 16.5c.6-3 2.8-4.6 5.5-4.6 1.3 0 2.4.3 3.3 1" stroke-width="1.6" stroke-linecap="round" /><path d="M12.5 14.6l1.8 1.8 3.4-3.6" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" /></>);
export const PathIcon = (p: P) =>
  svg(p, "0 0 20 20", <><circle cx="5" cy="4.5" r="1.8" stroke-width="1.5" /><circle cx="15" cy="15.5" r="1.8" stroke-width="1.5" /><path d="M5 6.3v3.2a2 2 0 0 0 2 2h6a2 2 0 0 1 2 2v.2" stroke-width="1.5" stroke-linecap="round" /></>);
export const ListIcon = (p: P) => svg(p, "0 0 20 20", <path d="M7 5.5h10M7 10h10M7 14.5h10M3.5 5.5h.01M3.5 10h.01M3.5 14.5h.01" stroke-width="1.8" stroke-linecap="round" />);
export const ScaleIcon = (p: P) =>
  svg(p, "0 0 20 20", <><path d="M10 3v14M5.5 17h9M4 6.5h12" stroke-width="1.6" stroke-linecap="round" /><path d="M4 6.5L2 11a2.2 2.2 0 0 0 4 0zM16 6.5L14 11a2.2 2.2 0 0 0 4 0z" stroke-width="1.4" stroke-linejoin="round" /></>);
export const ExternalIcon = (p: P) => svg(p, "0 0 16 16", <path d="M9.5 2.5h4v4M13.5 2.5L8 8M6.5 3.5h-3v9h9v-3" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />);
