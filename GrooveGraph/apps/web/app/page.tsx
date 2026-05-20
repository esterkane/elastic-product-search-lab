import React from "react";
import Link from "next/link";
import { HealthPanel } from "../components/HealthPanel";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50">
      <section className="mx-auto flex min-h-screen max-w-6xl flex-col justify-center px-6 py-12">
        <div className="max-w-3xl">
          <p className="text-sm font-semibold uppercase tracking-wide text-groove">GrooveGraph</p>
          <h1 className="mt-4 text-5xl font-semibold text-ink sm:text-6xl">
            Map bands, scenes, and listening paths without losing the thread.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-700">
            A fresh full-stack base for personal music discovery, artist research, and future agent workflows.
          </p>
        </div>
        <div className="mt-10 max-w-xl">
          <HealthPanel />
        </div>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/dashboard" className="bg-slate-950 px-4 py-2 text-sm font-medium text-white">
            Open dashboard
          </Link>
          <Link href="/chat" className="border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-800">
            Start research chat
          </Link>
        </div>
      </section>
    </main>
  );
}
