export const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8100";

export type Citation = {
  title?: string;
  url?: string;
  source_id?: string;
  quote?: string;
};

export type ToolCall = {
  id: string;
  name: string;
  status: "started" | "completed" | "error";
  summary?: string;
};

export type StreamEvent =
  | { event: "thinking"; message?: string }
  | { event: "node"; node?: string; data?: Record<string, unknown> }
  | { event: "tool_call"; tool_call?: ToolCall; tool_name?: string; result_summary?: string }
  | { event: "retrieved_source"; source?: Citation }
  | { event: "partial"; text?: string; delta?: string }
  | { event: "answer"; data?: { answer?: string; citations?: Citation[] } }
  | { event: "final"; answer?: string; citations?: Citation[]; tool_calls?: ToolCall[] }
  | { event: string; [key: string]: unknown };

export type Recommendation = {
  id: string;
  type: "track" | "artist";
  name?: string;
  artist_name?: string | null;
  score: number;
  confidence: number;
  reason_bullets: string[];
  source_evidence: Citation[];
  seed_explanation: string;
  actions: string[];
};

export type Concert = {
  id: string;
  title: string;
  starts_at?: string | null;
  venue?: { name: string; city?: string | null; country?: string | null } | null;
  city?: string | null;
  country?: string | null;
  ticket_url?: string | null;
  source_url?: string | null;
  lineup: string[];
  confidence: number;
  source_status: "current" | "historical";
};

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`);
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`API returned ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function streamChat(
  sessionId: string,
  message: string,
  onEvent: (event: StreamEvent) => void
): Promise<void> {
  const response = await fetch(`${apiBaseUrl}/chat/${encodeURIComponent(sessionId)}/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message })
  });
  if (!response.ok || !response.body) {
    throw new Error(`Chat stream failed with ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() ?? "";
    for (const part of parts) {
      const parsed = parseSseEvent(part);
      if (parsed) {
        onEvent(parsed);
      }
    }
  }
  const parsed = parseSseEvent(buffer);
  if (parsed) {
    onEvent(parsed);
  }
}

export function parseSseEvent(chunk: string): StreamEvent | null {
  const dataLine = chunk
    .split("\n")
    .map((line) => line.trim())
    .find((line) => line.startsWith("data:"));
  if (!dataLine) {
    return null;
  }
  try {
    return JSON.parse(dataLine.slice(5).trim()) as StreamEvent;
  } catch {
    return null;
  }
}
