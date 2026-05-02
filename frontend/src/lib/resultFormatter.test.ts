import { formatAnswer, groupRelatedResults } from "./resultFormatter";
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
});
