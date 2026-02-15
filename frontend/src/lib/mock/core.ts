/** Mock platform data: the sample organisations, people, roles, meta and settings (docs/DATA.md seed plan). */
import type { DemoPerson, Me, MemberOut, MetaOut, Role, RoleOut, UserOut } from "../types";

export const DEMO_NOW = "2026-02-19T18:30:00Z"; // Thu 19 Feb 2026, 10:30 a.m. Pacific

export const ROLE_LABELS: Record<Role, string> = {
  importer: "Importer",
  broker: "Licensed customs broker",
  compliance: "Compliance lead",
  admin: "Administrator",
};

const READ = ["classify:read", "rulings:read", "tariff:read", "products:read", "review:read", "watch:read", "settings:read"];
export const ROLE_PERMISSIONS: Record<Role, string[]> = {
  importer: [...READ, "classify:run", "products:write", "binder:export", "review:submit", "review:answer"],
  broker: [...READ, "classify:run", "binder:export", "review:decide", "rules:manage", "lab:read", "lab:sign"],
  compliance: [
    ...READ,
    "classify:run",
    "products:write",
    "binder:export",
    "review:submit",
    "review:answer",
    "rules:manage",
    "watch:manage",
    "lab:read",
    "lab:run",
    "lab:sign",
    "settings:manage",
    "audit:read",
  ],
  admin: [...READ, "lab:read", "settings:manage", "members:manage", "audit:read", "org:admin"],
};

export const ROLE_DESCRIPTIONS: Record<Role, string> = {
  importer: "Classifies products, keeps binders and answers the broker's questions.",
  broker: "Reviews, approves and corrects codes, and co-signs new training rounds.",
  compliance: "Owns the reasonable-care record, the always-review rules and the training rounds.",
  admin: "Manages people, roles and organisation settings.",
};

interface Person {
  id: string;
  fullName: string;
  email: string;
  role: Role;
  title: string;
  licence: string;
  via: string | null;
  color: string;
  joined: string;
}

export const PEOPLE: Person[] = [
  { id: "u-maya", fullName: "Maya Lindqvist", email: "maya.lindqvist@northbound.example", role: "compliance", title: "Compliance lead", licence: "", via: null, color: "#111111", joined: "2025-09-02T16:00:00Z" },
  { id: "u-jordan", fullName: "Jordan Tse", email: "jordan.tse@northbound.example", role: "importer", title: "Imports, Seattle", licence: "", via: null, color: "#3a3a36", joined: "2025-09-03T16:00:00Z" },
  { id: "u-dana", fullName: "Dana Whitlock", email: "dana.whitlock@driftwood.example", role: "broker", title: "Licensed customs broker, US entries", licence: "Sample licence US-0001", via: "Driftwood Customs Brokers", color: "#5a5a54", joined: "2025-09-10T16:00:00Z" },
  { id: "u-rafael", fullName: "Rafael Ouellet", email: "rafael.ouellet@driftwood.example", role: "broker", title: "Licensed customs broker, Canadian entries", licence: "Sample licence CA-0001", via: "Driftwood Customs Brokers", color: "#5a5a54", joined: "2025-09-10T16:00:00Z" },
  { id: "u-priscilla", fullName: "Priscilla Mensah", email: "priscilla.mensah@northbound.example", role: "admin", title: "Operations and administration", licence: "", via: null, color: "#62625b", joined: "2025-09-01T16:00:00Z" },
];

export const DEMO_BY_ROLE: Record<Role, string> = { importer: "u-jordan", broker: "u-dana", compliance: "u-maya", admin: "u-priscilla" };

export const DEMO_PEOPLE: DemoPerson[] = (["importer", "broker", "compliance", "admin"] as Role[]).map((role) => {
  const p = PEOPLE.find((x) => x.id === DEMO_BY_ROLE[role])!;
  return { role, roleLabel: ROLE_LABELS[role], fullName: p.fullName, title: p.title, orgName: p.via ?? "Northbound Goods Co." };
});

export function userOut(p: Person): UserOut {
  return { id: p.id, email: p.email, fullName: p.fullName, licence: p.licence, avatarColor: p.color };
}

export const NORTHBOUND = {
  id: "org-northbound",
  name: "Northbound Goods Co.",
  slug: "northbound",
  kind: "importer" as const,
  kindLabel: "Importer",
  locations: ["Vancouver, BC", "Seattle, WA"],
  timezone: "America/Vancouver",
  isSample: true,
};

export function meFor(role: Role): Me {
  const p = PEOPLE.find((x) => x.id === DEMO_BY_ROLE[role])!;
  return {
    user: userOut(p),
    activeOrg: NORTHBOUND,
    membership: { role, roleLabel: ROLE_LABELS[role], title: p.title, permissions: ROLE_PERMISSIONS[role] },
    orgs: [
      { id: NORTHBOUND.id, name: NORTHBOUND.name, kind: "importer", role, roleLabel: ROLE_LABELS[role], viaBroker: p.via, isSample: true },
    ],
    session: { expiresAt: "2026-02-19T19:00:00Z", absoluteExpiresAt: "2026-02-20T06:30:00Z" },
  };
}

export const MEMBERS: MemberOut[] = PEOPLE.map((p) => ({
  id: `m-${p.id}`,
  user: userOut(p),
  role: p.role,
  roleLabel: ROLE_LABELS[p.role],
  title: p.title,
  viaBroker: p.via,
  joinedAt: p.joined,
}));

export const ROLES: RoleOut[] = (Object.keys(ROLE_LABELS) as Role[]).map((role) => ({
  role,
  roleLabel: ROLE_LABELS[role],
  description: ROLE_DESCRIPTIONS[role],
  permissions: ROLE_PERMISSIONS[role],
}));

export const LABELS: Record<string, Record<string, string>> = {
  countries: { US: "United States", CA: "Canada" },
  verdicts: { strong: "Strong match", broker: "Needs a broker" },
  factSources: { stated: "Stated", read: "Read from the text", assumed: "Assumed", unknown: "Not stated" },
  rulingStatuses: { in_force: "In force", modified: "Modified", revoked: "Revoked", contrast: "Cited for contrast" },
  transport: { ocean: "Ocean freight", air: "Air freight", truck: "Truck", rail: "Rail", courier: "Courier" },
  categories: { outdoor: "Outdoor gear", electronics: "Small electronics", apparel: "Apparel", kitchen: "Kitchenware", bags: "Bags", other: "Other" },
  standings: { proposed: "Proposed", in_review: "With the broker", approved: "Approved", needs_recheck: "Needs a re-check", withdrawn: "Withdrawn" },
  reviewKinds: { unsure: "Classifier unsure", differs: "Differs from last code", ruling_changed: "Ruling changed", always_review: "Always reviewed", requested: "Sent for review" },
  reasonKinds: { facts_differ: "The product facts differ", ruling_elsewhere: "A ruling points elsewhere", heading_misread: "A heading was read wrongly", other: "Something else" },
  changeKinds: { legal_pending: "Pending decision", duty_layer: "Duty change", ruling_modified: "Ruling modified", ruling_revoked: "Ruling revoked", new_rulings: "New rulings", schedule_revision: "Tariff revision" },
  roundStatuses: { training: "Training", waiting_signoff: "Waiting for sign-off", live: "Live", not_made_live: "Not made live", retired: "Retired", failed: "Didn't finish" },
  jobStatuses: { queued: "Waiting to start", running: "Working", succeeded: "Done", failed: "Didn't finish" },
};

export const META: Omit<MetaOut, "clock"> = {
  product: "Tariff Compass",
  version: "0.1.0",
  snapshot: {
    usHts: "HTSUS 2026 Revision 3",
    usHtsInForce: ["2026-02-12", null],
    caTariff: "Customs Tariff T2026",
    caTariffFrom: "2026-01-01",
    dutyLayersAsOf: "2026-02-19",
    rulingsCount: 214,
    rulingsNewest: "2025-07-30",
    label: "Tariffs as of Thu 19 Feb 2026",
  },
  scopes: [
    { key: "answer", label: "Answer" },
    { key: "rulings", label: "Rulings" },
    { key: "tariff", label: "Tariff text" },
    { key: "products", label: "My products" },
    { key: "review", label: "Review" },
    { key: "watch", label: "Watch" },
    { key: "lab", label: "Lab" },
  ],
  labels: LABELS,
  origins: [
    { key: "CN", label: "China" },
    { key: "VN", label: "Vietnam" },
    { key: "MX", label: "Mexico" },
    { key: "DE", label: "Germany" },
    { key: "IT", label: "Italy" },
    { key: "PT", label: "Portugal" },
  ],
};
