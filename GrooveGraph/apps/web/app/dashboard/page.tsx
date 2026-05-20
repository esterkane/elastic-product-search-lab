import React from "react";
import Link from "next/link";
import { AppShell, PageHeader } from "../../components/AppShell";
import { HealthPanel } from "../../components/HealthPanel";
import { SpotifyConnectStatus } from "../../components/SpotifyConnectStatus";

export default function DashboardPage() {
  return (
    <AppShell>
      <PageHeader title="Dashboard" subtitle="A compact command center for discovery, research, recommendations, and live music." />
      <div className="grid gap-4 lg:grid-cols-3">
        <HealthPanel />
        <SpotifyConnectStatus />
        <section className="border border-slate-200 bg-white p-4">
          <h2 className="text-sm font-semibold text-slate-900">Next Actions</h2>
          <div className="mt-3 grid gap-2 text-sm">
            <Link className="text-groove hover:underline" href="/chat">Research a band</Link>
            <Link className="text-groove hover:underline" href="/recommendations">Generate recommendations</Link>
            <Link className="text-groove hover:underline" href="/concerts">Find concerts</Link>
          </div>
        </section>
      </div>
    </AppShell>
  );
}
