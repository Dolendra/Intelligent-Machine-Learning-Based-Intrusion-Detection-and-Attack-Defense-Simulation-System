/**
 * Typed client for the Aegis FastAPI backend.
 *
 * - Every request goes through `request()` / `upload()` so errors are normalised into `ApiError`
 *   (status + parsed FastAPI `{detail}` payload) and 401s are broadcast globally.
 * - Endpoint paths and request bodies are the contract with backend/routes/api.py — do not change them here.
 */
const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const TOKEN_KEY = "aegis_access_token";

/** Fired on `window` whenever an authenticated request returns 401 (token cleared first). */
export const UNAUTHORIZED_EVENT = "aegis:unauthorized";

export function getAccessToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAccessToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode) — token stays in-memory only for this request */
  }
}

function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

/** Normalised API failure. `detail` is FastAPI's `detail` field when the body was JSON. */
export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;
  readonly body: string;
  readonly path: string;

  constructor(opts: { status: number; message: string; detail?: unknown; body?: string; path: string }) {
    super(opts.message);
    this.name = "ApiError";
    this.status = opts.status;
    this.detail = opts.detail;
    this.body = opts.body ?? "";
    this.path = opts.path;
  }
}

/** Turn a FastAPI `detail` value (string | {message} | validation list) into readable text. */
export function detailToMessage(detail: unknown): string | null {
  if (detail == null) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d) => {
        if (d && typeof d === "object") {
          const o = d as Record<string, unknown>;
          const loc = Array.isArray(o.loc) ? o.loc.filter((x) => x !== "body").join(".") : "";
          const msg = typeof o.msg === "string" ? o.msg : JSON.stringify(o);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(d);
      })
      .filter(Boolean);
    return parts.join("; ") || null;
  }
  if (typeof detail === "object") {
    const o = detail as Record<string, unknown>;
    for (const k of ["message", "error", "detail", "reason"]) {
      if (typeof o[k] === "string") return o[k] as string;
    }
    if (typeof o.code === "string") return o.code;
  }
  return null;
}

async function toApiError(res: Response, path: string): Promise<ApiError> {
  let body = "";
  try {
    body = await res.text();
  } catch {
    /* ignore */
  }
  let detail: unknown = undefined;
  try {
    const parsed = body ? JSON.parse(body) : undefined;
    detail = parsed && typeof parsed === "object" && "detail" in parsed ? (parsed as { detail: unknown }).detail : parsed;
  } catch {
    detail = undefined;
  }
  const message = detailToMessage(detail) || body || res.statusText || `HTTP ${res.status}`;
  return new ApiError({ status: res.status, message, detail, body, path });
}

function handleUnauthorized(path: string) {
  // Login failures are 401s too — they must not bounce the user around.
  if (path.startsWith("/api/auth/login")) return;
  const hadToken = Boolean(getAccessToken());
  setAccessToken(null);
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT, { detail: { path, hadToken } }));
  }
}

async function send(path: string, init: RequestInit): Promise<Response> {
  const res = await fetch(apiUrl(path), init);
  if (!res.ok) {
    if (res.status === 401) handleUnauthorized(path);
    throw await toApiError(res, path);
  }
  return res;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await send(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options?.headers ?? {}),
    },
  });
  return res.json() as Promise<T>;
}

async function upload<T>(path: string, file: File): Promise<T> {
  const form = new FormData();
  form.append("file", file);
  const res = await send(path, { method: "POST", body: form, headers: authHeaders() });
  return res.json() as Promise<T>;
}

const q = (b: boolean) => (b ? "true" : "false");
const enc = encodeURIComponent;

/* ------------------------------------------------------------------ types */

export type SeverityLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
export type FeatureVector = Record<string, number>;

export interface TraceStep {
  stage: string;
  title: string;
  detail: string;
  timestamp?: string;
}

export interface DecisionTrace {
  title: string;
  incident_id?: string;
  advisory_only?: boolean;
  steps: TraceStep[];
}

export interface Recommendation {
  primary: string;
  actions: string[];
  rationale: string;
  expected_effect: string;
  advisory_only: boolean;
  disclaimer?: string;
  rule_hits?: Array<Record<string, string>>;
  rule_actions?: string[];
}

export interface PredictResult {
  is_attack: boolean;
  attack_type: string;
  confidence: number;
  binary_proba_attack: number;
  class_probabilities: Record<string, number>;
  risk_score: number;
  severity: string;
  recommendation: Recommendation;
  incident_id: string | null;
  certainty?: string | null;
  confidence_band?: string | null;
  confidence_band_label?: string | null;
  threshold?: number | null;
  uncertainty_lower?: number | null;
  uncertainty_upper?: number | null;
  threshold_note?: string | null;
  /** Raw risk inputs, e.g. attack_base, confidence, intensity, asset_criticality (+ string intensity_method). */
  risk_factors?: Record<string, number | string> | null;
  /** Additive risk components that sum to risk_score. */
  risk_contributions?: Record<string, number> | null;
  risk_why?: string | null;
  deduplicated?: boolean | null;
  source_ref?: string | null;
  campaign_id?: string | null;
  escalated?: boolean | null;
  decision_trace?: DecisionTrace | null;
  intensity_method?: string | null;
  /** v3 advisory Zero-Day Gate verdict (null when the gate is unavailable). Never alters the frozen verdict. */
  zero_day?: ZeroDayResult | null;
}

export interface BatchPredictResult {
  total_flows: number;
  attack_flows: number;
  benign_flows: number;
  attack_percentage: number;
  by_attack_type: Record<string, number>;
  highest_risk: { flow_index: number; attack_type: string; risk_score: number; severity: string } | null;
  results: Array<PredictResult & { flow_index: number }>;
  /** v3: flows the Zero-Day Gate alerted on. */
  zero_day_alerts?: number;
  /** v3: flows labelled UNKNOWN-ATTACK or ZERO-DAY-ANOMALY. */
  zero_day_novel?: number;
  /** v3: novel flows the frozen v1.1 model called benign. */
  zero_day_missed_by_frozen?: number;
}

/* ------------------------------------------------------------------ v3: Aegis-OSR Zero-Day Gate */

/** "BENIGN" | a known family (e.g. "DDoS") | "UNKNOWN-ATTACK" | "ZERO-DAY-ANOMALY" */
export type GateLabel = string;
export const GATE_BENIGN = "BENIGN";
export const GATE_UNKNOWN_ATTACK = "UNKNOWN-ATTACK";
export const GATE_ZERO_DAY = "ZERO-DAY-ANOMALY";

export interface GateDeviation {
  feature: string;
  value: number;
  benign_neighbor_value: number;
  /** Signed distance from the benign neighbourhood in standardized (signed-log) units. */
  deviation_sigma: number;
}

/** One `/api/zero-day/assess` result (also `PredictResult.zero_day`). */
export interface ZeroDayResult {
  label: GateLabel;
  alert: boolean;
  novel: boolean;
  summary: string;
  /** Split-conformal p-value; alert when p ≤ alpha. */
  p_value: number;
  alpha: number;
  fused_surprisal: number;
  evidence: {
    supervised: { p_attack: number; surprisal: number };
    novelty: { knn_distance: number; surprisal: number };
  };
  family: { predicted: string; probability: number; conformity_p: number };
  /** Only populated for alerts (and when explain_top > 0). */
  top_deviations: GateDeviation[];
}

export interface ZeroDayAssessResponse {
  alpha: number;
  total: number;
  alerts: number;
  novel: number;
  results: ZeroDayResult[];
}

export interface GateOperatingPoint {
  alpha: number;
  benign_fpr: number;
  known_attack_recall: number;
  natural_unknown_alert_rate: number;
  per_family_recall?: Record<string, number>;
}

export interface NaturalUnknownRow {
  family: string;
  n: number;
  gate_alert_rate: number;
  gate_flagged_novel_rate: number;
  gate_labels: Record<string, number>;
  frozen_v11_attack_rate: number;
  frozen_v11_labels: Record<string, number>;
}

export interface GateEvaluation {
  operating_points?: GateOperatingPoint[];
  frozen_v11_operating_point?: { threshold: number; benign_fpr: number };
  test_sizes?: Record<string, number>;
  gate?: {
    benign_fpr?: number;
    benign_fpr_nominal_alpha?: number;
    known_attack_recall?: number;
    known_family_accuracy?: number;
    natural_unknown_alert_rate?: number;
    latency_ms_per_flow_batch?: number;
    served_vs_research_parity?: number;
  };
  frozen_v11?: { benign_fpr?: number; known_attack_recall?: number; natural_unknown_attack_rate?: number };
  natural_unknowns?: NaturalUnknownRow[];
  per_family_recall?: Record<string, { gate: number; frozen_v11: number }>;
  note?: string;
}

export interface GateMethod {
  classifier?: string;
  novelty?: string;
  fusion?: string;
  calibration?: string;
  attribution?: string;
  [k: string]: string | undefined;
}

export interface ZeroDayStatus {
  available: boolean;
  reason?: string | null;
  alpha?: number;
  alpha_family?: number;
  known_classes?: string[];
  n_features?: number;
  knn_reference_size?: number;
  calibration_size?: number;
  trained_at?: string | null;
  git_commit?: string | null;
  training?: { dataset?: string; n_train?: number; n_val?: number; known_classes?: string[]; [k: string]: unknown } | null;
  evaluation?: GateEvaluation | null;
  method?: GateMethod | null;
}

/* ------------------------------------------------------------------ v3: Live Traffic Monitor */

export interface LivePhase {
  name: string;
  seconds: number;
  mix: Record<string, number>;
}

export interface LiveScenario {
  id: string;
  title: string;
  description: string;
  phases: LivePhase[];
  cycle_seconds: number;
}

export interface LiveScenariosResponse {
  scenarios: LiveScenario[];
  max_rate: number;
  pool_available: boolean;
  disclaimer: string;
}

export type LiveOutcome = "caught_both" | "caught_frozen_only" | "caught_gate_only" | "missed" | "false_alarm" | "clean";

export interface LiveFlow {
  id: number;
  /** Epoch seconds. */
  ts: number;
  src: string;
  dst: string;
  dst_port: number;
  bytes: number;
  duration_ms: number;
  /** Ground-truth family of the replayed flow ("BENIGN" or an attack family). */
  truth: string;
  /** Family neither model was trained on (Infiltration, Heartbleed). */
  unseen_family: boolean;
  frozen: { is_attack: boolean; attack_type: string | null; confidence: number; risk_score: number; severity: string | null };
  gate: {
    label: GateLabel;
    alert: boolean;
    novel: boolean;
    p_value: number;
    summary: string;
    top_deviations: GateDeviation[];
  } | null;
  outcome: LiveOutcome;
}

export interface LiveRates {
  frozen_recall: number;
  gate_recall: number;
  combined_recall: number;
  frozen_fpr: number;
  gate_fpr: number;
  unseen_gate_recall: number | null;
  unseen_frozen_recall: number | null;
}

export interface LiveStats {
  total: number;
  attacks_truth: number;
  frozen_alerts: number;
  gate_alerts: number;
  caught_both: number;
  caught_frozen_only: number;
  caught_gate_only: number;
  missed: number;
  false_alarm_frozen: number;
  false_alarm_gate: number;
  novel_flags: number;
  unseen_total: number;
  unseen_caught_gate: number;
  unseen_caught_frozen: number;
  by_family: Record<string, { n: number; frozen: number; gate: number }>;
  rates: LiveRates;
}

/** Paused ticks omit ts / rate / phase.mix / models. */
export interface LiveTick {
  type: "tick";
  paused: boolean;
  seq: number;
  ts?: number;
  scenario: string;
  rate?: number;
  phase: { index: number; name: string; progress: number; mix?: Record<string, number> };
  flows: LiveFlow[];
  stats: LiveStats;
  models?: { frozen: boolean; gate: boolean };
}

export type LiveMessage =
  | { type: "connected"; scenario: string; rate: number; role?: string; username?: string | null }
  | LiveTick
  | { type: "error"; code: string; message: string };

export type LiveCommand = { action: "pause" | "resume" | "reset" } | { action: "set"; scenario?: string; rate?: number };

/* ------------------------------------------------------------------ v3: Research Lab */

/** Mean with a 95% CI across seeds (low/high equal the mean when n = 1). */
export interface CI {
  mean: number;
  low: number | null;
  high: number | null;
  n: number | null;
}

export type MethodGroup = "proposed" | "ablation" | "baseline";

export interface ResearchMethodRow {
  method: string;
  group: MethodGroup | string;
  evidence: string[];
  fusion: string | null;
  zero_day_recall: CI | null;
  zero_day_recall_at_0_001: CI | null;
  zero_day_recall_at_0_05: CI | null;
  auroc_unknown: CI | null;
  auprc_unknown: CI | null;
  known_recall: CI | null;
  fpr: CI | null;
}

export interface ResearchFold {
  fold: string;
  methods: Record<string, { zero_day_recall: CI | null; fpr: CI | null; auroc_unknown: CI | null }>;
}

export interface SignificanceRow {
  metric: string;
  versus: string;
  n: number;
  mean_diff: number;
  wins: number;
  losses: number;
  ties: number;
  statistic: number | null;
  p_value: number | null;
}

export interface AdaptationRow {
  key: string;
  variant: "recal" | "recal+ref" | "oracle" | string;
  window: number | string;
  fold: string;
  method: string;
  zero_day_recall: CI | null;
  fpr: CI | null;
}

export interface ProtocolBlock {
  methods: ResearchMethodRow[];
  folds: ResearchFold[];
  per_family: Record<string, Record<string, CI | null>>;
  significance: SignificanceRow[];
  adaptation: AdaptationRow[];
  attribution: Record<string, Record<string, CI | null>>;
  meta: {
    generated_at?: string | null;
    git_commit?: string | null;
    seeds?: number[] | null;
    alpha?: number | null;
    n_records?: number | null;
    runtime_seconds?: number | null;
    caps?: unknown;
  };
}

export type ProtocolKey = "loafo" | "temporal" | "cross";

export interface ProtocolHeadline {
  proposed_zero_day_recall: number;
  baseline_zero_day_recall: number;
  proposed_fpr: number | null;
  baseline_fpr: number | null;
  proposed_auroc: number | null;
  baseline_auroc: number | null;
}

export interface ResearchOverview {
  proposed: string;
  baseline: string;
  methods_catalog: Array<{ method: string; group: string; evidence: string[]; fusion: string | null }>;
  status: { loafo: boolean; temporal: boolean; cross: boolean; gate: boolean; frozen_2018: boolean };
  loafo: ProtocolBlock | null;
  temporal: ProtocolBlock | null;
  cross: ProtocolBlock | null;
  /** zero_day_gate_report.json — same evaluation block as /zero-day/status. */
  gate: ({ name?: string; trained_at?: string; git_commit?: string; method?: GateMethod; training?: Record<string, unknown>; advisory_only?: boolean; evaluation?: GateEvaluation } & Record<string, unknown>) | null;
  /** Shape not fixed yet — render generically. */
  frozen_v11_on_cic2018: Record<string, unknown> | null;
  headline: Partial<Record<ProtocolKey, ProtocolHeadline>>;
}

export interface FeatureContribution {
  feature: string;
  contribution: number;
}

export interface ExplainResult {
  method?: string;
  requested_method?: string;
  actual_method?: string;
  fallback_used?: boolean;
  prediction: string;
  is_attack: boolean;
  predicted_class_index?: number;
  confidence: number;
  top_features: FeatureContribution[];
  explanation: string;
  available?: boolean;
}

export interface CounterfactualEdit {
  feature: string;
  original_value: number;
  counterfactual_value: number;
  new_attack_type: string;
  new_is_attack: boolean;
  new_binary_proba_attack: number;
  flipped_to_benign: boolean;
  family_changed: boolean;
}

export interface CounterfactualResult {
  method?: string;
  advisory_only?: boolean;
  note?: string;
  baseline?: { attack_type: string; is_attack: boolean; binary_proba_attack: number };
  edits?: CounterfactualEdit[];
  combined?: {
    features_changed: string[];
    new_attack_type: string;
    new_is_attack: boolean;
    new_binary_proba_attack: number;
    flipped_to_benign: boolean;
  } | null;
}

export interface Incident {
  incident_id: string;
  created_at: string | null;
  attack_type: string;
  confidence: number;
  risk_score: number;
  severity: string;
  recommendation: string | null;
  status: string;
  analyst_notes: string | null;
  defense_action: string | null;
  resolved_at: string | null;
  asset_criticality: number | null;
  source_ref: string | null;
  campaign_id: string | null;
  hit_count?: number;
  allowed_next_statuses?: string[];
}

export interface IncidentEvent {
  old_status?: string | null;
  new_status: string;
  timestamp?: string | null;
  actor?: string | null;
  notes?: string | null;
}

export interface IncidentDetail extends Incident {
  events?: IncidentEvent[];
}

export interface Analytics {
  total_incidents: number;
  by_severity: Record<string, number>;
  by_attack_type: Record<string, number>;
  by_status?: Record<string, number>;
}

export interface BinaryTestMetrics {
  accuracy?: number;
  precision?: number;
  recall?: number;
  f1?: number;
  specificity?: number;
  fpr?: number;
  fnr?: number;
  mcc?: number;
  roc_auc?: number;
  pr_auc?: number;
  brier_score?: number;
  ece?: number;
  /** [[TN, FP], [FN, TP]] */
  confusion_matrix?: number[][];
  true_negatives?: number;
  false_positives?: number;
  false_negatives?: number;
  true_positives?: number;
}

export interface MulticlassTestMetrics {
  accuracy?: number;
  precision_macro?: number;
  recall_macro?: number;
  f1_macro?: number;
  precision_weighted?: number;
  recall_weighted?: number;
  f1_weighted?: number;
  confusion_matrix?: number[][];
}

export interface ModelMetadata {
  application_version?: string;
  model_version?: string;
  dataset?: string;
  dataset_source?: string;
  generated_at?: string;
  training_git_commit?: string;
  config_hash?: string;
  python_version?: string;
  packages?: Record<string, string>;
  split_sizes?: { training_rows?: number; validation_rows?: number; test_rows?: number };
  binary_model?: string;
  multiclass_model?: string;
  attack_classes?: string[];
  feature_count_binary?: number;
  feature_count_multiclass?: number;
  dual_selectors?: boolean;
  binary_threshold?: number;
  uncertainty_lower?: number;
  uncertainty_upper?: number;
  use_calibrated_binary?: boolean;
  test_metrics_binary?: BinaryTestMetrics;
  artifact_hashes?: Record<string, string | null>;
  notes?: string[];
}

export interface ModelsInfo {
  models_loaded: boolean;
  application_version?: string;
  model_version?: string;
  binary_threshold?: number;
  use_calibrated_binary_config?: boolean;
  calibrated_binary_active?: boolean;
  metadata_available?: boolean;
  training_report_available?: boolean;
  metadata?: ModelMetadata;
}

export interface OperatingPoint {
  operating_threshold?: number;
  uncertainty_lower?: number;
  uncertainty_upper?: number;
  selection_method?: string;
  validation_split?: string;
  val_rows?: number;
  band_derivation?: string;
}

export interface ModelsHealth {
  status: string;
  models_loaded: boolean;
  missing_artifacts?: string[];
  application_version?: string;
  model_version?: string;
  binary_threshold?: number;
  calibrated_binary_active?: boolean;
  metadata?: ModelMetadata;
  operating_point_available?: boolean;
  operating_point?: OperatingPoint;
  drift_available?: boolean;
  drift_summary?: { flagged?: string[]; status?: string | null } | null;
  xai_agreement_available?: boolean;
  note?: string;
}

export interface BinaryValidationRow {
  model: string;
  precision?: number;
  recall?: number;
  f1?: number;
  pr_auc?: number | null;
  fpr?: number;
  selection_score?: number | null;
  infer_seconds_val?: number;
}

export interface MulticlassValidationRow {
  model: string;
  f1_macro?: number;
  f1_weighted?: number;
  selection_score?: number | null;
}

export interface ModelsComparison {
  selection_criteria?: Record<string, string>;
  binary_best?: string;
  multiclass_best?: string;
  binary_validation?: BinaryValidationRow[];
  multiclass_validation?: MulticlassValidationRow[];
  binary_test?: BinaryTestMetrics;
  multiclass_test?: MulticlassTestMetrics;
  per_class_validation?: Record<string, Record<string, number>>;
  classes?: string[];
}

export interface FeatureImportance {
  feature: string;
  importance?: number;
  mean_abs_contribution?: number;
  n?: number;
}

export interface GlobalShap {
  experiment?: string;
  status?: string;
  global?: {
    method?: string;
    note?: string;
    binary_top?: FeatureImportance[];
    multiclass_top?: FeatureImportance[];
  };
  attack_specific?: {
    method?: string;
    note?: string;
    by_attack?: Record<string, { samples?: number; top_features: FeatureImportance[] }>;
    attacks?: string[];
  };
  samples_explained?: number;
}

export interface PsiRow {
  feature: string;
  psi: number;
  mean_shift_z?: number;
}

export interface RetrainRecommendation {
  action: string;
  reason?: string;
  promote?: boolean;
}

export interface DriftReport {
  available: boolean;
  message?: string;
  experiment?: string;
  ref?: string;
  current?: string;
  feature_drift?: {
    n_ref?: number;
    n_cur?: number;
    features_compared?: number;
    "flagged_psi_ge_0.2"?: string[];
    top_psi?: PsiRow[];
    note?: string;
  };
  label_drift?: { by_label?: Array<{ label: string; ref_pct: number; cur_pct: number; delta_pp: number }> };
  retrain_recommendation?: RetrainRecommendation | boolean | null;
  note?: string;
  summary?: {
    protocol?: string;
    features_compared?: number;
    "flagged_psi_ge_0.2_count"?: number;
    max_psi?: number;
    academic_caveats?: string[];
  };
}

export interface Experiment {
  experiment_id: string;
  name: string;
  artifact: string;
  present: boolean;
  path?: string | null;
  intended_conclusion?: string;
}

export interface Campaign {
  campaign_id: string;
  incident_count: number;
  attack_types?: string[];
  progression?: string[];
  max_risk?: number;
  max_severity?: string;
  latest_at?: string;
}

export interface CampaignDetail extends Campaign {
  incidents?: Incident[];
}

export interface SimNode {
  id: string;
  label: string;
  kind: string;
  status: string;
}

export interface SimEdge {
  id: string;
  source: string;
  target: string;
  traffic: string;
  intensity: number;
}

export interface SimSeriesSet {
  traffic: number[];
  stress: number[];
  risk: number[];
}

export interface SimSession {
  id: string;
  attack_type: string;
  state: string;
  risk_score: number;
  severity: string;
  confidence: number;
  recommendation: Recommendation;
  nodes: SimNode[];
  edges: SimEdge[];
  timeline: { event: string; state: string; detail: string; timestamp?: string; t_s?: number; dt_s?: number }[];
  narrative?: string[];
  metrics?: Record<string, unknown>;
  series?: { labels: string[]; with_defense: SimSeriesSet; without_defense: SimSeriesSet };
  latencies?: {
    detection_s?: number | null;
    defense_s?: number | null;
    recovery_s?: number | null;
    attack_to_recover_s?: number | null;
  };
  phase_guide?: Array<{ t: string; label: string; state: string }>;
  comparison?: {
    without_defense: { peak_traffic: number; server_stress: number; risk: number; threat?: string };
    with_defense: { peak_traffic: number; server_stress: number; risk: number; traffic_blocked: number; threat?: string };
  };
  incident_id?: string | null;
  campaign_id?: string | null;
  campaign_progression?: string[];
  created_at?: string;
  advisory_only?: boolean;
  disclaimer?: string;
}

export interface SimHistoryItem {
  session_id: string;
  attack_type: string;
  state: string;
  created_at?: string;
}

export interface QueueJob {
  job_id: string;
  status: string;
  latency_ms?: number | null;
  error?: string | null;
  result_summary?: { total_flows?: number; attack_flows?: number; [k: string]: unknown } | null;
  [k: string]: unknown;
}

export interface IngestCapabilities {
  schema?: { schema_id?: string; schema_version?: string; feature_count?: number; feature_names?: string[] };
  flows_csv?: { available?: boolean; [k: string]: unknown };
  pcap?: { status?: string; live_capture?: boolean; [k: string]: unknown };
  [k: string]: unknown;
}

export interface IngestResult {
  prediction?: BatchPredictResult;
  flow_count?: number;
  [k: string]: unknown;
}

export interface AuthMe {
  authenticated: boolean;
  auth_enabled?: boolean;
  username?: string;
  role?: string;
  permissions?: string[];
  note?: string;
}

export interface SecurityStatus {
  auth?: { enabled?: boolean; [k: string]: unknown };
  [k: string]: unknown;
}

export interface ResponseAuditEvent {
  event: string;
  timestamp?: string;
  actor?: string;
  [k: string]: unknown;
}

export interface ResponseAction {
  action_id: string;
  action_type: string;
  target?: string;
  status: string;
  approval_status?: string;
  pending_approval?: boolean;
  mode?: string;
  adapter?: string;
  dry_run_preview?: string | null;
  result?: string | null;
  reason?: string | null;
  reversible?: boolean;
  audit?: ResponseAuditEvent[];
  [k: string]: unknown;
}

export interface OpsDependency {
  status?: string;
  detail?: string;
  depth?: number | null;
}

export interface OpsAlert {
  id: string;
  severity: string;
  message: string;
  component?: string;
  value?: unknown;
}

export interface OpsStatus {
  service?: string;
  environment?: string;
  readiness?: { ready?: boolean; status?: string; missing?: string[] };
  dependencies?: Record<string, OpsDependency>;
  performance?: {
    requests_total?: number;
    p50_latency_ms?: number | null;
    p95_latency_ms?: number | null;
    errors_4xx?: number;
    errors_5xx?: number;
    uptime_seconds?: number;
  };
  detection?: {
    flows_processed_total?: number;
    detections_total?: number;
    attacks_detected_total?: number;
    normal_flows_total?: number;
  };
  queue?: { jobs_submitted?: number; jobs_completed?: number; jobs_failed?: number; queue_depth?: number; avg_detect_latency_ms?: number | null };
  pcap?: Record<string, number>;
  response?: Record<string, number>;
  security?: Record<string, number>;
  alerts?: OpsAlert[];
  recovery?: { ran_at?: string; notes?: string[] };
  notes?: string[];
}

export type ExportKind = "incidents.csv" | "incidents.json" | "analytics.json" | "report.pdf";

/** MITRE ATT&CK context attached to detections, recommendations and range incidents. */
export interface MitreAttack {
  framework: string;
  tactic_id: string;
  tactic: string;
  technique_id: string;
  technique: string;
  related: Array<{ technique_id: string; technique: string }>;
  url: string;
  note?: string;
}

/* ------------------------------------------------------------------ cyber range (trace-driven) */

export interface RangeStage {
  name: string;
  seconds: number;
  families: Record<string, number>;
  rate: number;
}

export interface RangeScenario {
  id: string;
  name: string;
  family: string;
  research_focus: string;
  description: string;
  base_rate: number;
  attackers: number;
  target: string;
  stages: RangeStage[];
  internal_attacker: boolean;
  difficulty: string;
  version: number;
  attack_seconds: number;
}

export interface RangeDefense {
  title: string;
  effect: string;
}

export interface RangeConfigInput {
  scenario: string;
  seed?: number;
  intensity?: number;
  attackers?: number | null;
  detector?: "frozen" | "gate" | "union";
  alert_threshold?: number;
  alert_window_s?: number;
  response_mode?: "auto" | "manual";
  defense?: string;
  approval_delay_s?: number;
  benign_rate?: number;
  capacity?: number;
  duration_s?: number | null;
  explain?: boolean;
}

export interface RangeTelemetry {
  t: number;
  stage: string;
  state: string;
  benign_target: number;
  benign_served: number;
  benign_blocked: number;
  attack_sent: number;
  attack_passed: number;
  attack_blocked: number;
  alerts_true: number;
  alerts_false: number;
  load_units: number;
  availability: number;
}

export interface RangeEvent {
  event_id: string;
  run_id: string;
  event_type: string;
  timestamp: string;
  sim_time_s: number;
  sequence: number;
  schema_version: number;
  payload: Record<string, unknown>;
}

export interface RangeFlow {
  t: number;
  src: string;
  dst: string;
  dst_role: string;
  truth: string;
  is_attack: boolean;
  status: "blocked" | "alert" | "passed";
  frozen: { alert: boolean; type: string; confidence: number } | null;
  gate: { alert: boolean; label: string; p_value: number } | null;
}

export interface RangeMetrics {
  detection_latency_s: number | null;
  first_alert_latency_s: number | null;
  time_to_mitigate_s: number | null;
  containment_time_s: number | null;
  recovery_time_s: number | null;
  attack_success_rate: number | null;
  attack_success_before_defense: number | null;
  attack_success_after_defense: number | null;
  residual_attack_flows_per_s: number | null;
  mitigation_effectiveness: number | null;
  availability_mean_during_attack: number | null;
  availability_min_during_attack: number | null;
  availability_mean_overall: number | null;
  collateral_benign_blocked: number;
  collateral_rate: number | null;
  false_positive_alerts: number;
  fpr_flows: number | null;
  fpr_flows_frozen: number | null;
  fpr_flows_gate: number | null;
  false_incidents: number;
  attack_flow_recall: number | null;
  attack_flow_recall_frozen: number | null;
  attack_flow_recall_gate: number | null;
  unseen_flows: number;
  attackers_detected: number;
  attackers_total: number;
  flows_total: number;
  attack_flows_sent: number;
  defense_applied: string | null;
  detected_family: string | null;
  outcome: string;
}

export interface RangeView {
  run_id: string;
  created_at: string;
  config: Required<Omit<RangeConfigInput, "attackers" | "duration_s">> & { attackers: number | null; duration_s: number | null };
  scenario: RangeScenario;
  t: number;
  duration_s: number;
  done: boolean;
  state: string;
  stage: string;
  awaiting_decision: boolean;
  recommended: string;
  chosen: string | null;
  detected_family: string | null;
  mitre_attack?: MitreAttack | null;
  controls: { policy: string | null; blocked: string[]; rate_limited: string[]; isolated: boolean; inspection: boolean };
  marks: Record<string, number | null>;
  attackers: Array<{ ip: string; detected_at: number | null; first_alert_at: number | null }>;
  telemetry: RangeTelemetry[];
  events: RangeEvent[];
  event_count: number;
  recent_flows: RangeFlow[];
  explanation: {
    actual_method?: string;
    prediction?: string;
    confidence?: number;
    explanation?: string;
    top_features?: Array<{ feature: string; contribution: number }>;
    feature_values?: Record<string, number | null>;
    flow_family_truth?: string;
  } | null;
  metrics: RangeMetrics;
  topology: { nodes: SimNode[]; edges: SimEdge[] };
  models: { frozen: boolean; gate: boolean };
  defenses: Record<string, RangeDefense>;
}

export interface RangeCI {
  mean: number | null;
  ci_low: number | null;
  ci_high: number | null;
  n: number;
}

export interface RangeSweepCell {
  cell: Record<string, string | number>;
  summary: Record<string, RangeCI>;
}

export interface RangeSweep {
  cells: RangeSweepCell[];
  seeds: number[];
  runtime_seconds: number;
}

export interface RangeExperiments {
  generated_at: string;
  seeds: number[];
  defenses: Record<string, RangeDefense>;
  scenarios: Record<string, RangeScenario>;
  suites: Record<string, RangeSweep>;
  notes: string[];
}

/* ------------------------------------------------------------------ client */

export const api = {
  rangeScenarios: () =>
    request<{ items: RangeScenario[]; defenses: Record<string, RangeDefense>; detectors: string[] }>("/api/range/scenarios"),
  rangeCreate: (body: RangeConfigInput) => request<RangeView>("/api/range/runs", { method: "POST", body: JSON.stringify(body) }),
  rangeGet: (runId: string) => request<RangeView>(`/api/range/runs/${enc(runId)}`),
  rangeStep: (runId: string, seconds = 1) =>
    request<RangeView>(`/api/range/runs/${enc(runId)}/step`, { method: "POST", body: JSON.stringify({ seconds }) }),
  rangeRespond: (runId: string, action: string) =>
    request<RangeView>(`/api/range/runs/${enc(runId)}/respond`, { method: "POST", body: JSON.stringify({ action }) }),
  rangeComplete: (runId: string) => request<RangeView>(`/api/range/runs/${enc(runId)}/complete`, { method: "POST" }),
  rangeExperiments: () => request<RangeExperiments>("/api/range/experiments/latest"),
  rangeSweep: (body: { scenarios: string[]; defenses: string[]; seeds: number[]; detector?: string; intensity?: number; approval_delay_s?: number }) =>
    request<RangeSweep>("/api/range/experiments/sweep", { method: "POST", body: JSON.stringify(body) }),
  health: () => request<{ status: string; models_loaded: boolean; version: string }>("/api/health"),
  incidents: (limit = 50) => request<{ items: Incident[] }>(`/api/incidents?limit=${limit}`),
  getIncident: (incident_id: string) => request<IncidentDetail>(`/api/incidents/${enc(incident_id)}`),
  incidentTrace: (incident_id: string) => request<DecisionTrace>(`/api/incidents/${enc(incident_id)}/trace`),
  models: () => request<ModelsInfo>("/api/models"),
  modelsHealth: () => request<ModelsHealth>("/api/models/health"),
  modelsComparison: () => request<ModelsComparison>("/api/models/comparison"),
  globalShap: (refresh = false) => request<GlobalShap>(`/api/models/shap/global?refresh=${q(refresh)}`),
  experiments: () => request<{ experiments?: Experiment[]; generated_at?: string }>("/api/experiments"),
  drift: () => request<DriftReport>("/api/drift"),
  assets: () => request<{ items: Array<Record<string, unknown>> }>("/api/assets"),
  campaigns: () => request<{ items: Campaign[] }>("/api/campaigns"),
  getCampaign: (campaign_id: string) => request<CampaignDetail>(`/api/campaigns/${enc(campaign_id)}`),
  simulateCampaign: (campaign_id: string) =>
    request<SimSession>(`/api/campaigns/${enc(campaign_id)}/simulate`, { method: "POST" }),
  analytics: () => request<Analytics>("/api/analytics"),
  predict: (features: FeatureVector, sourceRef?: string) =>
    request<PredictResult>("/api/predict", {
      method: "POST",
      body: JSON.stringify({ features, persist: true, ...(sourceRef ? { source_ref: sourceRef } : {}) }),
    }),
  predictBatch: (flows: FeatureVector[], persist = false) =>
    request<BatchPredictResult>("/api/predict/batch", { method: "POST", body: JSON.stringify({ flows, persist }) }),
  demoFlows: (attackType?: string, n = 10) =>
    request<{ items: Array<{ features: FeatureVector; label: string }>; count: number }>(
      `/api/demo/flows?n=${n}${attackType ? `&attack_type=${enc(attackType)}` : ""}`
    ),
  updateIncident: (incident_id: string, status: string, extras?: { analyst_notes?: string; defense_action?: string }) =>
    request<IncidentDetail>(`/api/incidents/${enc(incident_id)}`, {
      method: "PATCH",
      body: JSON.stringify({ status, ...extras }),
    }),
  explain: (features: FeatureVector, method: "shap" | "lime" = "shap") =>
    request<ExplainResult>("/api/explain", { method: "POST", body: JSON.stringify({ features, top_k: 10, method }) }),
  counterfactual: (features: FeatureVector) =>
    request<CounterfactualResult>("/api/explain/counterfactual", {
      method: "POST",
      body: JSON.stringify({ features, top_k: 5, method: "shap" }),
    }),
  demoFlow: (attackType?: string) =>
    request<{ features: FeatureVector; label: string | null }>(
      `/api/demo/flow${attackType ? `?attack_type=${enc(attackType)}` : ""}`
    ),
  startSim: (
    attack_type: string,
    confidence = 0.96,
    incident_id?: string,
    extras?: { traffic_intensity?: number; asset_criticality?: number; risk_score?: number; severity?: string }
  ) =>
    request<SimSession>("/api/simulation/start", {
      method: "POST",
      body: JSON.stringify({ attack_type, confidence, incident_id, ...extras }),
    }),
  listSims: (limit = 20) => request<{ items: SimHistoryItem[] }>(`/api/simulation?limit=${limit}`),
  simulateIncident: (incident_id: string) =>
    request<SimSession>(`/api/incidents/${enc(incident_id)}/simulate`, { method: "POST", body: JSON.stringify({}) }),
  simulateFromPrediction: (payload: {
    incident_id?: string;
    attack_type?: string;
    confidence?: number;
    risk_score?: number;
    severity?: string;
  }) => request<SimSession>("/api/simulation/from-prediction", { method: "POST", body: JSON.stringify(payload) }),
  advanceSim: (session_id: string, action?: string) =>
    request<SimSession>("/api/simulation/advance", { method: "POST", body: JSON.stringify({ session_id, action }) }),
  getSim: (session_id: string) => request<SimSession>(`/api/simulation/${enc(session_id)}`),
  predictBatchCsv: (file: File, persist = false) =>
    upload<BatchPredictResult>(`/api/predict/batch/csv?persist=${q(persist)}`, file),
  ingestCapabilities: () => request<IngestCapabilities>("/api/ingest/capabilities"),
  ingestFlowsCsv: (file: File, predict = false, persist = false) =>
    upload<IngestResult>(`/api/ingest/flows/csv?predict=${q(predict)}&persist=${q(persist)}`, file),
  ingestPcap: (file: File, predict = false, persist = false) =>
    upload<IngestResult>(`/api/ingest/pcap?predict=${q(predict)}&persist=${q(persist)}`, file),
  ingestQueueStatus: () => request<Record<string, unknown>>("/api/ingest/queue"),
  ingestQueueSubmit: (file: File) => upload<{ job: QueueJob }>("/api/ingest/queue/submit", file),
  ingestQueueSubmitPcap: (file: File) => upload<{ job: QueueJob }>("/api/ingest/queue/submit-pcap", file),
  ingestQueueJob: (jobId: string) => request<QueueJob>(`/api/ingest/queue/${enc(jobId)}`),
  authStatus: () => request<Record<string, unknown>>("/api/auth/status"),
  authLogin: async (username: string, password: string) => {
    const out = await request<{ access_token: string; user: { username: string; role: string; permissions: string[] } }>(
      "/api/auth/login",
      { method: "POST", body: JSON.stringify({ username, password }) }
    );
    setAccessToken(out.access_token);
    return out;
  },
  authLogout: async () => {
    try {
      await request("/api/auth/logout", { method: "POST", body: "{}" });
    } finally {
      setAccessToken(null);
    }
  },
  authMe: () => request<AuthMe>("/api/auth/me"),
  securityStatus: () => request<SecurityStatus>("/api/security/status"),
  opsStatus: () => request<OpsStatus>("/api/ops/status"),
  metrics: () => request<Record<string, unknown>>("/api/metrics"),
  ready: () => request<Record<string, unknown>>("/api/ready"),
  responseCapabilities: () => request<Record<string, unknown>>("/api/response/capabilities"),
  proposeResponse: (body: Record<string, unknown>) =>
    request<ResponseAction>("/api/response/actions/propose", { method: "POST", body: JSON.stringify(body) }),
  proposeIncidentResponse: (incidentId: string) =>
    request<ResponseAction>(`/api/incidents/${enc(incidentId)}/response/propose`, { method: "POST", body: "{}" }),
  listIncidentResponses: (incidentId: string) =>
    request<{ incident_id: string; items: ResponseAction[] }>(`/api/incidents/${enc(incidentId)}/response/actions`),
  dryRunResponse: (actionId: string) =>
    request<{ action: ResponseAction }>(`/api/response/actions/${enc(actionId)}/dry-run`, { method: "POST", body: "{}" }),
  approveResponse: (actionId: string) =>
    request<{ action: ResponseAction }>(`/api/response/actions/${enc(actionId)}/approve`, { method: "POST", body: "{}" }),
  rejectResponse: (actionId: string, reason?: string) =>
    request<{ action: ResponseAction }>(`/api/response/actions/${enc(actionId)}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  rollbackResponse: (actionId: string) =>
    request<{ action: ResponseAction }>(`/api/response/actions/${enc(actionId)}/rollback`, { method: "POST", body: "{}" }),
  getResponseAction: (actionId: string) => request<ResponseAction>(`/api/response/actions/${enc(actionId)}`),
  downloadExport: async (kind: ExportKind) => {
    const res = await send(`/api/export/${kind}`, { headers: authHeaders() });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aegis_${kind}`;
    a.click();
    URL.revokeObjectURL(url);
  },

  /* ---------------- v3 ---------------- */
  zeroDayStatus: () => request<ZeroDayStatus>("/api/zero-day/status"),
  /** Score raw flows with the advisory Zero-Day Gate. alpha ∈ (0, 0.2]; explain_top ∈ [0, 20]. */
  zeroDayAssess: (flows: FeatureVector[], opts?: { alpha?: number; explain_top?: number }) =>
    request<ZeroDayAssessResponse>("/api/zero-day/assess", {
      method: "POST",
      body: JSON.stringify({ flows, alpha: opts?.alpha, explain_top: opts?.explain_top ?? 5 }),
    }),
  liveScenarios: () => request<LiveScenariosResponse>("/api/live/scenarios"),
  researchOverview: () => request<ResearchOverview>("/api/research/overview"),
  /** Raw protocol summary (404 NOT_RUN until generated). */
  researchProtocol: (protocol: ProtocolKey) => request<Record<string, unknown>>(`/api/research/openset/${protocol}`),
};

/**
 * WebSocket URL for an API socket path (e.g. "/api/ws/events"). The Vite dev proxy is HTTP-only,
 * so in dev we talk to the API port directly. The bearer token rides as ?token= when present.
 */
export function wsUrl(path: string, params: Record<string, string | number | undefined> = {}): string {
  const base = import.meta.env.VITE_API_BASE ?? "";
  let url: string;
  if (base.startsWith("http")) {
    url = base.replace(/^http/, "ws") + path;
  } else {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.host;
    url = host.includes("5173") ? `${proto}://127.0.0.1:8000${path}` : `${proto}://${host}${path}`;
  }
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") qs.set(k, String(v));
  const token = getAccessToken();
  if (token) qs.set("token", token);
  const s = qs.toString();
  return s ? `${url}?${s}` : url;
}

/** WebSocket URL for the incident/analytics event stream. */
export function eventsWsUrl(): string {
  return wsUrl("/api/ws/events");
}

/** WebSocket URL for the Live Traffic Monitor replay stream. */
export function liveWsUrl(scenario: string, rate: number): string {
  return wsUrl("/api/ws/live", { scenario, rate });
}
