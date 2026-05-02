# Contributing

Thanks for helping improve Elastic Repo Inventory. This project is intentionally strict about provenance, licensing, and deterministic evaluation because search quality is only useful when evidence can be audited.

## Branching

- Create feature branches from `main`.
- Use short, descriptive branch names such as `codex/incremental-indexing` or `fix/source-attribution`.
- Keep changes scoped to one feature or bug fix when possible.
- Do not commit generated source repositories under `sources/` or local artifacts under `artifacts/`.

## Local Checks

Before opening a pull request, run the relevant checks:

```powershell
python -m pytest -p no:cacheprovider
```

```powershell
cd frontend
npm install
npm run build
```

```powershell
docker compose config --quiet
```

For service-level validation:

```powershell
docker compose up -d --build
```

Then verify:

- API health returns `ok`.
- The frontend loads at `http://localhost:5173`.
- A small ingestion request is idempotent when repeated.

## Provenance Rules

All ingestion, retrieval, answer, and release-intelligence changes must preserve canonical source metadata:

- `repo`
- `repo_url`
- `path`
- `source_url`
- `commit_sha`
- `content_type`
- `license_family`

Do not generate an answer, release briefing, or evaluation fixture that cannot be traced back to direct source links. If content is transformed, chunked, summarized, embedded, reranked, or fused, the source URL and license family must remain attached to the derived record.

## Licensing Rules

- Keep source repository license families in indexed metadata.
- Treat unknown licenses conservatively.
- Do not blend evidence across license families without retaining per-source attribution.
- Do not copy large source excerpts into tests or docs. Prefer short snippets, hashes, paths, and source URLs.

## Deterministic Evaluation Rules

- Evaluation queries and expected judgments should be stable and reviewable.
- Sort ties deterministically by score and ID.
- Avoid tests that depend on live model randomness.
- Prefer mocked embedding/reranking responses in unit tests.
- Report NDCG@10, MRR@10, and Recall@20 for retrieval-quality changes.
- Include topic and version-range expectations for release-intelligence changes.
- Keep serverless-focused results out of the primary answer unless the query or filter explicitly asks for serverless.

## Pull Request Expectations

A pull request should include:

- Summary of user-facing behavior changes.
- Tests or a clear explanation of why tests were not added.
- Notes about provenance, attribution, and license handling.
- Golden-query notes for retrieval, answer synthesis, topic classification, or version filtering changes.
