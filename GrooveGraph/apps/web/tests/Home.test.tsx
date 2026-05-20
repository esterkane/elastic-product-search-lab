import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import Home from "../app/page";

describe("Home", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ status: "ok", service: "groovegraph-api" })
      })
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the landing page and API health", async () => {
    render(<Home />);

    expect(screen.getByRole("heading", { name: /map bands/i })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("groovegraph-api is ok")).toBeInTheDocument();
    });
  });
});
