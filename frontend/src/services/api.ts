const API_BASE = import.meta.env.VITE_API_BASE ?? "";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
    ...options,
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
  };
  incident_id: string | null;
};

export type ExplainResult = {
  method?: string;
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
  timeline: { event: string; state: string; detail: string }[];
};

export const api = {
  health: () => request<{ status: string; models_loaded: boolean; version: string }>("/api/health"),
  analytics: () =>
    request<{ total_incidents: number; by_severity: Record<string, number>; by_attack_type: Record<string, number> }>(
      "/api/analytics"
    ),
  incidents: () => request<{ items: Array<Record<string, unknown>> }>("/api/incidents"),
  predict: (features: Record<string, number>) =>
    request<PredictResult>("/api/predict", { method: "POST", body: JSON.stringify({ features, persist: true }) }),
  explain: (features: Record<string, number>, method: "shap" | "lime" = "shap") =>
    request<ExplainResult>("/api/explain", {
      method: "POST",
      body: JSON.stringify({ features, top_k: 10, method }),
    }),
  demoFlow: (attackType?: string) =>
    request<{ features: Record<string, number>; label: string | null }>(
      `/api/demo/flow${attackType ? `?attack_type=${encodeURIComponent(attackType)}` : ""}`
    ),
  startSim: (attack_type: string, confidence = 0.96) =>
    request<SimSession>("/api/simulation/start", {
      method: "POST",
      body: JSON.stringify({ attack_type, confidence }),
    }),
  advanceSim: (session_id: string, action?: string) =>
    request<SimSession>("/api/simulation/advance", {
      method: "POST",
      body: JSON.stringify({ session_id, action }),
    }),
};
