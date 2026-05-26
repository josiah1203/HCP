import * as d3 from "d3";
import { useEffect, useRef } from "react";

import type { GraphEdge, GraphNode } from "../api/types";

interface GraphViewProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  centerId: string;
}

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  isCenter: boolean;
}

type SimLink = d3.SimulationLinkDatum<SimNode>;

function nodeX(n: SimLink["source"]): number {
  if (typeof n === "object" && n !== null && "x" in n) return (n as SimNode).x ?? 0;
  return 0;
}

function nodeY(n: SimLink["target"]): number {
  if (typeof n === "object" && n !== null && "y" in n) return (n as SimNode).y ?? 0;
  return 0;
}

export function GraphView({ nodes, edges, centerId }: GraphViewProps) {
  const ref = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const svg = ref.current;
    if (!svg || nodes.length === 0) return;

    const width = svg.clientWidth || 600;
    const height = 360;

    d3.select(svg).selectAll("*").remove();

    const g = d3.select(svg).attr("viewBox", `0 0 ${width} ${height}`).append("g");

    const simNodes: SimNode[] = nodes.map((n) => ({
      id: n.id,
      label: n.label ?? n.id.slice(0, 8),
      isCenter: n.id === centerId,
    }));

    const simLinks: SimLink[] = edges.map((e) => ({
      source: e.source as unknown as SimNode,
      target: e.target as unknown as SimNode,
    }));

    const simulation = d3
      .forceSimulation(simNodes)
      .force(
        "link",
        d3
          .forceLink<SimNode, SimLink>(simLinks)
          .id((d) => d.id)
          .distance(80)
      )
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2));

    const link = g
      .append("g")
      .attr("stroke", "#94a3b8")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(simLinks)
      .join("line")
      .attr("stroke-width", 1.5);

    const node = g
      .append("g")
      .selectAll("g")
      .data(simNodes)
      .join("g");

    node
      .append("circle")
      .attr("r", (d) => (d.isCenter ? 14 : 10))
      .attr("fill", (d) => (d.isCenter ? "#2563eb" : "#64748b"));

    node
      .append("text")
      .text((d) => d.label)
      .attr("x", 14)
      .attr("y", 4)
      .attr("font-size", 11)
      .attr("fill", "#334155");

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => nodeX(d.source))
        .attr("y1", (d) => nodeY(d.source))
        .attr("x2", (d) => nodeX(d.target))
        .attr("y2", (d) => nodeY(d.target));

      node.attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    return () => {
      simulation.stop();
    };
  }, [nodes, edges, centerId]);

  if (nodes.length === 0) {
    return (
      <p className="text-sm text-slate-500 py-8 text-center">
        No graph data yet. Graph API returns relationships when indexed.
      </p>
    );
  }

  return (
    <svg
      ref={ref}
      className="w-full h-[360px] bg-slate-50 rounded border border-slate-200"
      role="img"
      aria-label="Object relationship graph"
    />
  );
}
