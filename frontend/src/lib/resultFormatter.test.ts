import {
  buildAnswerSummary,
  buildWhatNewSummary,
  dedupeClaims,
  formatAnswer,
  formatSearchResult,
  groupRelatedResults,
  normalizeDisplayMetadata,
  normalizeSourceMetadata
} from "./resultFormatter";
import { hybridRetrievalAnswer, hybridRetrievalSearch } from "../test/fixtures";

describe("resultFormatter", () => {
  it("selects the best source and separates supporting sources", () => {
    const model = formatAnswer(hybridRetrievalAnswer);

    expect(model.bestSource?.title).toBe("Ranking and reranking");
    expect(model.supportingSources).toHaveLength(1);
    expect(model.primaryEvidence?.role).toBe("primary");
    expect(model.supportingEvidence[0].title).toBe("Lab hybrid retrieval example");
    expect(model.explanation).toMatch(/two-stage retrieval pattern|hybrid retrieval/i);
    expect(model.supportingContext).toMatch(/Supporting evidence/i);
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
    expect(display.canonicalPath).toBe("Section: Documentation archive | File: archive.md | Repo: elastic/docs-content");
  });

  it("removes duplicated boilerplate snippets from formatted results", () => {
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
    expect(result.snippet).toBeUndefined();
    expect(result.display.cleanPath).not.toContain("Documentation archive > Documentation archive");
  });

  it("normalizes repeated rerank title and breadcrumb artifacts", () => {
    const display = normalizeSourceMetadata({
      title: "Elastic Rerank Elastic Rerank",
      heading_path: "Elastic Rerank > Elastic Rerank > Performance [ml-nlp-rerank-performance]",
      repo: "elastic/docs-content",
      path: "explore-analyze/machine-learning/nlp/ml-nlp-rerank.md"
    });

    expect(display.displayTitle).toBe("Elastic Rerank");
    expect(display.displaySection).toBe("Performance [ml-nlp-rerank-performance]");
    expect(display.canonicalPath).toBe(
      "Section: Performance [ml-nlp-rerank-performance] | File: explore-analyze/machine-learning/nlp/ml-nlp-rerank.md | Repo: elastic/docs-content"
    );
  });

  it("builds synthesized answer fields instead of reusing raw snippets", () => {
    const model = formatAnswer({
      ...hybridRetrievalAnswer,
      summary: "Performance Elastic Rerank shows significant improvements over raw retrieval.",
      direct_answer: "Performance Elastic Rerank shows significant improvements over raw retrieval."
    });

    expect(model.directAnswer).toMatch(/hybrid retrieval|rerank/i);
    expect(model.directAnswer).not.toMatch(/^Performance Elastic Rerank shows/);
    expect(buildAnswerSummary(hybridRetrievalAnswer, [model.primaryEvidence!])).toMatch(/hybrid retrieval/i);
    expect(buildWhatNewSummary(hybridRetrievalAnswer, [model.primaryEvidence!]).length).toBeGreaterThan(0);
  });

  it("suppresses evidence claims that repeat synthesized answer text", () => {
    const evidence = [formatAnswer(hybridRetrievalAnswer).primaryEvidence!];
    const deduped = dedupeClaims(evidence, [evidence[0].claim]);

    expect(deduped[0].claim).toBe("");
  });
});
