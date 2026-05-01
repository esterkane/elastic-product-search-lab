import type { AnswerResponse, SearchResponse } from "../lib/api";

export const hybridRetrievalAnswer: AnswerResponse = {
  summary:
    "Hybrid retrieval improvements should combine lexical and semantic candidates first, then rerank the strongest evidence before presenting it.",
  evidence: [
    {
      title: "Ranking and reranking",
      heading_path: "Ranking and reranking > Two-stage retrieval pipelines",
      repo: "elastic/docs-content",
      path: "solutions/search/ranking.md",
      excerpt:
        "Hybrid retrieval improvements start with a first-stage candidate set and use reranking only on the strongest candidates.",
      highlight_terms: ["hybrid", "retrieval", "improvements"],
      reader_url: "https://www.elastic.co/docs/solutions/search/ranking#two-stage-retrieval-pipelines",
      source_url:
        "https://github.com/elastic/docs-content/blob/main/solutions/search/ranking.md#two-stage-retrieval-pipelines",
      link_label: "Read documentation"
    },
    {
      title: "Lab hybrid retrieval example",
      heading_path: "Lab > Hybrid retrieval",
      repo: "elastic/elasticsearch-labs",
      path: "supporting-blog-content/hybrid/README.md",
      excerpt:
        "Hybrid retrieval examples combine structured filtering with semantic search for better relevance in application workflows.",
      highlight_terms: ["hybrid", "retrieval"],
      reader_url:
        "https://github.com/elastic/elasticsearch-labs/blob/abc/supporting-blog-content/hybrid/README.md#hybrid-retrieval",
      source_url:
        "https://github.com/elastic/elasticsearch-labs/blob/abc/supporting-blog-content/hybrid/README.md#hybrid-retrieval",
      link_label: "View source"
    }
  ],
  links: [
    {
      title: "Ranking and reranking",
      url: "https://www.elastic.co/docs/solutions/search/ranking#two-stage-retrieval-pipelines",
      link_label: "Read documentation"
    },
    {
      title: "Lab hybrid retrieval example",
      url: "https://github.com/elastic/elasticsearch-labs/blob/abc/supporting-blog-content/hybrid/README.md#hybrid-retrieval",
      link_label: "View source"
    }
  ],
  warnings: [],
  degraded: false
};

export const hybridRetrievalSearch: SearchResponse = {
  hits: [
    {
      id: "docs-1",
      score: 0.88,
      title: "Ranking and reranking",
      repo: "elastic/docs-content",
      path: "solutions/search/ranking.md",
      heading_path: "Ranking and reranking > Two-stage retrieval pipelines",
      content_type: "documentation",
      license_family: "elastic-license",
      source_url:
        "https://github.com/elastic/docs-content/blob/main/solutions/search/ranking.md#two-stage-retrieval-pipelines",
      snippet:
        "Hybrid retrieval improvements start with a first-stage candidate set and use reranking only on the strongest candidates.",
      highlights: ["hybrid", "retrieval", "improvements"]
    }
  ],
  warnings: [],
  degraded: false
};
