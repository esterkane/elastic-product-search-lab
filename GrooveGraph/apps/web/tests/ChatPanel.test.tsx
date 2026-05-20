import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ChatPanel } from "../components/ChatPanel";
import { parseSseEvent } from "../lib/api";

function streamFrom(text: string) {
  return new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(text));
      controller.close();
    }
  });
}

describe("ChatPanel", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses SSE events", () => {
    expect(parseSseEvent('event: partial\ndata: {"event":"partial","text":"hello"}')).toEqual({
      event: "partial",
      text: "hello"
    });
  });

  it("displays partial events, tool calls, sources, and final citations", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        body: streamFrom(
          [
            'event: thinking\ndata: {"event":"thinking","message":"thinking"}',
            'event: tool_call\ndata: {"event":"tool_call","tool_call":{"id":"1","name":"web_research","status":"completed","summary":"searched sources"}}',
            'event: retrieved_source\ndata: {"event":"retrieved_source","source":{"title":"Radiohead source","url":"https://example.com"}}',
            'event: partial\ndata: {"event":"partial","text":"Radiohead formed"}',
            'event: final\ndata: {"event":"final","answer":"Radiohead formed in Oxford.","citations":[{"title":"Band history","url":"https://example.com/history"}]}'
          ].join("\n\n")
        )
      })
    );

    render(<ChatPanel initialSessionId="test-session" />);
    fireEvent.change(screen.getByLabelText("message"), { target: { value: "Tell me about Radiohead" } });
    fireEvent.submit(screen.getByRole("button", { name: "Send" }).closest("form") as HTMLFormElement);

    await waitFor(() => {
      expect(screen.getByText("Radiohead formed in Oxford.")).toBeInTheDocument();
    });
    expect(screen.getByText("web_research")).toBeInTheDocument();
    expect(screen.getByText("Radiohead source")).toBeInTheDocument();
    expect(screen.getByText("Band history")).toBeInTheDocument();
  });
});
