"use client";

import React, { FormEvent, useState } from "react";
import type { Citation, ToolCall } from "../lib/api";
import { streamChat } from "../lib/api";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { ToolCallTimeline } from "./ToolCallTimeline";
import { DebugDrawer } from "./DebugDrawer";

type ChatMessage = { role: "user" | "assistant"; content: string };

export function ChatPanel({ initialSessionId = "web-session" }: { initialSessionId?: string }) {
  const [sessionId] = useState(initialSessionId);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState("Idle");
  const [partial, setPartial] = useState("");
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([]);
  const [sources, setSources] = useState<Citation[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [debugEvents, setDebugEvents] = useState<unknown[]>([]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = input.trim();
    if (!message) {
      return;
    }
    setMessages((current) => [...current, { role: "user", content: message }]);
    setInput("");
    setStatus("thinking");
    setPartial("");
    setDebugEvents([]);

    await streamChat(sessionId, message, (streamEvent) => {
      setDebugEvents((current) => [...current, streamEvent]);
      if (streamEvent.event === "thinking") {
        setStatus(String(streamEvent.message ?? "thinking"));
      }
      if (streamEvent.event === "node") {
        const node = String(streamEvent.node ?? "agent");
        setStatus(node === "answer_synthesis" ? "writing" : "researching");
        const data = streamEvent.data ?? {};
        const calls = Array.isArray(data.tool_calls) ? data.tool_calls : [];
        calls.forEach((rawCall) => {
          const call = rawCall as { tool_name?: string; result?: string; run_id?: string };
          setToolCalls((current) => [
            ...current,
            {
              id: `${call.run_id ?? "run"}-${call.tool_name ?? node}-${current.length}`,
              name: call.tool_name ?? node,
              status: "completed",
              summary: call.result ?? ""
            }
          ]);
        });
        const nextCitations = Array.isArray(data.citations) ? (data.citations as Citation[]) : [];
        if (nextCitations.length) {
          setSources(nextCitations);
        }
      }
      if (streamEvent.event === "tool_call") {
        const call: ToolCall = (streamEvent.tool_call as ToolCall | undefined) ?? {
          id: `${Date.now()}`,
          name: String(streamEvent.tool_name ?? "tool"),
          status: "completed" as const,
          summary: String(streamEvent.result_summary ?? "")
        };
        setToolCalls((current) => [...current, call]);
        setStatus("researching");
      }
      if (streamEvent.event === "retrieved_source" && streamEvent.source) {
        const source = streamEvent.source as Citation;
        setSources((current) => [...current, source]);
      }
      if (streamEvent.event === "partial") {
        setPartial((current) => current + String(streamEvent.text ?? streamEvent.delta ?? ""));
      }
      if (streamEvent.event === "final") {
        const answer = String(streamEvent.answer ?? partial);
        setMessages((current) => [...current, { role: "assistant", content: answer }]);
        setCitations((streamEvent.citations as Citation[] | undefined) ?? []);
        setStatus("done");
        setPartial("");
      }
      if (streamEvent.event === "answer") {
        const answer = String(streamEvent.data?.answer ?? partial);
        setMessages((current) => [...current, { role: "assistant", content: answer }]);
        setCitations(streamEvent.data?.citations ?? []);
        setStatus("done");
        setPartial("");
      }
    });
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
      <section className="border border-slate-200 bg-white p-4">
        <div className="min-h-[360px] space-y-4" aria-label="chat transcript">
          {messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={message.role === "user" ? "text-right" : "text-left"}>
              <p className={`inline-block max-w-[80%] px-3 py-2 text-sm leading-6 ${message.role === "user" ? "bg-slate-950 text-white" : "bg-slate-100 text-slate-800"}`}>
                {message.content}
              </p>
            </div>
          ))}
          {partial ? <p className="inline-block max-w-[80%] bg-slate-100 px-3 py-2 text-sm leading-6 text-slate-800">{partial}</p> : null}
        </div>
        <p className="mt-3 text-sm text-slate-500" aria-live="polite">{status}</p>
        <form onSubmit={(event) => void submit(event)} className="mt-4 flex gap-2">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            className="min-w-0 flex-1 border border-slate-300 px-3 py-2 text-sm"
            placeholder="Ask about a band, side project, lyrics context, or concert"
            aria-label="message"
          />
          <button type="submit" className="bg-groove px-4 py-2 text-sm font-medium text-white">
            Send
          </button>
        </form>
        <div className="mt-4">
          <EvidenceDrawer citations={citations} />
        </div>
      </section>
      <ToolCallTimeline toolCalls={toolCalls} sources={sources} />
      <div className="lg:col-span-2">
        <DebugDrawer data={{ sessionId, status, toolCalls, sources, citations, events: debugEvents }} />
      </div>
    </div>
  );
}
