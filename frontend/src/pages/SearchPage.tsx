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

export function SearchPage() {
  const [query, setQuery] = useState("hybrid retrieval improvements");
  const [repo, setRepo] = useState("");
  const [path, setPath] = useState("");
  const [headingPath, setHeadingPath] = useState("");
  const [contentType, setContentType] = useState("");
  const [licenseFamily, setLicenseFamily] = useState("");
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
    const request = {
      query: query.trim(),
      limit: 10,
      explain: explainScores,
      filters: Object.keys(filters).length > 0 ? filters : undefined,
      boosts: boostDocumentation ? { content_type: { documentation: 0.15 } } : undefined
    };

    try {
      const [searchResult, answerResult] = await Promise.all([
        search(request),
        answer(request)
      ]);
      setSearchData(searchResult);
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
          boostDocumentation,
          explainScores,
          repos: REPOS,
          contentTypes: CONTENT_TYPES,
          licenseFamilies: LICENSE_FAMILIES,
          onRepoChange: setRepo,
          onPathChange: setPath,
          onHeadingPathChange: setHeadingPath,
          onContentTypeChange: setContentType,
          onLicenseFamilyChange: setLicenseFamily,
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
        <AnswerPanel answer={answerData} isLoading={isLoading} />

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
