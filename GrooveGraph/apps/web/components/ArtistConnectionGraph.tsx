"use client";

import React, { useMemo } from "react";
import { forceCenter, forceLink, forceManyBody, forceSimulation } from "d3-force";

export type GraphNode = { id: string; label: string; group?: string; x?: number; y?: number };
export type GraphLink = { source: string; target: string; label?: string };

export function ArtistConnectionGraph({ nodes, links }: { nodes: GraphNode[]; links: GraphLink[] }) {
  const layout = useMemo(() => {
    const graphNodes = nodes.map((node) => ({ ...node }));
    const graphLinks = links.map((link) => ({ ...link }));
    forceSimulation(graphNodes)
      .force("charge", forceManyBody().strength(-180))
      .force("center", forceCenter(260, 160))
      .force("link", forceLink(graphLinks).id((node) => (node as GraphNode).id).distance(105))
      .stop()
      .tick(80);
    return { nodes: graphNodes, links: graphLinks };
  }, [nodes, links]);

  return (
    <svg viewBox="0 0 520 320" className="h-[320px] w-full border border-slate-200 bg-white" role="img" aria-label="artist connection graph">
      {layout.links.map((link) => {
        const source = link.source as unknown as GraphNode;
        const target = link.target as unknown as GraphNode;
        return (
          <g key={`${source.id}-${target.id}`}>
            <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="#94a3b8" />
            {link.label ? (
              <text x={((source.x ?? 0) + (target.x ?? 0)) / 2} y={((source.y ?? 0) + (target.y ?? 0)) / 2 - 4} className="fill-slate-500 text-[10px]">
                {link.label}
              </text>
            ) : null}
          </g>
        );
      })}
      {layout.nodes.map((node) => (
        <g key={node.id} transform={`translate(${node.x ?? 0},${node.y ?? 0})`}>
          <circle r="20" fill={node.group === "project" ? "#f97316" : "#0f766e"} />
          <text y="36" textAnchor="middle" className="fill-slate-800 text-xs">
            {node.label}
          </text>
        </g>
      ))}
    </svg>
  );
}
