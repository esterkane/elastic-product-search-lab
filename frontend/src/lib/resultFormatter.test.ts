import { formatAnswer, formatSearchResult, groupRelatedResults, normalizeDisplayMetadata } from "./resultFormatter";
import { hybridRetrievalAnswer, hybridRetrievalSearch } from "../test/fixtures";

describe("resultFormatter", () => {
  it("selects the best source and separates supporting sources", () => {
    const model = formatAnswer(hybridRetrievalAnswer);

    expect(model.bestSource?.title).toBe("Ranking and reranking");
    expect(model.supportingSources).toHaveLength(1);
    expect(model.primaryEvidence?.role).toBe("primary");
    expect(model.supportingEvidence[0].title).toBe("Lab hybrid retrieval example");
  });

  it("groups the first hit as primary and keeps related matches secondary", () => {
    const result = groupRelatedResults([
      ...hybridRetrievalSearch.hits,
      { ...hybridRetrievalSearch.hits[0], id: "docs-2", title: "Semantic search" }
    ]);

    expect(result.primary?.id).toBe("docs-1");
    expect(result.related.map((hit) => hit.id)).toEqual(["docs-2"]);
  });

  it("normalizes repeated documentation archive headings and paths", () => {
    const display = normalizeDisplayMetadata({
      title: "Documentation archive",
      heading_path: "Documentation archive > Documentation archive",
      repo: "elastic/docs-content",
      path: "archive.md",
      sourceType: "documentation"
    });

    expect(display.title).toBe("Documentation archive");
    expect(display.section).toBe("Documentation archive");
    expect(display.cleanPath).toBe("Section: Documentation archive | archive.md | elastic/docs-content");
  });

  it("cleans duplicated snippet text from formatted results", () => {
    const result = formatSearchResult({
      id: "archive",
      title: "Documentation archive",
      heading_path: "Documentation archive > Documentation archive",
      repo: "elastic/docs-content",
      path: "archive.md",
      content_type: "documentation",
      license_family: "elastic-license",
      score: 0.02,
      source_url: "https://github.com/elastic/docs-content/blob/main/archive.md",
      snippet: "Documentation archive Documentation archive > Documentation archive documentation.",
      highlights: ["documentation"],
      match_reason: "Matched by keyword/BM25 evidence in Documentation archive > Documentation archive."
    });

    expect(result.title).toBe("Documentation archive");
    expect(result.snippet).toBe("Documentation archive.");
    expect(result.display.cleanPath).not.toContain("Documentation archive > Documentation archive");
  });
});
