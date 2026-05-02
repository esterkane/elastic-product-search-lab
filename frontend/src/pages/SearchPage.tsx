import { FormEvent, useMemo, useState } from "react";
import { AlertCircle, CheckCircle2, Loader2, RefreshCw, Search } from "lucide-react";
import { AnswerPanel } from "../components/AnswerPanel";
import { ResultList } from "../components/ResultList";
import { SearchBar } from "../components/SearchBar";
import {
  answer,
  ingestRepo,
  search,
  type AnswerResponse,
  type ChangeTopic,
  type IngestRepoResponse,
  type QueryRequest,
  type RetrievalWarning,
  type SearchResponse,
  type TimeRange
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

const CHANGE_TOPICS: { value: ChangeTopic; label: string; queryTerms: string }[] = [
  { value: "relevance", label: "Relevance and ranking", queryTerms: "relevance ranking reranking scoring query rules" },
  { value: "ingestion", label: "Ingestion and pipelines", queryTerms: "ingest pipeline bulk indexing failure store data freshness" },
  { value: "data_modeling", label: "Data modeling and mappings", queryTerms: "mapping fields data modeling index templates" },
  { value: "performance", label: "Performance and scaling", queryTerms: "performance latency memory faster query indexing scaling" },
  { value: "resilience", label: "Resilience and recovery", queryTerms: "resilience recovery retries backoff circuit breaker failure" },
  { value: "esql", label: "ES|QL and query language", queryTerms: "ESQL ES|QL query language joins lookup" },
  { value: "vector_search", label: "Vector search", queryTerms: "vector search semantic dense kNN reranking inference" },
  { value: "search_applications", label: "Search applications", queryTerms: "search applications templates query rules" },
  { value: "observability", label: "Observability for search", queryTerms: "observability monitoring metrics profiling slow logs" },
  { value: "release_notes", label: "Release notes and breaking changes", queryTerms: "release notes breaking changes deprecations migration" }
];

const VERSIONS = ["9.2", "9.1", "9.0", "8.19", "8.18", "8.17", "8.16", "8.15", "8.14", "8.13", "8.12", "8.11", "8.10", "8.9", "8.8", "8.7", "8.6", "8.5", "8.4", "8.3", "8.2", "8.1", "8.0"];

const TIME_RANGES: { value: TimeRange; label: string }[] = [
  { value: "latest", label: "Latest first" },
  { value: "30d", label: "Last 30 days" },
  { value: "90d", label: "Last 90 days" },
  { value: "1y", label: "Last year" },
  { value: "all", label: "All time" }
];

export function SearchPage() {
  const [query, setQuery] = useState("hybrid retrieval improvements");
  const [repo, setRepo] = useState("");
  const [path, setPath] = useState("");
  const [headingPath, setHeadingPath] = useState("");
  const [contentType, setContentType] = useState("");
  const [licenseFamily, setLicenseFamily] = useState("");
  const [topic, setTopic] = useState<ChangeTopic | "">("vector_search");
  const [versionFrom, setVersionFrom] = useState("9.0");
  const [versionTo, setVersionTo] = useState("9.2");
  const [timeRange, setTimeRange] = useState<TimeRange>("latest");
  const [boostDocumentation, setBoostDocumentation] = useState(false);
  const [explainScores, setExplainScores] = useState(false);
  const [searchData, setSearchData] = useState<SearchResponse | null>(null);
  const [answerData, setAnswerData] = useState<AnswerResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexStatus, setIndexStatus] = useState<IngestRepoResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const retrievalWarnings = useMemo(
    () => uniqueWarnings([
      ...(searchData?.warnings ?? []),
      ...(answerData?.warnings ?? [])
    ]),
    [searchData, answerData]
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
    const releaseMode = isReleaseMode(query, topic, versionFrom, versionTo);
    const boosts: QueryRequest["boosts"] = {};
    if (boostDocumentation) {
      boosts.content_type = { documentation: 0.15 };
    }
    if (releaseMode) {
      boosts.path = { "release-notes": 0.25 };
      boosts.content_type = { ...(boosts.content_type ?? {}), release_note: 0.2, documentation: 0.1 };
    }
    const enrichedQuery = buildReleaseQuery(query.trim(), topic, versionFrom, versionTo, timeRange);
    const request: QueryRequest = {
      query: enrichedQuery,
      limit: 10,
      explain: explainScores,
      filters: Object.keys(filters).length > 0 ? filters : undefined,
      boosts: Object.keys(boosts).length > 0 ? boosts : undefined,
      topic,
      version_range: { ...(versionFrom ? { from: versionFrom } : {}), ...(versionTo ? { to: versionTo } : {}) },
      time_range: timeRange
    };

    try {
      const [searchOutcome, answerOutcome] = await Promise.allSettled([
        search(request),
        answer(request)
      ]);
      if (searchOutcome.status === "fulfilled") {
        setSearchData(searchOutcome.value);
      } else {
        setSearchData(null);
      }
      if (answerOutcome.status === "fulfilled") {
        setAnswerData(answerOutcome.value);
      } else {
        setAnswerData(null);
      }
      if (searchOutcome.status === "rejected") {
        throw searchOutcome.reason;
      }
      if (answerOutcome.status === "rejected") {
        setError("Search results loaded, but answer synthesis did not respond. Showing ranked evidence instead.");
      }
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
          <h1>Search and Explain</h1>
        </div>
        <button className="sync-button" type="button" onClick={handleIndexChanges} disabled={isIndexing}>
          {isIndexing ? <Loader2 aria-hidden="true" className="spin" size={18} /> : <RefreshCw aria-hidden="true" size={18} />}
          <span>{isIndexing ? "Indexing" : "Sync & index changes"}</span>
        </button>
      </header>

      <SearchBar
        query={query}
        onQueryChange={setQuery}
        onSubmit={handleSubmit}
        isLoading={isLoading}
        advanced={{
          repo,
          path,
          headingPath,
          contentType,
          licenseFamily,
          topic,
          versionFrom,
          versionTo,
          timeRange,
          boostDocumentation,
          explainScores,
          repos: REPOS,
          contentTypes: CONTENT_TYPES,
          licenseFamilies: LICENSE_FAMILIES,
          topics: CHANGE_TOPICS,
          versions: VERSIONS,
          timeRanges: TIME_RANGES,
          onRepoChange: setRepo,
          onPathChange: setPath,
          onHeadingPathChange: setHeadingPath,
          onContentTypeChange: setContentType,
          onLicenseFamilyChange: setLicenseFamily,
          onTopicChange: setTopic,
          onVersionFromChange: setVersionFrom,
          onVersionToChange: setVersionTo,
          onTimeRangeChange: setTimeRange,
          onBoostDocumentationChange: setBoostDocumentation,
          onExplainScoresChange: setExplainScores
        }}
      />

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

      <div className="answer-results-grid">
        <AnswerPanel answer={answerData} searchHits={searchData?.hits ?? []} isLoading={isLoading} />

        <section className="panel results-panel" aria-labelledby="results-heading">
          <div className="panel-heading">
            <Search aria-hidden="true" size={18} />
            <h2 id="results-heading">Search Results</h2>
          </div>
          <ResultList hits={searchData?.hits ?? []} />
        </section>
      </div>
    </main>
  );
}

function buildReleaseQuery(query: string, topic: ChangeTopic | "", versionFrom: string, versionTo: string, timeRange: TimeRange): string {
  const topicTerms = CHANGE_TOPICS.find((item) => item.value === topic)?.queryTerms;
  const versionTerms = [versionFrom, versionTo].filter(Boolean).map((version) => `Elasticsearch ${version}`).join(" ");
  const wantsChange = isReleaseMode(query, topic, versionFrom, versionTo);
  return [
    query,
    wantsChange ? "what changed what is new release notes engineering impact" : null,
    topicTerms,
    versionTerms,
    timeRange === "latest" ? "latest 9.x 8.x" : null,
    !/\bserverless\b/i.test(query) ? "-serverless" : null
  ].filter(Boolean).join(" ");
}

function isReleaseMode(query: string, topic: ChangeTopic | "", versionFrom: string, versionTo: string): boolean {
  return Boolean(topic || versionFrom || versionTo || /\b(new|changed|latest|release|8\.|9\.|version)\b/i.test(query));
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
