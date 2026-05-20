"use client";

import React from "react";
import { useEffect, useState } from "react";

type HealthState =
  | { status: "checking"; label: string }
  | { status: "ok"; label: string }
  | { status: "error"; label: string };

export function HealthPanel() {
  const [health, setHealth] = useState<HealthState>({
    status: "checking",
    label: "Checking API health"
  });

  useEffect(() => {
    const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

    fetch(`${apiBaseUrl}/health`)
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }

        const payload = (await response.json()) as { status?: string; service?: string };
        setHealth({
          status: "ok",
          label: `${payload.service ?? "API"} is ${payload.status ?? "ready"}`
        });
      })
      .catch(() => {
        setHealth({
          status: "error",
          label: "API health check unavailable"
        });
      });
  }, []);

  const color =
    health.status === "ok" ? "bg-groove" : health.status === "error" ? "bg-pulse" : "bg-slate-400";

  return (
    <div className="border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center gap-3">
        <span className={`h-3 w-3 rounded-full ${color}`} aria-hidden="true" />
        <p className="text-sm font-medium text-slate-900">{health.label}</p>
      </div>
    </div>
  );
}
