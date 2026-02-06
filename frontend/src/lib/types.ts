/**
 * Wire shapes of /api/v1 (docs/API_CONTRACT.md Part 1, backend/tariffcompass/api/schemas). camelCase on the
 * wire. Dates are ISO strings; money is a decimal string with a currency, never a float.
 */

export type Country = "US" | "CA";
export type Role = "importer" | "broker" | "compliance" | "admin";

export interface Money {
  amount: string;
  currency: "USD" | "CAD";
}
export interface Span {
  start: number;
  end: number;
}
export interface Page<T> {
  items: T[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}
export interface Labelled {
  key: string;
  label: string;
}
export interface Clock {
  now: string;
  today: string;
  timezone: string;
  demo: boolean;
  demoToday?: string | null;
  demoTime?: string | null;
}
export interface CodeOut {
  country: Country;
  countryLabel: string;
  code: string;
  digits: string;
  headingDigits: string;
  text: string;
  headingText: string;
  leaning: boolean;
}
export interface PersonRef {
  id: string;
  fullName: string;
  role: string;
  roleLabel: string;
  licence: string;
}

/* ---------- auth / platform ---------- */
export interface UserOut {
  id: string;
  email: string;
  fullName: string;
  licence: string;
  avatarColor: string;
}
export interface OrgOut {
  id: string;
  name: string;
  slug: string;
  kind: "importer" | "broker";
  kindLabel: string;
  locations: string[];
  timezone: string;
  isSample: boolean;
}
export interface OrgSummary {
  id: string;
  name: string;
  kind: "importer" | "broker";
  role: Role;
  roleLabel: string;
  viaBroker: string | null;
  isSample: boolean;
}
export interface MembershipOut {
  role: Role;
  roleLabel: string;
  title: string;
  permissions: string[];
}
export interface Me {
  user: UserOut;
  activeOrg: OrgOut | null;
  membership: MembershipOut | null;
  orgs: OrgSummary[];
  session: { expiresAt: string; absoluteExpiresAt: string };
}
export interface DemoPerson {
  role: Role;
  roleLabel: string;
  fullName: string;
  title: string;
  orgName: string;
}
export interface SessionOut {
  me: Me | null;
  clock: Clock;
  demoSignIn: boolean;
  demoPeople: DemoPerson[];
}
export interface MemberOut {
  id: string;
  user: UserOut;
  role: Role;
  roleLabel: string;
  title: string;
  viaBroker: string | null;
  joinedAt: string;
}
export interface InvitationOut {
  id: string;
  email: string;
  role: Role;
  roleLabel: string;
  expiresAt: string;
  invitedBy: string;
  link?: string | null;
}
export interface RoleOut {
  role: Role;
  roleLabel: string;
  description: string;
  permissions: string[];
}
export interface EngagementOut {
  id: string;
  brokerOrg: string;
  importerOrg: string;
  countries: Country[];
  countriesLabel: string;
  startedOn: string;
  people: MemberOut[];
}

/* ---------- meta / home ---------- */
export interface SnapshotOut {
  usHts: string;
  usHtsInForce: [string, string];
  caTariff: string;
  caTariffFrom: string;
  dutyLayersAsOf: string;
  rulingsCount: number;
  rulingsNewest: string | null;
  label: string;
}
export interface MetaOut {
  product: string;
  version: string;
  clock: Clock;
  snapshot: SnapshotOut;
  scopes: Labelled[];
  labels: Record<string, Record<string, string>>;
  origins: Labelled[];
}
export interface ScopeCounts {
  rulings: number;
  products: number;
  review: number;
  watch: number;
}
export interface RecentAnswer {
  id: string;
  queryText: string;
  usCode: string | null;
  verdict: Verdict;
  verdictLabel: string;
  createdAt: string;
  createdBy: string;
}
export interface HomeChange {
  id: string;
  headline: string;
  affectedCount: number;
  consequence: string;
}
export interface HomeOut {
  dateLine: string;
  recent: RecentAnswer[];
  changes: HomeChange[];
}

/* ---------- classify / answers ---------- */
export type Verdict = "strong" | "broker";
export type FactSource = "stated" | "read" | "assumed" | "unknown";
export type RulingStatusKind = "in_force" | "modified" | "revoked" | "contrast";
export type MatchWord = "same" | "close" | "differs";
export type Transport = "ocean" | "air" | "truck" | "rail" | "courier";

export interface ConfirmedFact {
  key: string;
  answer: string;
}
export interface ShipmentIn {
  value: Money;
  quantity: number;
  transport: Transport;
}
export interface ClassifyIn {
  text: string;
  madeIn: string;
  into: Country[];
  productId?: string | null;
  evidenceIds: string[];
  confirmedFacts: ConfirmedFact[];
  shipment?: ShipmentIn | null;
}
export interface EvidenceOut {
  id: string;
  kind: "spec_sheet" | "photo" | "listing" | "supplier_email" | "other";
  kindLabel: string;
  fileName: string;
  pages?: number | null;
  extractedText: string;
  photoFacts: string[];
  certain: boolean;
  sha256: string;
  uploadedBy: string;
  uploadedAt: string;
}
export interface VerdictOut {
  word: Verdict;
  wordLabel: string;
  sentence: string;
  agreeing: number;
  cited: number;
  inForce: number;
  agreementBar: { n: number; kind: "same" | "contrast" | "differs" }[];
}
export interface AlternativeOut {
  code: CodeOut;
  condition: string;
  dutyAtStake?: string | null;
}
export interface DecidingQuestionOut {
  factKey: string;
  question: string;
  options: { key: string; label: string; leadsTo?: string | null }[];
  notSureLabel: string;
}
export interface FactOut {
  key: string;
  label: string;
  value: string;
  source: FactSource;
  sourceLabel: string;
  sourceNote: string;
  decides: boolean;
}
export interface ClaimOut {
  text: string;
  cites: number[];
  marked: Span[];
}
export interface NotNeighbourOut {
  code: string;
  text: string;
  reason: string;
  cite?: number | null;
}
export interface PathStepOut {
  level: string;
  levelLabel: string;
  code: string;
  text: string;
  gri: string;
  griLabel: string;
  why: string;
  cites: number[];
  notNeighbours: NotNeighbourOut[];
  countryNote?: string | null;
}
export interface RulingStatusOut {
  kind: RulingStatusKind;
  kindLabel: string;
  text: string;
  byId?: string | null;
  date?: string | null;
}
export interface FactCompareOut {
  fact: string;
  yours: string;
  theirs: string;
  match: MatchWord;
  matchLabel: string;
}
export interface CitedRulingOut {
  n: number;
  id: string;
  key: string;
  date: string;
  subject: string;
  status: RulingStatusOut;
  holding: string;
  markedSpans: Span[];
  match: ("same_heading" | "same_subheading" | "different_heading")[];
  matchLabels: string[];
  factCompare: FactCompareOut[];
  supports: number[];
  url: string;
}
export interface AnswerOut {
  id: string;
  query: ClassifyIn;
  madeInLabel: string;
  createdAt: string;
  createdBy: string | null;
  tariffsAsOf: string;
  snapshotLabel: string;
  sample: boolean;
  us: CodeOut | null;
  ca: CodeOut | null;
  verdict: VerdictOut;
  alternative?: AlternativeOut | null;
  decidingQuestion?: DecidingQuestionOut | null;
  holdingSentence: string;
  issue: string;
  facts: FactOut[];
  reason: ClaimOut[];
  path: PathStepOut[];
  rulings: CitedRulingOut[];
  tariffAuthorities: { ref: string; quote: string }[];
  landed: LandedCostOut[];
  productId?: string | null;
  reviewItemId?: string | null;
  provenance: { classifierRound: number | null; firstStageVersion: string; searchVersion: string; lmLabel: string };
  timings: Record<string, number>;
}
export interface AnswerSummary {
  id: string;
  queryText: string;
  usCode: string | null;
  caCode: string | null;
  verdict: Verdict;
  verdictLabel: string;
  createdAt: string;
  createdBy: string;
}
export interface SampleOut {
  key: string;
  title: string;
  madeIn: string;
  query: string;
}

/* ---------- landed cost ---------- */
export type LayerKind = "base" | "remedy" | "emergency" | "fee" | "tax" | "surtax" | "preference";
export interface LandedCostIn {
  country: Country;
  code: string;
  madeIn: string;
  value: Money;
  quantity: number;
  transport: Transport;
  usmcaAnswers: Record<string, boolean>;
  metalContentValue?: Money | null;
}
export interface LayerLineOut {
  letter: string;
  layerId: string;
  kind: LayerKind;
  kindLabel: string;
  name: string;
  rate: string;
  amount: Money;
  plain: string;
  source: string;
  sourceUrl: string;
  chapter99?: string | null;
  effectiveFrom: string;
  effectiveTo?: string | null;
  legalStatus?: string | null;
  legalStatusOpen: boolean;
}
export interface LandedCostOut {
  country: Country;
  countryLabel: string;
  code: string;
  madeIn: string;
  madeInLabel: string;
  value: Money;
  quantity: number;
  transport: string;
  transportLabel: string;
  lines: LayerLineOut[];
  notApplied: { name: string; why: string }[];
  chargesTotal: Money;
  landedTotal: Money;
  perUnit: Money;
  effectiveRate: string;
  questions: { key: string; question: string; answer: boolean | null }[];
  whatCouldChange: { label: string; landedTotal: Money; chargesTotal: Money }[];
  tariffsAsOf: string;
  snapshotLabel: string;
}

/* ---------- rulings / tariff ---------- */
export interface RulingSummary {
  id: string;
  key: string;
  issued: string;
  subject: string;
  code: string;
  codeAsQuoted: string;
  heading: string;
  status: RulingStatusOut;
  holding: string;
  snippet: string;
  snippetMarks: Span[];
}
export interface RulingDetail extends RulingSummary {
  category: string;
  codes: string[];
  text: string;
  paragraphs: Span[];
  related: { id: string; key: string; relation: string; relationLabel: string }[];
  alsoCitedIn: { productId: string; sku: string; title: string }[];
  sourceUrl: string;
}
export interface CompareOut {
  ruling: RulingDetail;
  citedAs: number | null;
  productTitle: string;
  madeInLabel: string;
  ruleQuote: string;
  alignment: FactCompareOut[];
  evidence: { kind: string; label: string; text: string; marked: Span[] }[];
  rulingMarked: Span[];
}
export interface TariffLineOut {
  country: Country;
  code: string;
  digits: string;
  level: string;
  levelLabel: string;
  indent: number;
  text: string;
  fullText: string;
  unit: string;
  generalRate: string;
  special: string;
  hasChildren: boolean;
}
export interface TariffOutline {
  line: TariffLineOut;
  ancestors: TariffLineOut[];
  children: TariffLineOut[];
  notes: string[];
  editionLabel: string;
}
export interface SectionOut {
  section: string;
  title: string;
  chapters: { chapter: string; title: string; reserved: boolean }[];
}

/* ---------- products / binder ---------- */
export type Standing = "proposed" | "in_review" | "approved" | "needs_recheck" | "withdrawn";
export type BinderRow = "usCode" | "caCode" | "standing" | "decidingFact" | "evidence" | "rulingsRelied" | "decidedBy" | "why";
export interface ProductSummary {
  id: string;
  sku: string;
  title: string;
  category: string;
  categoryLabel: string;
  madeIn: string;
  madeInLabel: string;
  usCode: string | null;
  caCode: string | null;
  standing: Standing;
  standingLabel: string;
  versions: number;
  lastDecidedAt: string | null;
  inReview: boolean;
}
export interface ProductDetail extends ProductSummary {
  listingText: string;
  unitValue: Money | null;
  evidence: EvidenceOut[];
  latestAnswerId: string | null;
}
export interface RulingRef {
  id: string;
  key: string;
  statusLabel: string;
}
export interface BinderVersion {
  n: number;
  kind: string;
  kindLabel: string;
  at: string;
  usCode: string | null;
  caCode: string | null;
  standing: Standing;
  standingLabel: string;
  decidingFact: { label: string; value: string; sourceNote: string } | null;
  evidence: string[];
  rulingsRelied: RulingRef[];
  decidedBy: PersonRef | null;
  why: string;
  fingerprint: string;
  current: boolean;
  changed: BinderRow[];
}
export interface EntryOut {
  entryNumber: string;
  country: Country;
  enteredOn: string;
  code: string;
  dutyPaid: Money;
}
export interface BinderOut {
  product: ProductSummary;
  openedOn: string;
  keptUntil: string;
  retentionNote: string;
  versions: BinderVersion[];
  approval: { by: PersonRef; at: string; version: number; sentence: string } | null;
  evidence: EvidenceOut[];
  entries: EntryOut[];
  record: { chainVerified: boolean; checkedAt: string; events: number; fingerprint: string };
  advanceRuling: string | null;
}
export interface ExportResult {
  downloadUrl: string;
  fileName: string;
  bytes: number;
  pages: number | null;
  fingerprint: string;
  recordFingerprint: string;
}

/* ---------- review ---------- */
export type ReviewKind = "unsure" | "differs" | "ruling_changed" | "always_review" | "requested";
export type ReasonKind = "facts_differ" | "ruling_elsewhere" | "heading_misread" | "other";
export type DocketFilter = "all" | "unsure" | "differs" | "ruling_changed" | "always" | "ca";
export interface ReviewRow {
  id: string;
  productId: string;
  sku: string;
  productTitle: string;
  waitingSince: string;
  waitingLabel: string;
  into: "US" | "CA" | "both";
  intoLabel: string;
  proposedUs: CodeOut | null;
  proposedCa: CodeOut | null;
  kind: ReviewKind;
  kindLabel: string;
  detail: string;
  value: Money | null;
  withName: string | null;
  status: string;
  statusLabel: string;
}
export interface DocketOut {
  counts: { all: number; unsure: number; differs: number; rulingChanged: number; always: number; ca: number };
  oldestLabel: string;
  items: ReviewRow[];
  total: number;
  week: Record<string, number>;
  nextRound: Record<string, number>;
  emptyMessage: string;
}
export interface QuestionOut {
  id: string;
  askedBy: string;
  askedAt: string;
  text: string;
  options: string[];
  answer: string | null;
  answeredBy: string | null;
  answeredAt: string | null;
}
export interface DecisionRecord {
  row: ReviewRow;
  listing: string;
  specSheet: string;
  specSheetFile: string | null;
  uploadedBy: string | null;
  uploadedAt: string | null;
  decidingPhrases: { source: "listing" | "spec_sheet"; span: Span }[];
  misread: string | null;
  previousUs: string | null;
  rulingsRelied: RulingRef[];
  rulingChange: RulingStatusOut | null;
  rule: string | null;
  answerId: string;
  questions: QuestionOut[];
}
export interface RedlineCell {
  index: number;
  proposed: string;
  yours: string;
  changed: boolean;
}
export interface LessonOut {
  lesson: string;
  redline: RedlineCell[];
}
export interface DecisionOut {
  item: ReviewRow;
  binderVersion: number | null;
  lesson: string | null;
  toast: string;
}
export interface RuleOut {
  id: string;
  kind: string;
  kindLabel: string;
  value: string;
  label: string;
  active: boolean;
  createdBy: string;
  createdAt: string;
  matches: number;
}

/* ---------- watch ---------- */
export interface AffectedOut {
  productId: string;
  sku: string;
  title: string;
  effect: string;
  recheck: "unchanged" | "needs_review" | "re_approved";
  recheckLabel: string;
  dutyBefore?: Money | null;
  dutyAfter?: Money | null;
}
export interface WatchItemOut {
  id: string;
  date: string | null;
  dateLabel: string;
  dateNote: string | null;
  kind: string;
  kindLabel: string;
  headline: string;
  body: string;
  knows: string[];
  unknowns: string[];
  affectedCount: number;
  affected: AffectedOut[];
  sourceLabel: string;
  sourceUrl: string;
}
export interface WatchOut {
  items: WatchItemOut[];
  lastCheckedAt: string;
  checks: string[];
  quietMessage: string;
}

/* ---------- lab ---------- */
export type RoundStatus = "training" | "waiting_signoff" | "live" | "not_made_live" | "retired" | "failed";
export interface RoundStrip {
  n: number;
  status: RoundStatus;
  statusLabel: string;
  trainedOn: string | null;
  note: string;
}
export interface InUseOut {
  kind: "word_matching" | "round";
  round: number | null;
  label: string;
  fullCode: number;
  heading: number;
  sentence: string;
}
export interface LabOut {
  inUse?: InUseOut | null;
  rounds: RoundStrip[];
  live: number | null;
  candidate: number | null;
  correctionsWaiting: number;
}
export interface DepthRow {
  level: "chapter" | "heading" | "subheading" | "full_code";
  levelLabel: string;
  wordMatching: number;
  live: number | null;
  candidate: number;
  unoptimised?: number | null;
}
export interface ConfidenceCell {
  said: number;
  right: number;
  per100: number;
  sentence: string;
}
export interface ChapterRow {
  chapter: string;
  title: string;
  tested: number;
  before: number;
  after: number;
  change: number;
  changeLabel: string;
  newRulings: number;
  moving: boolean;
}
export interface CheckOut {
  key: string;
  label: string;
  passed: boolean;
  value: string;
  threshold: string;
}
export interface Signature {
  name: string;
  role: string;
  roleLabel: string;
  signedAt: string;
  statement: string;
}
export interface RoundOut {
  n: number;
  status: RoundStatus;
  statusLabel: string;
  trainedOn: string | null;
  testCount: number;
  testFrom: string;
  testTo: string;
  snapshot: string;
  rerunNote: string;
  lede: string;
  byDepth: DepthRow[];
  confidence: { strong?: ConfidenceCell; broker?: ConfidenceCell };
  byChapter: ChapterRow[];
  learned: string[];
  drift: Record<string, string | number>;
  checks: CheckOut[];
  signOff: { required: number; signatures: Signature[]; canSign: boolean; willPromote: boolean; note: string };
  runBy: string;
}

/* ---------- settings / audit / jobs ---------- */
export interface OrgSettingsOut {
  into: Country[];
  madeIn: string;
  ports: string[];
  alwaysSendToBroker: boolean;
  retentionYears: number;
  retentionYearsCa?: number;
  retentionNote?: string;
  deletingNote: string;
  brokerName: string | null;
}
export interface AuditRow {
  id: number;
  at: string;
  actorName: string;
  actorRole: string;
  actorRoleLabel: string;
  action: string;
  actionLabel: string;
  summary: string;
  targetType: string;
  targetId: string;
  targetLabel: string;
  fingerprint: string;
}
export interface ChainOut {
  ok: boolean;
  events: number;
  brokenAt: number | null;
  checkedAt: string;
  sentence: string;
}
export interface JobOut {
  id: string;
  kind: string;
  kindLabel: string;
  status: "queued" | "running" | "succeeded" | "failed";
  statusLabel: string;
  progress: number;
  stage: string;
  message: string;
  result: Record<string, unknown>;
  error: string;
  createdAt: string;
  finishedAt: string | null;
}
export interface JobAccepted {
  jobId: string;
  statusUrl: string;
  eventsUrl: string;
}
