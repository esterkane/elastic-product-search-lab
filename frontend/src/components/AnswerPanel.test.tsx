import { render, screen, within } from "@testing-library/react";
import { AnswerPanel } from "./AnswerPanel";
import { hybridRetrievalAnswer } from "../test/fixtures";

describe("AnswerPanel", () => {
  it("renders a grounded summary, confidence, and highlighted evidence", () => {
    const { container } = render(<AnswerPanel answer={hybridRetrievalAnswer} />);

    expect(screen.getByText(/Use hybrid retrieval to gather candidates/i)).toBeInTheDocument();
    expect(screen.getByText(/two-stage retrieval pattern/i)).toBeInTheDocument();
    expect(screen.getByText("high confidence")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "What to look for" })).toBeInTheDocument();
    expect(screen.getByText(/Look for the split between first-stage retrieval/i)).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Related sources" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Read first" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Ranking and reranking" })).toBeInTheDocument();
    expect(screen.queryByText(/matched by|semantic evidence|keyword\/BM25|primary proof|supporting context/i)).not.toBeInTheDocument();
    expect(container.querySelectorAll("mark").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Hybrid", { selector: "mark" })).toHaveLength(2);
  });

  it("labels docs-content reader links as documentation links", () => {
    render(<AnswerPanel answer={hybridRetrievalAnswer} />);

    const docsEvidence = screen.getByRole("heading", { name: "Ranking and reranking" }).closest("article");
    expect(docsEvidence).not.toBeNull();
    expect(within(docsEvidence!).getByRole("link", { name: /Read docs/i })).toHaveAttribute(
      "href",
      "https://www.elastic.co/docs/solutions/search/ranking#two-stage-retrieval-pipelines"
    );
  });

  it("labels non-docs-content evidence links as source links", () => {
    render(<AnswerPanel answer={hybridRetrievalAnswer} />);

    const labLink = screen.getAllByRole("link", { name: /Open source/i }).find((link) =>
      link.getAttribute("href")?.includes("elasticsearch-labs")
    );

    expect(labLink).toHaveAttribute(
      "href",
      "https://github.com/elastic/elasticsearch-labs/blob/abc/supporting-blog-content/hybrid/README.md#hybrid-retrieval"
    );
  });
});
