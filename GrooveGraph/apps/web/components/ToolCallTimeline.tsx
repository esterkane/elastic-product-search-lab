"use client";

import React from "react";
import type { Citation, ToolCall } from "../lib/api";

export function ToolCallTimeline({ toolCalls, sources }: { toolCalls: ToolCall[]; sources: Citation[] }) {
  return (
    <aside className="border border-slate-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-slate-900">Research Activity</h2>
      <div className="mt-4 space-y-3" aria-label="tool calls">
        {toolCalls.length === 0 ? <p className="text-sm text-slate-500">No tool calls yet.</p> : null}
        {toolCalls.map((call, index) => (
          <div key={`${call.id}-${index}`} className="border-l-2 border-groove pl-3">
            <p className="text-sm font-medium text-slate-900">{call.name}</p>
            <p className="text-xs uppercase text-slate-500">{call.status}</p>
            {call.summary ? <p className="mt-1 text-sm text-slate-600">{call.summary}</p> : null}
          </div>
        ))}
      </div>
      <h3 className="mt-5 text-sm font-semibold text-slate-900">Retrieved Sources</h3>
      <div className="mt-3 space-y-2">
        {sources.length === 0 ? <p className="text-sm text-slate-500">Sources appear as research completes.</p> : null}
        {sources.map((source, index) => (
          <a
            key={`${source.url ?? source.source_id ?? index}`}
            href={source.url ?? "#"}
            className="block text-sm text-groove hover:underline"
          >
            {source.title ?? source.url ?? source.source_id ?? "Source"}
          </a>
        ))}
      </div>
    </aside>
  );
}
