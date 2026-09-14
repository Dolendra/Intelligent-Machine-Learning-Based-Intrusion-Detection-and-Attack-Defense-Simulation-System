const API_BASE = import.meta.env.VITE_API_BASE ?? "";
const TOKEN_KEY = "aegis_access_token";

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
    /* ignore */
  }
}

function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

export type PredictResult = {
  is_attack: boolean;
  attack_type: string;
  confidence: number;
  binary_proba_attack: number;
  class_probabilities: Record<string, number>;
  risk_score: number;
  severity: string;
  recommendation: {
    primary: string;
    actions: string[];
    rationale: string;
    expected_effect: string;
    advisory_only: boolean;
    disclaimer?: string;
    rule_hits?: Array<Record<string, string>>;
    rule_actions?: string[];
  };
  incident_id: string | null;
  certainty?: string;
  confidence_band?: string;
  confidence_band_label?: string;
  threshold?: number;
  uncertainty_lower?: number;
  uncertainty_upper?: number;
  threshold_note?: string;
  risk_factors?: Record<string, number>;
  risk_contributions?: Record<string, number>;
  risk_why?: string;
  decision_trace?: {
    title: string;
    advisory_only?: boolean;
    steps: Array<{ stage: string; title: string; detail: string; timestamp?: string }>;
  };
};

export type BatchPredictResult = {
  total_flows: number;
  attack_flows: number;
  benign_flows: number;
  attack_percentage: number;
  by_attack_type: Record<string, number>;
  highest_risk: {
    flow_index: number;
    attack_type: string;
    risk_score: number;
    severity: string;
  } | null;
  results: Array<PredictResult & { flow_index: number }>;
};

export type ExplainResult = {
  method?: string;
  requested_method?: string;
  actual_method?: string;
  fallback_used?: boolean;
  prediction: string;
  is_attack: boolean;
  confidence: number;
  top_features: { feature: string; contribution: number }[];
  explanation: string;
  available?: boolean;
};

export type SimSession = {
  id: string;
  attack_type: string;
  state: string;
  risk_score: number;
  severity: string;
  confidence: number;
  recommendation: PredictResult["recommendation"];
  nodes: { id: string; label: string; kind: string; status: string }[];
  edges: { id: string; source: string; target: string; traffic: string; intensity: number }[];
  timeline: { event: string; state: string; detail: string; timestamp?: string; t_s?: number }[];
  narrative?: string[];
  metrics?: Record<string, number | string | unknown>;
  series?: {
    labels: string[];
    with_defense: { traffic: number[]; stress: number[]; risk: number[] };
    without_defense: { traffic: number[]; stress: number[]; risk: number[] };
  };
  latencies?: {
    detection_s?: number | null;
    defense_s?: number | null;
    recovery_s?: number | null;
    attack_to_recover_s?: number | null;
  };
  phase_guide?: Array<{ t: string; label: string; state: string }>;
  comparison?: {
    without_defense: { peak_traffic: number; server_stress: number; risk: number; threat?: string };
    with_defense: {
      peak_traffic: number;
      server_stress: number;
      risk: number;
      traffic_blocked: number;
      threat?: string;
    };
  };
  incident_id?: string | null;
  campaign_id?: string | null;
  campaign_progression?: string[];
  disclaimer?: string;
};

export const api = {
  health: () =>
    request<{ status: string; models_loaded: boolean; version: string }>("/api/health"),
  incidents: () => request<{ items: Array<Record<string, unknown>> }>("/api/incidents"),
  getIncident: (incident_id: string) =>
    request<Record<string, unknown>>(`/api/incidents/${encodeURIComponent(incident_id)}`),
  incidentTrace: (incident_id: string) =>
    request<{
      title: string;
      steps: Array<{ stage: string; title: string; detail: string; timestamp?: string }>;
    }>(`/api/incidents/${encodeURIComponent(incident_id)}/trace`),
  models: () => request<Record<string, unknown>>("/api/models"),
  modelsHealth: () => request<Record<string, unknown>>("/api/models/health"),
  modelsComparison: () => request<Record<string, unknown>>("/api/models/comparison"),
  globalShap: (refresh = false) =>
    request<Record<string, unknown>>(`/api/models/shap/global?refresh=${refresh ? "true" : "false"}`),
  experiments: () => request<{ experiments?: Array<Record<string, unknown>> }>("/api/experiments"),
  drift: () => request<Record<string, unknown>>("/api/drift"),
  assets: () => request<{ items: Array<Record<string, unknown>> }>("/api/assets"),
  campaigns: () => request<{ items: Array<Record<string, unknown>> }>("/api/campaigns"),
  getCampaign: (campaign_id: string) =>
    request<Record<string, unknown>>(`/api/campaigns/${encodeURIComponent(campaign_id)}`),
  simulateCampaign: (campaign_id: string) =>
    request<SimSession>(`/api/campaigns/${encodeURIComponent(campaign_id)}/simulate`, { method: "POST" }),
  analytics: () =>
    request<{ total_incidents: number; by_severity: Record<string, number>; by_attack_type: Record<string, number> }>(
      "/api/analytics"
    ),
  predict: (features: Record<string, number>) =>
    request<PredictResult>("/api/predict", { method: "POST", body: JSON.stringify({ features, persist: true }) }),
  predictBatch: (flows: Record<string, number>[], persist = false) =>
    request<BatchPredictResult>("/api/predict/batch", {
      method: "POST",
      body: JSON.stringify({ flows, persist }),
    }),
  demoFlows: (attackType?: string, n = 10) =>
    request<{ items: Array<{ features: Record<string, number>; label: string }>; count: number }>(
      `/api/demo/flows?n=${n}${attackType ? `&attack_type=${encodeURIComponent(attackType)}` : ""}`
    ),
  updateIncident: (incident_id: string, status: string, extras?: { analyst_notes?: string; defense_action?: string }) =>
    request<Record<string, unknown>>(`/api/incidents/${encodeURIComponent(incident_id)}`, {
      method: "PATCH",
      body: JSON.stringify({ status, ...extras }),
    }),
  explain: (features: Record<string, number>, method: "shap" | "lime" = "shap") =>
    request<ExplainResult>("/api/explain", {
      method: "POST",
      body: JSON.stringify({ features, top_k: 10, method }),
    }),
  counterfactual: (features: Record<string, number>) =>
    request<Record<string, unknown>>("/api/explain/counterfactual", {
      method: "POST",
      body: JSON.stringify({ features, top_k: 5, method: "shap" }),
    }),
  demoFlow: (attackType?: string) =>
    request<{ features: Record<string, number>; label: string | null }>(
      `/api/demo/flow${attackType ? `?attack_type=${encodeURIComponent(attackType)}` : ""}`
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
  listSims: (limit = 20) =>
    request<{ items: Array<Record<string, unknown>> }>(`/api/simulation?limit=${limit}`),
  simulateIncident: (incident_id: string) =>
    request<SimSession>(`/api/incidents/${encodeURIComponent(incident_id)}/simulate`, {
      method: "POST",
      body: JSON.stringify({}),
    }),
  simulateFromPrediction: (payload: {
    incident_id?: string;
    attack_type?: string;
    confidence?: number;
    risk_score?: number;
    severity?: string;
  }) =>
    request<SimSession>("/api/simulation/from-prediction", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  advanceSim: (session_id: string, action?: string) =>
    request<SimSession>("/api/simulation/advance", {
      method: "POST",
      body: JSON.stringify({ session_id, action }),
    }),
  getSim: (session_id: string) =>
    request<SimSession>(`/api/simulation/${encodeURIComponent(session_id)}`),
  predictBatchCsv: async (file: File, persist = false) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(
      `${API_BASE}/api/predict/batch/csv?persist=${persist ? "true" : "false"}`,
      { method: "POST", body: form, headers: authHeaders() }
    );
    if (!res.ok) throw new Error((await res.text()) || res.statusText);
    return res.json() as Promise<BatchPredictResult>;
  },
  ingestCapabilities: () => request<Record<string, unknown>>("/api/ingest/capabilities"),
  ingestFlowsCsv: async (file: File, predict = false, persist = false) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(
      `${API_BASE}/api/ingest/flows/csv?predict=${predict ? "true" : "false"}&persist=${persist ? "true" : "false"}`,
      { method: "POST", body: form, headers: authHeaders() }
    );
    if (!res.ok) throw new Error((await res.text()) || res.statusText);
    return res.json() as Promise<Record<string, unknown>>;
  },
  ingestPcap: async (file: File, predict = false, persist = false) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(
      `${API_BASE}/api/ingest/pcap?predict=${predict ? "true" : "false"}&persist=${persist ? "true" : "false"}`,
      { method: "POST", body: form, headers: authHeaders() }
    );
    if (!res.ok) throw new Error((await res.text()) || res.statusText);
    return res.json() as Promise<Record<string, unknown>>;
  },
  ingestQueueStatus: () => request<Record<string, unknown>>("/api/ingest/queue"),
  ingestQueueSubmit: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/ingest/queue/submit`, {
      method: "POST",
      body: form,
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error((await res.text()) || res.statusText);
    return res.json() as Promise<Record<string, unknown>>;
  },
  ingestQueueSubmitPcap: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/ingest/queue/submit-pcap`, {
      method: "POST",
      body: form,
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error((await res.text()) || res.statusText);
    return res.json() as Promise<Record<string, unknown>>;
  },
  ingestQueueJob: (jobId: string) =>
    request<Record<string, unknown>>(`/api/ingest/queue/${encodeURIComponent(jobId)}`),
  authStatus: () => request<Record<string, unknown>>("/api/auth/status"),
  authLogin: async (username: string, password: string) => {
    const out = await request<{
      access_token: string;
      user: { username: string; role: string; permissions: string[] };
    }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
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
  authMe: () =>
    request<{
      authenticated: boolean;
      auth_enabled?: boolean;
      username?: string;
      role?: string;
      permissions?: string[];
      note?: string;
    }>("/api/auth/me"),
  securityStatus: () => request<Record<string, unknown>>("/api/security/status"),
  responseCapabilities: () => request<Record<string, unknown>>("/api/response/capabilities"),
  proposeResponse: (body: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/response/actions/propose", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  proposeIncidentResponse: (incidentId: string) =>
    request<Record<string, unknown>>(
      `/api/incidents/${encodeURIComponent(incidentId)}/response/propose`,
      { method: "POST", body: "{}" }
    ),
  listIncidentResponses: (incidentId: string) =>
    request<{ incident_id: string; items: Array<Record<string, unknown>> }>(
      `/api/incidents/${encodeURIComponent(incidentId)}/response/actions`
    ),
  dryRunResponse: (actionId: string) =>
    request<Record<string, unknown>>(`/api/response/actions/${encodeURIComponent(actionId)}/dry-run`, {
      method: "POST",
      body: "{}",
    }),
  approveResponse: (actionId: string) =>
    request<Record<string, unknown>>(`/api/response/actions/${encodeURIComponent(actionId)}/approve`, {
      method: "POST",
      body: "{}",
    }),
  rejectResponse: (actionId: string, reason?: string) =>
    request<Record<string, unknown>>(`/api/response/actions/${encodeURIComponent(actionId)}/reject`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  rollbackResponse: (actionId: string) =>
    request<Record<string, unknown>>(`/api/response/actions/${encodeURIComponent(actionId)}/rollback`, {
      method: "POST",
      body: "{}",
    }),
  getResponseAction: (actionId: string) =>
    request<Record<string, unknown>>(`/api/response/actions/${encodeURIComponent(actionId)}`),
  downloadExport: async (kind: "incidents.csv" | "incidents.json" | "analytics.json" | "report.pdf") => {
    const res = await fetch(`${API_BASE}/api/export/${kind}`, { headers: authHeaders() });
    if (!res.ok) throw new Error((await res.text()) || res.statusText);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `aegis_${kind}`;
    a.click();
    URL.revokeObjectURL(url);
  },
};
