import { useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MarkerType,
  Position,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

type SimNode = { id: string; label: string; kind: string; status: string };
type SimEdge = { id: string; source: string; target: string; traffic: string; intensity: number };

const POS: Record<string, { x: number; y: number }> = {
  attacker: { x: 40, y: 160 },
  internet: { x: 220, y: 160 },
  firewall: { x: 400, y: 160 },
  router: { x: 580, y: 160 },
  ids: { x: 580, y: 40 },
  server: { x: 780, y: 80 },
  pc01: { x: 780, y: 180 },
  pc02: { x: 780, y: 280 },
};

function statusColor(status: string) {
  if (status === "alert") return "#e35d6a";
  if (status === "stressed") return "#e4a54a";
  if (status === "blocked") return "#3ec7c2";
  if (status === "isolated") return "#9b8cff";
  return "#8fa6b5";
}

function trafficColor(traffic: string) {
  if (traffic === "malicious") return "#e35d6a";
  if (traffic === "blocked") return "#e4a54a";
  if (traffic === "filtered") return "#3ec7c2";
  return "#4d6a7c";
}

export function NetworkTopology({
  nodes,
  edges,
}: {
  nodes: SimNode[];
  edges: SimEdge[];
}) {
  const rfNodes: Node[] = useMemo(
    () =>
      nodes.map((n) => ({
        id: n.id,
        position: POS[n.id] ?? { x: 0, y: 0 },
        data: { label: `${n.label}\n${n.status}` },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        style: {
          background: "#0c1a27",
          color: "#e7f0f5",
          border: `1px solid ${statusColor(n.status)}`,
          borderRadius: 12,
          padding: 10,
          fontSize: 12,
          fontFamily: "IBM Plex Mono, monospace",
          width: 120,
          textAlign: "center" as const,
          boxShadow: n.status === "alert" ? "0 0 18px rgba(227,93,106,.35)" : "none",
          whiteSpace: "pre-line" as const,
        },
      })),
    [nodes]
  );

  const rfEdges: Edge[] = useMemo(
    () =>
      edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        animated: e.traffic === "malicious" || e.traffic === "filtered",
        style: {
          stroke: trafficColor(e.traffic),
          strokeWidth: 1.5 + e.intensity * 3,
        },
        markerEnd: { type: MarkerType.ArrowClosed, color: trafficColor(e.traffic) },
        label: e.traffic !== "normal" ? e.traffic : undefined,
        labelStyle: { fill: "#8fa6b5", fontSize: 10 },
      })),
    [edges]
  );

  useEffect(() => {
    // ensure react-flow measures after mount animations
  }, [nodes, edges]);

  return (
    <div className="sim-canvas">
      <ReactFlow nodes={rfNodes} edges={rfEdges} fitView proOptions={{ hideAttribution: true }}>
        <Background gap={18} color="rgba(140,190,210,0.08)" />
        <Controls />
      </ReactFlow>
    </div>
  );
}
