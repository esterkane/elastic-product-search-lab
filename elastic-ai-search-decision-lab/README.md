# Elastic AI Search Decision Lab

This compact lab evaluates conversational retrieval over six Markdown pages. It extends single-turn findability into turn-level evaluation where short follow-up turns use prior user intent as context.

No external LLM, embedding service, Elasticsearch, or OpenSearch cluster is required. The evaluator is intentionally local and deterministic so reports can be regenerated in a quick portfolio review.

## Data

- `content/pages/`: six Markdown pages with front matter.
- `data/conversations.json`: two three-turn conversations.
- Each turn has graded target-page judgments:
  - `3`: exact answer target
  - `2`: strong supporting page
  - `1`: weak supporting page
  - `0`: judged non-relevant page

## Method

The evaluator runs a simple lexical retrieval strategy over page title, topic, and body text. For first turns, the raw user query is evaluated directly. For follow-up turns, `decisionRouter.ts` expands the effective query with salient terms from prior turns.

This means a turn such as `How do I tune it?` is evaluated as a conversational turn about the previous hybrid-search question, not as an isolated query about the pronoun `it`.

Metrics:

- nDCG@5 for graded relevance quality.
- MRR@5 for first useful result position.
- Precision@3 for top-result density.
- Recall@5 for coverage of judged relevant pages.

## Run

```powershell
npm test
npm run evaluate
```

Outputs:

- `reports/conversation-eval-report.json`
- `reports/conversation-eval-report.md`

## Assumptions

- The corpus is deliberately small: six pages are enough to show turn-level mechanics, not production statistical confidence.
- Context expansion is deterministic and transparent. It is a stand-in for a production query rewrite component, not an LLM dependency.
- The report focuses on retrieval ranking quality, not answer generation or chatbot UX.
