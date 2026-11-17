import { useMemo } from "react";
import { ReactFlow, Background, Controls, MarkerType, Position, type Edge, type Node } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { SimEdge, SimNode } from "../services/api";
import { useChartTheme, type ChartTheme } from "./charts/theme";
import { useThemeName } from "../app/theme";
import { humanize } from "../lib/format";

/** Hand-placed coordinates for the known scenario nodes (left → right: attacker → edge → core → hosts). */
const POS: Record<string, { x: number; y: number }> = {
  attacker: { x: 40, y: 160 },
  attacker2: { x: 40, y: 60 },
  attacker3: { x: 40, y: 260 },
  attacker4: { x: 40, y: 340 },
  internet: { x: 220, y: 160 },
  firewall: { x: 400, y: 160 },
  waf: { x: 520, y: 80 },
  router: { x: 580, y: 200 },
  ids: { x: 580, y: 40 },
  server: { x: 780, y: 80 },
  auth: { x: 780, y: 40 },
  ports: { x: 780, y: 200 },
  pc01: { x: 780, y: 260 },
  pc02: { x: 780, y: 340 },
  c2: { x: 940, y: 260 },
};

const KIND_COLUMN: Record<string, number> = { attacker: 0, router: 1, firewall: 2, ids: 3, waf: 3, server: 4, host: 4, c2: 5 };

/**
 * Deterministic fallback for nodes without a fixed position: column by node kind, rows by
 * order of appearance — no Math.random(), so the layout never jitters between renders.
 */
export function layoutNodes(nodes: SimNode[]): Record<string, { x: number; y: number }> {
  const out: Record<string, { x: number; y: number }> = {};
  const rowsUsed: Record<number, number> = {};
  for (const n of nodes) {
    if (POS[n.id]) {
      out[n.id] = POS[n.id];
      continue;
    }
    const col = KIND_COLUMN[n.kind] ?? 3;
    const row = rowsUsed[col] ?? 0;
    rowsUsed[col] = row + 1;
    out[n.id] = { x: 40 + col * 180, y: 420 + row * 90 };
  }
  return out;
}

function statusColor(t: ChartTheme, status: string) {
  if (status === "alert") return t.severity.CRITICAL;
  if (status === "stressed") return t.severity.MEDIUM;
  if (status === "blocked") return t.accent;
  if (status === "isolated") return t.series[6];
  return t.axis;
}

function trafficColor(t: ChartTheme, traffic: string) {
  if (traffic === "malicious") return t.severity.CRITICAL;
  if (traffic === "blocked") return t.severity.MEDIUM;
  if (traffic === "filtered") return t.accent;
  return t.muted;
}

export function NetworkTopology({ nodes, edges }: { nodes: SimNode[]; edges: SimEdge[] }) {
  const theme = useChartTheme();
  const themeName = useThemeName();
  const positions = useMemo(() => layoutNodes(nodes), [nodes]);

  const rfNodes: Node[] = useMemo(
    () =>
      nodes.map((n) => {
        const c = statusColor(theme, n.status);
        return {
          id: n.id,
          position: positions[n.id],
          data: { label: `${n.label}\n${humanize(n.status)}` },
          sourcePosition: Position.Right,
          targetPosition: Position.Left,
          ariaLabel: `${n.label}: ${n.status}`,
          style: {
            background: theme.surface,
            color: theme.text,
            border: `1.5px solid ${c}`,
            borderRadius: 12,
            padding: 10,
            fontSize: 12,
            fontFamily: "IBM Plex Mono, monospace",
            width: 124,
            textAlign: "center" as const,
            boxShadow: n.status === "alert" ? `0 0 18px ${c}66` : "none",
            whiteSpace: "pre-line" as const,
          },
        };
      }),
    [nodes, positions, theme]
  );

  const rfEdges: Edge[] = useMemo(
    () =>
      edges.map((e) => {
        const c = trafficColor(theme, e.traffic);
        return {
          id: e.id,
          source: e.source,
          target: e.target,
          animated: e.traffic === "malicious" || e.traffic === "filtered",
          style: { stroke: c, strokeWidth: 1.5 + e.intensity * 3 },
          markerEnd: { type: MarkerType.ArrowClosed, color: c },
          label: e.traffic !== "normal" ? e.traffic : undefined,
          labelStyle: { fill: theme.text2, fontSize: 10 },
          labelBgStyle: { fill: theme.surface },
        };
      }),
    [edges, theme]
  );

  const legend = [
    { label: "Alert / malicious", color: theme.severity.CRITICAL },
    { label: "Stressed / blocked", color: theme.severity.MEDIUM },
    { label: "Filtered / defended", color: theme.accent },
    { label: "Normal", color: theme.muted },
  ];

  return (
    <div className="stack-sm">
      <div className="sim-canvas" role="img" aria-label={`Network topology with ${nodes.length} nodes and ${edges.length} links`}>
        <ReactFlow nodes={rfNodes} edges={rfEdges} fitView proOptions={{ hideAttribution: true }} nodesDraggable={false} colorMode={themeName}>
          <Background gap={18} color={theme.grid} />
          <Controls showInteractive={false} />
        </ReactFlow>
      </div>
      <div className="legend">
        {legend.map((l) => (
          <span key={l.label} className="legend-item">
            <span className="legend-swatch line" style={{ background: l.color }} aria-hidden />
            {l.label}
          </span>
        ))}
      </div>
    </div>
  );
}
