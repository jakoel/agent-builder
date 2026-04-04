"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Node,
  Edge,
  MarkerType,
} from "reactflow";
import "reactflow/dist/style.css";
import { FlowDefinition } from "@/lib/types";

interface FlowVisualizationProps {
  flow?: FlowDefinition;
}

const nodeColors: Record<string, string> = {
  start: "#22c55e",
  end: "#ef4444",
  tool_call: "#3b82f6",
  llm_call: "#a855f7",
  condition: "#f59e0b",
};

export default function FlowVisualization({
  flow,
}: FlowVisualizationProps) {
  const { nodes, edges } = useMemo(() => {
    if (!flow)
      return { nodes: [] as Node[], edges: [] as Edge[] };

    const rfNodes: Node[] = flow.nodes.map((n, i) => ({
      id: n.id,
      data: { label: n.label },
      position: { x: 150, y: i * 120 },
      style: {
        background: nodeColors[n.type] ?? "#6b7280",
        color: "#fff",
        border: "none",
        borderRadius: "8px",
        padding: "10px 16px",
        fontSize: "12px",
        fontWeight: 600,
      },
    }));

    const rfEdges: Edge[] = flow.edges.map((e, i) => ({
      id: `edge-${i}`,
      source: e.source,
      target: e.target,
      label: e.condition,
      animated: true,
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "#6b7280" },
      labelStyle: { fill: "#9ca3af", fontSize: 10 },
    }));

    return { nodes: rfNodes, edges: rfEdges };
  }, [flow]);

  if (!flow) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500 text-sm">
        No flow defined.
      </div>
    );
  }

  return (
    <div className="h-96 bg-gray-900 rounded-lg border border-gray-800 overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        attributionPosition="bottom-left"
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#374151" gap={16} />
        <Controls
          style={{ button: { background: "#1f2937", color: "#fff" } } as any}
        />
      </ReactFlow>
    </div>
  );
}
