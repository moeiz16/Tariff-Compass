/** One typed function per endpoint the web app calls (docs/API_CONTRACT.md Part 1). */
import { api, del, get, patch, post, qs } from "./api";
import type {
  AnswerOut,
  AnswerSummary,
  AuditRow,
  BinderOut,
  BinderVersion,
  ChainOut,
  ClassifyIn,
  CompareOut,
  ConfirmedFact,
  Country,
  DecisionOut,
  DecisionRecord,
  DocketFilter,
  DocketOut,
  EngagementOut,
  EvidenceOut,
  HomeOut,
  InvitationOut,
  JobAccepted,
  JobOut,
  LabOut,
  LandedCostIn,
  LandedCostOut,
  LessonOut,
  Me,
  MemberOut,
  MetaOut,
  OrgSettingsOut,
  Page,
  ProductDetail,
  ProductSummary,
  ReasonKind,
  ReviewRow,
  Role,
  RoleOut,
  RoundOut,
  RuleOut,
  RulingDetail,
  RulingSummary,
  SampleOut,
  ScopeCounts,
  SectionOut,
  SessionOut,
  TariffLineOut,
  TariffOutline,
  WatchItemOut,
  WatchOut,
} from "./types";

const enc = encodeURIComponent;

export const auth = {
  csrf: () => api<void>("/auth/csrf"),
  session: () => get<SessionOut>("/auth/session"),
  login: (email: string, password: string) => post<Me>("/auth/login", { email, password }),
  demo: (role: Role) => post<Me>("/auth/demo", { role }),
  logout: () => post<void>("/auth/logout"),
  refresh: () => post<{ expiresAt: string; absoluteExpiresAt: string }>("/auth/refresh"),
  switchOrg: (orgId: string) => post<Me>("/auth/switch-org", { orgId }),
};

export const meta = {
  get: () => get<MetaOut>("/meta"),
  home: () => get<HomeOut>("/home"),
  counts: (q = "") => get<ScopeCounts>(`/scopes/counts${qs({ q })}`),
  sections: () => get<SectionOut[]>("/tariff/sections"),
};

export const publicApi = {
  samples: () => get<SampleOut[]>("/public/samples"),
  sample: (key: string) => get<AnswerOut>(`/public/samples/${enc(key)}`),
  classify: (text: string) => post<AnswerOut>("/public/classify", { text }),
};

export const answers = {
  classify: (body: ClassifyIn) => post<AnswerOut>("/classify", body),
  get: (id: string) => get<AnswerOut>(`/answers/${enc(id)}`),
  mine: (page = 1) => get<Page<AnswerSummary>>(`/answers${qs({ mine: true, page })}`),
  confirmFact: (id: string, fact: ConfirmedFact) => post<AnswerOut>(`/answers/${enc(id)}/facts`, fact),
  save: (id: string, productId?: string) => post<BinderVersion>(`/answers/${enc(id)}/save`, productId ? { productId } : {}),
  sendToBroker: (id: string, note: string) => post<ReviewRow>(`/answers/${enc(id)}/send-to-broker`, { note }),
  citationFeedback: (id: string, n: number, reason: string) =>
    post<void>(`/answers/${enc(id)}/citations/${n}/feedback`, { reason }),
  uploadEvidence: (file: File, kind?: string) => {
    const form = new FormData();
    form.set("file", file);
    if (kind) form.set("kind", kind);
    return post<EvidenceOut>("/evidence", form);
  },
  landedCost: (body: LandedCostIn) => post<LandedCostOut>("/landed-cost", body),
};

export const rulings = {
  search: (p: { q?: string; heading?: string; status?: string; sort?: string; page?: number; pageSize?: number }) =>
    get<Page<RulingSummary>>(`/rulings${qs(p)}`),
  get: (key: string) => get<RulingDetail>(`/rulings/${enc(key)}`),
  compare: (key: string, answerId: string, n?: number) => get<CompareOut>(`/rulings/${enc(key)}/compare${qs({ answerId, n })}`),
};

export const tariff = {
  search: (country: Country, q: string, under?: string) => get<TariffLineOut[]>(`/tariff/${country}/search${qs({ q, under })}`),
  line: (country: Country, code: string) => get<TariffOutline>(`/tariff/${country}/lines/${enc(code)}`),
};

export const products = {
  list: (p: { q?: string; category?: string; standing?: string; page?: number; pageSize?: number; sort?: string }) =>
    get<Page<ProductSummary>>(`/products${qs(p)}`),
  get: (sku: string) => get<ProductDetail>(`/products/${enc(sku)}`),
  binder: (sku: string) => get<BinderOut>(`/products/${enc(sku)}/binder`),
  exportBinder: (sku: string, format: "pdf" | "zip") => post<JobAccepted>(`/products/${enc(sku)}/binder/export`, { format }),
};

export const review = {
  docket: (p: { filter?: DocketFilter; q?: string; sort?: string; page?: number }) => get<DocketOut>(`/review${qs(p)}`),
  get: (id: string) => get<DecisionRecord>(`/review/${enc(id)}`),
  lesson: (id: string, body: { usCode?: string; caCode?: string; reasonKind: ReasonKind; reason: string }) =>
    post<LessonOut>(`/review/${enc(id)}/lesson`, body),
  approve: (id: string, note = "") => post<DecisionOut>(`/review/${enc(id)}/approve`, { note }),
  correct: (
    id: string,
    body: { usCode?: string; caCode?: string; reasonKind: ReasonKind; reason: string; rulingRelied?: string; alsoChangeCa: boolean },
  ) => post<DecisionOut>(`/review/${enc(id)}/correct`, body),
  ask: (id: string, question: string, options: string[]) => post<DecisionOut>(`/review/${enc(id)}/ask`, { question, options }),
  answer: (id: string, answer: string) => post<DecisionOut>(`/review/${enc(id)}/answer`, { answer }),
};

export const rules = {
  list: () => get<RuleOut[]>("/rules"),
  create: (body: { kind: string; value: string; label: string }) => post<RuleOut>("/rules", body),
  update: (id: string, body: { active?: boolean; label?: string }) => patch<RuleOut>(`/rules/${enc(id)}`, body),
  remove: (id: string) => del(`/rules/${enc(id)}`),
};

export const watch = {
  list: (p: { q?: string; kind?: string }) => get<WatchOut>(`/watch${qs(p)}`),
  get: (id: string) => get<WatchItemOut>(`/watch/${enc(id)}`),
  scan: () => post<JobAccepted>("/watch/scan"),
};

export const lab = {
  get: () => get<LabOut>("/lab"),
  round: (n: number) => get<RoundOut>(`/lab/rounds/${n}`),
  start: (note: string) => post<JobAccepted>("/lab/rounds", { note }),
  sign: (n: number, statement: string) => post<RoundOut>(`/lab/rounds/${n}/sign`, { statement }),
};

export const org = {
  settings: () => get<OrgSettingsOut>("/settings"),
  updateSettings: (body: Partial<Pick<OrgSettingsOut, "into" | "madeIn" | "ports" | "alwaysSendToBroker">>) =>
    patch<OrgSettingsOut>("/settings", body),
  members: () => get<MemberOut[]>("/org/members"),
  updateMember: (id: string, body: { role?: Role; title?: string }) => patch<MemberOut>(`/org/members/${enc(id)}`, body),
  removeMember: (id: string) => del(`/org/members/${enc(id)}`),
  invitations: () => get<InvitationOut[]>("/org/invitations"),
  invite: (email: string, role: Role) => post<InvitationOut>("/org/invitations", { email, role }),
  revokeInvitation: (id: string) => del(`/org/invitations/${enc(id)}`),
  roles: () => get<RoleOut[]>("/roles"),
  brokers: () => get<EngagementOut[]>("/org/brokers"),
};

export const audit = {
  list: (p: { page?: number; pageSize?: number; action?: string; actor?: string; from?: string; to?: string }) =>
    get<Page<AuditRow>>(`/audit${qs(p)}`),
  verify: () => get<ChainOut>("/audit/verify"),
  csvPath: (p: { action?: string; actor?: string; from?: string; to?: string }) => `/audit/export.csv${qs(p)}`,
};

export const jobs = {
  get: (id: string) => get<JobOut>(`/jobs/${enc(id)}`),
};

/** Poll a job once a second until it finishes (the SSE stream is optional; polling is the contract's fallback). */
export async function waitForJob(id: string, onProgress: (j: JobOut) => void, signal?: AbortSignal): Promise<JobOut> {
  for (;;) {
    if (signal?.aborted) throw new DOMException("aborted", "AbortError");
    const job = await jobs.get(id);
    onProgress(job);
    if (job.status === "succeeded" || job.status === "failed") return job;
    await new Promise((r) => setTimeout(r, 1000));
  }
}
