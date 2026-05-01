import { FormEvent, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, RefreshCw, Search } from "lucide-react";
import { ResultCard } from "../components/ResultCard";
import { RecommendationPanel } from "../components/RecommendationPanel";
import { SourceList } from "../components/SourceList";
import {
  analyze,
  answer,
  ingestRepo,
  search,
  type AnalyzeResponse,
  type AnswerResponse,
  type Category,
  type IngestRepoResponse,
  type RetrievalWarning,
  type SearchResponse
} from "../lib/api";

const REPOS = [
  "elastic/docs-content",
  "elastic/elasticsearch-labs",
  "elastic/labs-releases"
];

const CONTENT_TYPES = [
  "documentation",
  "guide",
  "reference",
  "troubleshooting",
  "release_note",
  "example",
  "lab",
  "release_metadata"
];

const LICENSE_FAMILIES = ["elastic-license", "apache-2.0", "unknown"];

const DEFAULT_CATEGORIES: Category[] = ["relevance", "ingestion", "mapping", "performance", "resiliency"];

export function SearchPage() {
  const [query, setQuery] = useState("hybrid retrieval improvements");
  const [repo, setRepo] = useState("");
  const [path, setPath] = useState("");
  const [headingPath, setHeadingPath] = useState("");
  const [contentType, setContentType] = useState("");
  const [licenseFamily, setLicenseFamily] = useState("");
  const [boostDocumentation, setBoostDocumentation] = useState(false);
  const [explainScores, setExplainScores] = useState(false);
  const [category, setCategory] = useState<Category | "all">("all");
  const [searchData, setSearchData] = useState<SearchResponse | null>(null);
  const [analysisData, setAnalysisData] = useState<AnalyzeResponse | null>(null);
  const [answerData, setAnswerData] = useState<AnswerResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexStatus, setIndexStatus] = useState<IngestRepoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const categories = useMemo(
    () => searchData?.recommendation_categories ?? DEFAULT_CATEGORIES,
    [searchData]
  );
  const retrievalWarnings = useMemo(
    () => uniqueWarnings([
      ...(searchData?.warnings ?? []),
      ...(analysisData?.warnings ?? []),
      ...(answerData?.warnings ?? [])
    ]),
    [searchData, analysisData, answerData]
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!query.trim()) {
      setError("Enter a query before searching.");
      return;
    }

    setIsLoading(true);
    setError(null);
    const filters = {
      ...(repo ? { repo } : {}),
      ...(path ? { path } : {}),
      ...(headingPath ? { heading_path: headingPath } : {}),
      ...(contentType ? { content_type: contentType } : {}),
      ...(licenseFamily ? { license_family: licenseFamily } : {})
    };
    const request = {
      query: query.trim(),
      limit: 10,
      explain: explainScores,
      filters: Object.keys(filters).length > 0 ? filters : undefined,
      boosts: boostDocumentation ? { content_type: { documentation: 0.15 } } : undefined
    };

    try {
      const [searchResult, analysisResult, answerResult] = await Promise.all([
        search(request),
        analyze(request),
        answer(request)
      ]);
      setSearchData(searchResult);
      setAnalysisData(analysisResult);
      setAnswerData(answerResult);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Search failed.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleIndexChanges() {
    setIsIndexing(true);
    setError(null);
    setIndexStatus(null);

    try {
      const result = await ingestRepo({
        ...(repo ? { repo } : {}),
        force: false,
        update_sources: true
      });
      setIndexStatus(result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Indexing failed.");
    } finally {
      setIsIndexing(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Elastic repo intelligence</p>
          <h1>Search, Explain, Improve</h1>
        </div>
        <button className="sync-button" type="button" onClick={handleIndexChanges} disabled={isIndexing}>
          {isIndexing ? <Loader2 aria-hidden="true" className="spin" size={18} /> : <RefreshCw aria-hidden="true" size={18} />}
          <span>{isIndexing ? "Indexing" : "Sync & index changes"}</span>
        </button>
      </header>

      <form className="search-form" onSubmit={handleSubmit}>
        <label className="query-field">
          <span>Query</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ask about search, ingestion, mappings, or resiliency"
          />
        </label>

        <div className="filter-row">
          <label>
            <span>Repo</span>
            <select value={repo} onChange={(event) => setRepo(event.target.value)}>
              <option value="">All repos</option>
              {REPOS.map((item) => (
                <option value={item} key={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>License</span>
            <select value={licenseFamily} onChange={(event) => setLicenseFamily(event.target.value)}>
              <option value="">All licenses</option>
              {LICENSE_FAMILIES.map((item) => (
                <option value={item} key={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>

          <label>
            <span>Content type</span>
            <select value={contentType} onChange={(event) => setContentType(event.target.value)}>
              <option value="">All types</option>
              {CONTENT_TYPES.map((item) => (
                <option value={item} key={item}>
                  {item}
                </option>
              ))}
            </select>
          </label>

          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={explainScores}
              onChange={(event) => setExplainScores(event.target.checked)}
            />
            <span>Explain scores</span>
          </label>

          <label className="checkbox-field">
            <input
              type="checkbox"
              checked={boostDocumentation}
              onChange={(event) => setBoostDocumentation(event.target.checked)}
            />
            <span>Boost docs</span>
          </label>

          <button type="submit" disabled={isLoading}>
            {isLoading ? <Loader2 aria-hidden="true" className="spin" size={18} /> : <Search aria-hidden="true" size={18} />}
            <span>{isLoading ? "Searching" : "Search"}</span>
          </button>
        </div>

        <div className="metadata-row">
          <label>
            <span>Path</span>
            <input
              value={path}
              onChange={(event) => setPath(event.target.value)}
              placeholder="solutions/search/ranking/semantic-reranking.md"
            />
          </label>

          <label>
            <span>Heading</span>
            <input
              value={headingPath}
              onChange={(event) => setHeadingPath(event.target.value)}
              placeholder="Semantic reranking [semantic-reranking]"
            />
          </label>
        </div>
      </form>

      {error && (
        <div className="alert" role="alert">
          <AlertCircle aria-hidden="true" size={18} />
          <span>{error}</span>
        </div>
      )}

      {indexStatus && (
        <div className="alert alert-success" role="status">
          <CheckCircle2 aria-hidden="true" size={18} />
          <span>
            {indexStatus.message} {indexStatus.repos_scanned} repos, {indexStatus.documents_scanned} docs,{" "}
            {indexStatus.new_chunks} new chunks, {indexStatus.updated_chunks} updated chunks.
          </span>
        </div>
      )}

      {retrievalWarnings.length > 0 && (
        <div className="warning-stack" role="status" aria-label="Retrieval warnings">
          {retrievalWarnings.map((warning) => (
            <div className="alert alert-warning" key={`${warning.stage}-${warning.code}`}>
              <AlertCircle aria-hidden="true" size={18} />
              <span>{warning.message}</span>
            </div>
          ))}
        </div>
      )}

      <div className="workspace-grid">
        <section className="panel" aria-labelledby="results-heading">
          <div className="panel-heading">
            <Search aria-hidden="true" size={18} />
            <h2 id="results-heading">Search Results</h2>
          </div>
          {searchData?.hits.length ? (
            <div className="result-stack">
              {searchData.hits.map((result) => (
                <ResultCard key={result.id} result={result} />
              ))}
            </div>
          ) : (
            <p className="empty-state">Run a search to see ranked evidence.</p>
          )}
        </section>

        <section className="panel answer-panel" aria-labelledby="answer-heading">
          <h2 id="answer-heading">Answer With Evidence</h2>
          <p className="answer-text">
            {answerData?.summary ?? "Answers will appear here with direct source attributions."}
          </p>
          {answerData?.evidence?.length ? (
            <div className="answer-evidence" aria-label="Grounded evidence">
              {answerData.evidence.map((item) => (
                <article className="answer-evidence__item" key={`${item.title}-${item.source_url}`}>
                  <h3>{item.title}</h3>
                  <p className="result-location">
                    {[item.heading_path, item.path, item.repo].filter(Boolean).join(" - ")}
                  </p>
                  <blockquote className="evidence-snippet">
                    {renderEvidenceExcerpt(item.excerpt, item.highlight_terms)}
                  </blockquote>
                  <div className="answer-evidence__links">
                    <a href={item.reader_url} target="_blank" rel="noreferrer">
                      {item.link_label}
                    </a>
                    <a href={item.source_url} target="_blank" rel="noreferrer">
                      View source
                    </a>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <SourceList sources={answerData?.links ?? []} />
          )}
        </section>
      </div>

      <RecommendationPanel
        categories={categories}
        recommendations={analysisData?.recommendations ?? []}
        selectedCategory={category}
        onCategoryChange={setCategory}
      />
    </main>
  );
}

function uniqueWarnings(warnings: RetrievalWarning[]): RetrievalWarning[] {
  const seen = new Set<string>();
  return warnings.filter((warning) => {
    const key = `${warning.stage}:${warning.code}`;
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function renderEvidenceExcerpt(excerpt: string, highlights: string[]) {
  if (highlights.length === 0) {
    return excerpt;
  }
  const pattern = new RegExp(`(${highlights.map(escapeRegExp).join("|")})`, "gi");
  return excerpt.split(pattern).map((part, index) => {
    const marked = highlights.some((term) => term.toLowerCase() === part.toLowerCase());
    return marked ? <mark key={`${part}-${index}`}>{part}</mark> : part;
  });
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
