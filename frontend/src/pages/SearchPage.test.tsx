import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { SearchPage } from "./SearchPage";
import { hybridRetrievalAnswer, hybridRetrievalSearch } from "../test/fixtures";
import { answer, search } from "../lib/api";

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return {
    ...actual,
    answer: vi.fn(),
    ingestRepo: vi.fn(),
    search: vi.fn()
  };
});

describe("SearchPage", () => {
  beforeEach(() => {
    vi.mocked(search).mockResolvedValue(hybridRetrievalSearch);
    vi.mocked(answer).mockResolvedValue(hybridRetrievalAnswer);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("does not show internal improvement suggestions in the default UI", () => {
    render(<SearchPage />);

    expect(screen.queryByText(/Improvement Suggestions/i)).not.toBeInTheDocument();
  });

  it("keeps advanced controls collapsed by default", () => {
    render(<SearchPage />);

    const advanced = screen.getByText("Advanced options").closest("details");
    expect(advanced).not.toHaveAttribute("open");
  });

  it("submits search and answer requests without calling analyze", async () => {
    render(<SearchPage />);

    fireEvent.click(screen.getByRole("button", { name: /Search/i }));

    await waitFor(() => {
      expect(search).toHaveBeenCalledWith(expect.objectContaining({ query: "hybrid retrieval improvements" }));
      expect(answer).toHaveBeenCalledWith(expect.objectContaining({ query: "hybrid retrieval improvements" }));
    });
    expect(screen.queryByText(/Improvement Suggestions/i)).not.toBeInTheDocument();
    expect(screen.getByText(/Hybrid retrieval improvements should combine lexical/i)).toBeInTheDocument();
  });

  it("renders the answer region before the results region", () => {
    render(<SearchPage />);

    const answerHeading = screen.getByRole("heading", { name: "Answer" });
    const resultsHeading = screen.getByRole("heading", { name: /Search Results/i });

    expect(answerHeading.compareDocumentPosition(resultsHeading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
