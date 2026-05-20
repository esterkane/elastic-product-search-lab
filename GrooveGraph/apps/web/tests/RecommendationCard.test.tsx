import React from "react";
import { render, screen } from "@testing-library/react";
import { RecommendationCard } from "../components/RecommendationCard";

describe("RecommendationCard", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows why a recommendation was made", () => {
    render(
      <RecommendationCard
        recommendation={{
          id: "rec-1",
          type: "artist",
          name: "Pixies",
          artist_name: null,
          score: 0.91,
          confidence: 0.91,
          reason_bullets: ["Similar to followed artists.", "Graph relationships support this connection."],
          source_evidence: [{ title: "Last.fm", url: "https://last.fm" }],
          seed_explanation: "Connected to artist Radiohead.",
          actions: ["save", "hide", "research", "add_to_playlist"]
        }}
      />
    );

    expect(screen.getByText("Why this was recommended")).toBeInTheDocument();
    expect(screen.getByText("Similar to followed artists.")).toBeInTheDocument();
    expect(screen.getByText("Connected to artist Radiohead.")).toBeInTheDocument();
    expect(screen.getByText("Last.fm")).toBeInTheDocument();
  });
});
