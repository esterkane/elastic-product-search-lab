"use client";

import React from "react";

export function DebugDrawer({ title = "Run Debug", data }: { title?: string; data: unknown }) {
  if (process.env.NODE_ENV === "production") {
    return null;
  }
  return (
    <details className="border border-slate-200 bg-white p-4">
      <summary className="cursor-pointer text-sm font-semibold text-slate-900">{title}</summary>
      <pre className="mt-3 max-h-80 overflow-auto bg-slate-950 p-3 text-xs text-slate-100">
        {JSON.stringify(data, null, 2)}
      </pre>
    </details>
  );
}
