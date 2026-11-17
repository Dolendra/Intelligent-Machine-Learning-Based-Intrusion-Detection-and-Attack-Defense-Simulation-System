/**
 * Shared visuals for the advisory Aegis-OSR Zero-Day Gate (Detection, Zero-Day Lab, Live Monitor).
 * Colour convention: violet (--chart-7) = novelty / "caught only by the gate".
 */
import type { LucideIcon } from "lucide-react";
import {
  AlertOctagon,
  CheckCircle2,
  CircleDashed,
  EyeOff,
  Fingerprint,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import {
  GATE_BENIGN,
  GATE_UNKNOWN_ATTACK,
  GATE_ZERO_DAY,
  type GateDeviation,
  type LiveOutcome,
  type ZeroDayResult,
} from "../../services/api";
import { Badge, type BadgeTone } from "../ui/Badge";
import { Callout } from "../ui/Card";
import { BarList } from "../charts/BarList";
import { HorizontalBars } from "../charts/HorizontalBars";
import { formatNumber, formatPct } from "../../lib/format";

/* ------------------------------------------------------------------ labels */

export function gateLabelMeta(label: string | null | undefined): { text: string; tone: BadgeTone; icon: LucideIcon; color: string } {
  if (!label) return { text: "Unavailable", tone: "neutral", icon: CircleDashed, color: "var(--muted)" };
  if (label === GATE_BENIGN) return { text: "Benign", tone: "ok", icon: ShieldCheck, color: "var(--ok)" };
  if (label === GATE_ZERO_DAY) return { text: "Zero-day anomaly", tone: "novel", icon: Sparkles, color: "var(--chart-7)" };
  if (label === GATE_UNKNOWN_ATTACK) return { text: "Unknown attack", tone: "warn", icon: ShieldQuestion, color: "var(--warn)" };
  return { text: label, tone: "high", icon: ShieldAlert, color: "var(--sev-high)" };
}

/** Gate label with icon + text (Benign / known family / Unknown attack / Zero-day anomaly). */
export function GateLabelBadge({ label, size }: { label: string | null | undefined; size?: "sm" | "md" }) {
  const m = gateLabelMeta(label);
  return (
    <Badge tone={m.tone} icon={m.icon} size={size} title={label ?? "Gate unavailable"}>
      {m.text}
    </Badge>
  );
}

/* ------------------------------------------------------------------ live outcomes */

export const OUTCOME_META: Record<LiveOutcome, { text: string; short: string; tone: BadgeTone; icon: LucideIcon; color: string }> = {
  caught_both: { text: "Caught by both", short: "Both", tone: "ok", icon: CheckCircle2, color: "var(--ok)" },
  caught_frozen_only: { text: "Frozen model only", short: "Frozen only", tone: "info", icon: ShieldCheck, color: "var(--chart-1)" },
  caught_gate_only: { text: "Zero-day catch (gate only)", short: "Gate only", tone: "novel", icon: Sparkles, color: "var(--chart-7)" },
  missed: { text: "Missed by both", short: "Missed", tone: "danger", icon: EyeOff, color: "var(--danger)" },
  false_alarm: { text: "False alarm", short: "False alarm", tone: "warn", icon: TriangleAlert, color: "var(--warn)" },
  clean: { text: "Clean", short: "Clean", tone: "neutral", icon: CircleDashed, color: "var(--muted)" },
};

export function OutcomeBadge({ outcome, size = "sm", short }: { outcome: LiveOutcome; size?: "sm" | "md"; short?: boolean }) {
  const m = OUTCOME_META[outcome] ?? OUTCOME_META.clean;
  return (
    <Badge tone={m.tone} icon={m.icon} size={size}>
      {short ? m.short : m.text}
    </Badge>
  );
}

/* ------------------------------------------------------------------ p-value meter */

const P_FLOOR = 1e-5;

/** Log-scale meter: the shaded zone left of α is the alert region; the dot is the flow's p-value. */
export function PValueMeter({ p, alpha }: { p: number; alpha: number }) {
  const span = -Math.log10(P_FLOOR);
  const pos = (v: number) => `${((Math.log10(Math.max(v, P_FLOOR)) + span) / span) * 100}%`;
  const alert = p <= alpha;
  return (
    <div>
      <div className="pmeter" role="img" aria-label={`p-value ${p.toExponential(2)} versus alpha ${alpha}: ${alert ? "alert" : "no alert"}`}>
        <span className="pmeter-track">
          <span className="pmeter-zone" style={{ width: pos(alpha) }} />
        </span>
        <span className="pmeter-alpha" style={{ left: pos(alpha) }} />
        <span className="pmeter-dot" style={{ left: pos(p), background: alert ? "var(--danger)" : "var(--ok)" }} />
      </div>
      <div className="pmeter-scale" aria-hidden>
        <span>10⁻⁵</span>
        <span>10⁻⁴</span>
        <span>10⁻³</span>
        <span>0.01</span>
        <span>0.1</span>
        <span>1</span>
      </div>
      <div className="row small" style={{ justifyContent: "space-between", marginTop: 6 }}>
        <span>
          p = <strong className="mono">{formatP(p)}</strong>
        </span>
        <span className="muted">
          α = <span className="mono">{alpha}</span> · {alert ? "p ≤ α → alert" : "p > α → no alert"}
        </span>
      </div>
    </div>
  );
}

export function formatP(p: number): string {
  if (!Number.isFinite(p)) return "—";
  if (p === 0) return "0";
  return p < 0.001 ? p.toExponential(2) : p.toFixed(4);
}

/* ------------------------------------------------------------------ evidence */

/** Benign surprisals of the two evidence sources and their Fisher sum, plus family conformity. */
export function GateEvidence({ result, alphaFamily }: { result: ZeroDayResult; alphaFamily?: number }) {
  const { supervised, novelty } = result.evidence;
  const conforming = alphaFamily != null ? result.family.conformity_p > alphaFamily : undefined;
  return (
    <div className="stack-sm">
      <BarList
        ariaLabel="Benign surprisal per evidence source"
        sort={false}
        valueFormatter={(v) => v.toFixed(2)}
        items={[
          {
            label: "classifier",
            display: `Classifier evidence · P(attack) ${formatPct(supervised.p_attack, 1)}`,
            value: supervised.surprisal,
            color: "var(--chart-1)",
          },
          {
            label: "novelty",
            display: `Novelty evidence · kNN dist ${formatNumber(novelty.knn_distance, 3)}`,
            value: novelty.surprisal,
            color: "var(--chart-3)",
          },
          { label: "fused", display: "Fisher-fused surprisal", value: result.fused_surprisal, color: "var(--chart-7)" },
        ]}
      />
      <dl className="kv">
        <dt>Nearest known family</dt>
        <dd>
          {result.family.predicted} ({formatPct(result.family.probability, 0)})
        </dd>
        <dt>Family conformity p</dt>
        <dd>
          {formatP(result.family.conformity_p)}
          {conforming === undefined ? "" : conforming ? " · conforms" : " · does not conform"}
        </dd>
      </dl>
    </div>
  );
}

/** "Why it looks novel": per-feature deviation from the benign neighbourhood. */
export function DeviationBars({ deviations, max = 8 }: { deviations: GateDeviation[]; max?: number }) {
  if (!deviations.length) return <p className="muted small">No deviations reported (only computed for alerts).</p>;
  return (
    <HorizontalBars
      ariaLabel="Feature deviations from the nearest benign flows"
      maxItems={max}
      valueFormatter={(v) => `${v.toFixed(2)}σ`}
      positiveLabel="Higher than benign neighbours"
      negativeLabel="Lower than benign neighbours"
      positiveColor="var(--chart-7)"
      negativeColor="var(--chart-1)"
      items={deviations.map((d) => ({
        label: d.feature,
        value: d.deviation_sigma,
        hint: `${d.feature}: ${formatNumber(d.value, 3)} vs benign neighbours ${formatNumber(d.benign_neighbor_value, 3)}`,
      }))}
    />
  );
}

/* ------------------------------------------------------------------ verdict panel */

export interface GateVerdictPanelProps {
  result: ZeroDayResult | null | undefined;
  /** Frozen v1.1 verdict for the same flow (enables the "frozen model missed it" highlight). */
  frozenIsAttack?: boolean;
  alphaFamily?: number;
  /** Hide evidence/deviation details. */
  compact?: boolean;
}

export function GateVerdictPanel({ result, frozenIsAttack, alphaFamily, compact }: GateVerdictPanelProps) {
  if (!result) {
    return (
      <Callout tone="neutral" icon={CircleDashed} title="Zero-Day Gate unavailable">
        Gate artifacts are not loaded on the server (run scripts/51_train_zero_day_gate.py). The frozen verdict is unaffected.
      </Callout>
    );
  }
  const missedByFrozen = result.alert && frozenIsAttack === false;
  const disagreeBenign = !result.alert && frozenIsAttack === true;
  return (
    <div className="stack">
      <div className="row" style={{ gap: 8 }}>
        <GateLabelBadge label={result.label} />
        {result.novel && (
          <Badge tone="novel" icon={Fingerprint}>
            Novel
          </Badge>
        )}
      </div>
      <p className="text-2">{result.summary}</p>
      {missedByFrozen && (
        <Callout tone="danger" icon={AlertOctagon} title="Possible zero-day — the frozen model missed it">
          The frozen v1.1 detector classified this flow as benign, but it is statistically unlike benign traffic at α = {result.alpha}.
        </Callout>
      )}
      {disagreeBenign && (
        <Callout tone="info" title="Gate sees benign-like traffic">
          The frozen model alerted while the gate's benign test did not reject at α = {result.alpha}. The frozen verdict stands.
        </Callout>
      )}
      <PValueMeter p={result.p_value} alpha={result.alpha} />
      {!compact && (
        <>
          <GateEvidence result={result} alphaFamily={alphaFamily} />
          {result.top_deviations.length > 0 && (
            <div className="stack-sm">
              <h4 className="small muted" style={{ textTransform: "uppercase", letterSpacing: "0.06em" }}>
                {result.novel ? "Why it looks novel" : "Largest deviations from benign neighbours"}
              </h4>
              <DeviationBars deviations={result.top_deviations} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
