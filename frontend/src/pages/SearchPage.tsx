import { FormEvent, useMemo, useState } from "react";
import { AlertCircle, Loader2, Search } from "lucide-react";
import { ResultCard } from "../components/ResultCard";
import { RecommendationPanel } from "../components/RecommendationPanel";
import { SourceList } from "../components/SourceList";
import {
  analyze,
  answer,
  search,
  type AnalyzeResponse,
  type AnswerResponse,
  type Category,
  type SearchResponse
} from "../lib/api";

const REPOS = [
  "elastic/docs-content",
  "elastic/docs-builder",
  "elastic/docs",
  "elastic/elasticsearch-labs",
  "elastic/labs-releases"
];

const CONTENT_TYPES = [
  "documentation",
  "guide",
  "reference",
  "troubleshooting",
  "release_note",
  "tooling",
  "example",
  "lab",
  "release_metadata"
];

const DEFAULT_CATEGORIES: Category[] = ["relevance", "ingestion", "mapping", "performance", "resiliency"];

export function SearchPage() {
  const [query, setQuery] = useState("hybrid retrieval improvements");
  const [repo, setRepo] = useState("");
  const [contentType, setContentType] = useState("");
  const [category, setCategory] = useState<Category | "all">("all");
  const [searchData, setSearchData] = useState<SearchResponse | null>(null);
  const [analysisData, setAnalysisData] = useState<AnalyzeResponse | null>(null);
  const [answerData, setAnswerData] = useState<AnswerResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const categories = useMemo(
    () => searchData?.recommendation_categories ?? DEFAULT_CATEGORIES,
    [searchData]
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
      ...(contentType ? { content_type: contentType } : {})
    };
    const request = {
      query: query.trim(),
      limit: 10,
      filters: Object.keys(filters).length > 0 ? filters : undefined
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

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Elastic repo intelligence</p>
          <h1>Search, Explain, Improve</h1>
        </div>
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

          <button type="submit" disabled={isLoading}>
            {isLoading ? <Loader2 aria-hidden="true" className="spin" size={18} /> : <Search aria-hidden="true" size={18} />}
            <span>{isLoading ? "Searching" : "Search"}</span>
          </button>
        </div>
      </form>

      {error && (
        <div className="alert" role="alert">
          <AlertCircle aria-hidden="true" size={18} />
          <span>{error}</span>
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
            {answerData?.answer ?? "Answers will appear here with direct source attributions."}
          </p>
          <SourceList sources={answerData?.sources ?? []} />
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
