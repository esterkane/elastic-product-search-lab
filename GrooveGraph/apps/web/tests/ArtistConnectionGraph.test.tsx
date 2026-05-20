import React from "react";
import { render, screen } from "@testing-library/react";
import { ArtistConnectionGraph } from "../components/ArtistConnectionGraph";

describe("ArtistConnectionGraph", () => {
  it("renders graph nodes and relationship labels", () => {
    render(
      <ArtistConnectionGraph
        nodes={[
          { id: "radiohead", label: "Radiohead" },
          { id: "the-smile", label: "The Smile", group: "project" }
        ]}
        links={[{ source: "the-smile", target: "radiohead", label: "SIDE_PROJECT_OF" }]}
      />
    );

    expect(screen.getByRole("img", { name: "artist connection graph" })).toBeInTheDocument();
    expect(screen.getByText("Radiohead")).toBeInTheDocument();
    expect(screen.getByText("SIDE_PROJECT_OF")).toBeInTheDocument();
  });
});
