import type { AnswerResponse, SearchHit, Source } from "./api";

export type ConfidenceLevel = "high" | "medium" | "low";

export type FormattedEvidence = AnswerResponse["evidence"][number] & {
  claim: string;
  concept: string;
  takeaway: string;
  whatToLookFor: string;
  sourceType: SourceKind;
  topic: ChangeTopicName;
  version?: string;
  date?: string;
  role: "primary" | "supporting";
  tags: string[];
  display: DisplayMetadata;
};

export type AnswerViewModel = {
  directAnswer: string;
  explanation: string;
  whatNew: string[];
  important: string;
  keyTakeaways: string[];
  whatToNotice: string[];
  supportingContext: string;
  confidence: ConfidenceLevel;
  bestSource: FormattedSource | null;
  supportingSources: FormattedSource[];
  primaryEvidence: FormattedEvidence | null;
  supportingEvidence: FormattedEvidence[];
  sourceNavigator: FormattedSource[];
};

export type DisplayMetadata = {
  title: string;
  section?: string;
  repo?: string;
  filePath?: string;
  sourceType?: string;
  cleanPath: string;
  displayTitle: string;
  displaySection?: string;
  displayFile?: string;
  displayRepo?: string;
  canonicalPath: string;
};

export type FormattedSource = Source & {
  display: DisplayMetadata;
};

export type NormalizedSearchResult = SearchHit & {
  display: DisplayMetadata;
  concept: string;
  explanation: string;
  takeaway: string;
  whatToLookFor: string;
  sourceType: SourceKind;
  topic: ChangeTopicName;
  version?: string;
  date?: string;
  links: {
    source: string;
  };
};

export type SearchResult = NormalizedSearchResult;
export type SourceKind = "procedural" | "conceptual" | "troubleshooting" | "performance" | "reference" | "example";
export type ChangeTopicName =
  | "relevance"
  | "ingestion"
  | "data_modeling"
  | "performance"
  | "resilience"
  | "esql"
  | "vector_search"
  | "search_applications"
  | "observability"
  | "release_notes";

export function formatAnswer(answer: AnswerResponse | null): AnswerViewModel {
  const rawEvidence = prioritizeEvidence((answer?.evidence ?? []).map(formatEvidence));
  const bestSource = selectPrimarySource(answer, rawEvidence);
  const synthesis = {
    answer: buildAnswerSummary(answer, rawEvidence),
    explanation: buildExplanationSummary(answer, rawEvidence),
    whatNew: buildWhatNewSummary(answer, rawEvidence),
    whyItMatters: buildWhyItMattersSummary(answer, rawEvidence),
    supportingContext: buildSupportingContext(rawEvidence)
  };
  const evidence = dedupeClaims(rawEvidence, [
    synthesis.answer,
    synthesis.explanation,
    synthesis.whyItMatters,
    synthesis.supportingContext,
    ...synthesis.whatNew
  ]);
  const otherSources = selectDistinctSupportingSources(answer, evidence, bestSource);
  return {
    directAnswer: polishText(synthesis.answer),
    explanation: polishText(synthesis.explanation),
    whatNew: synthesis.whatNew,
    important: polishText(synthesis.whyItMatters),
    keyTakeaways: (answer?.key_takeaways?.length ? answer.key_takeaways : inferTakeaways(answer)).map(polishText),
    whatToNotice: buildWhatToNotice(answer, evidence).map(polishText),
    supportingContext: polishText(synthesis.supportingContext),
    confidence: answer?.confidence ?? inferConfidence(answer),
    bestSource,
    supportingSources: otherSources,
    primaryEvidence: evidence[0] ?? null,
    supportingEvidence: evidence.slice(1),
    sourceNavigator: [bestSource, ...otherSources].filter(Boolean) as FormattedSource[]
  };
}

function selectDistinctSupportingSources(
  answer: AnswerResponse | null,
  evidence: FormattedEvidence[],
  bestSource: FormattedSource | null
): FormattedSource[] {
  const candidates = [
    ...evidence.slice(1).filter(isUsefulSecondaryEvidence).map((item) =>
      formatSource({
        title: item.title,
        url: item.reader_url,
        link_label: item.link_label,
        repo: item.repo,
        path: item.path,
        heading_path: item.heading_path
      })
    ),
    ...(answer?.supporting_sources ?? []).map(formatSource),
    ...(answer?.links ?? []).map(formatSource)
  ];
  const seen = new Set<string>(bestSource ? [sourceKey(bestSource)] : []);
  const distinct: FormattedSource[] = [];
  for (const source of candidates) {
    const key = sourceKey(source);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    distinct.push(source);
    if (distinct.length >= 3) {
      break;
    }
  }
  return distinct;
}

function isUsefulSecondaryEvidence(item: FormattedEvidence): boolean {
  if ((item.score ?? 0) < 0.015) {
    return false;
  }
  if (isBoilerplateClaim(item.excerpt, item.title, item.heading_path)) {
    return false;
  }
  return item.sourceType !== "reference" || Boolean(item.display.section);
}

function sourceKey(source: FormattedSource): string {
  if (source.url) {
    return source.url.toLowerCase();
  }
  return [source.url, source.display.title, source.display.section, source.display.filePath, source.display.repo]
    .filter(Boolean)
    .join("|")
    .toLowerCase();
}

export function groupRelatedResults(hits: SearchHit[]): { primary: NormalizedSearchResult | null; related: NormalizedSearchResult[] } {
  const normalized = dedupeResults(hits.map(formatSearchResult));
  return {
    primary: normalized[0] ?? null,
    related: normalized.slice(1)
  };
}

export function formatEvidence(item: AnswerResponse["evidence"][number]): FormattedEvidence {
  const display = normalizeDisplayMetadata({
    title: item.title,
    heading_path: item.heading_path,
    repo: item.repo,
    path: item.path,
    sourceType: item.content_type
  });
  const excerpt = cleanClaim(item.excerpt, item.title, item.heading_path);
  const claim = cleanClaim(item.claim ?? item.excerpt, item.title, item.heading_path);
  const insight = buildSourceInsight({
    title: display.title,
    section: display.section,
    text: `${claim} ${excerpt}`,
    contentType: item.content_type,
    score: item.score
  });
  return {
    ...item,
    title: display.title,
    claim: claim || `Open ${display.title} for the exact passage.`,
    excerpt: shortestFaithfulExcerpt(excerpt || item.excerpt),
    concept: insight.concept,
    takeaway: insight.takeaway,
    whatToLookFor: insight.whatToLookFor,
    sourceType: insight.sourceType,
    topic: classifyTopic(`${display.title} ${display.section ?? ""} ${display.filePath ?? ""} ${claim} ${excerpt}`),
    version: extractVersion(`${display.title} ${display.section ?? ""} ${display.filePath ?? ""} ${claim} ${excerpt}`),
    date: extractDate(`${display.title} ${display.section ?? ""} ${display.filePath ?? ""} ${claim} ${excerpt}`),
    role: item.role ?? "supporting",
    tags: evidenceTags(item),
    display
  };
}

export function formatSearchResult(hit: SearchHit): NormalizedSearchResult {
  const display = normalizeDisplayMetadata({
    title: hit.title ?? hit.heading_path ?? hit.path ?? hit.id,
    heading_path: hit.heading_path,
    repo: hit.repo,
    path: hit.path,
    sourceType: hit.content_type
  });
  const excerpt = cleanClaim(hit.snippet ?? "", display.title, display.section);
  const insight = buildSourceInsight({
    title: display.title,
    section: display.section,
    text: `${hit.title ?? ""} ${hit.heading_path ?? ""} ${excerpt}`,
    contentType: hit.content_type,
    score: hit.score
  });
  return {
    ...hit,
    title: display.title,
    snippet: excerpt || undefined,
    display,
    concept: insight.concept,
    explanation: insight.summary,
    takeaway: insight.takeaway,
    whatToLookFor: insight.whatToLookFor,
    sourceType: insight.sourceType,
    topic: classifyTopic(`${display.title} ${display.section ?? ""} ${display.filePath ?? ""} ${excerpt}`),
    version: extractVersion(`${display.title} ${display.section ?? ""} ${display.filePath ?? ""} ${excerpt}`),
    date: extractDate(`${display.title} ${display.section ?? ""} ${display.filePath ?? ""} ${excerpt}`),
    links: {
      source: hit.source_url
    }
  };
}

export function formatSource(source: Source): FormattedSource {
  return {
    ...source,
    title: cleanTitle(source.title, source.heading_path),
    display: normalizeDisplayMetadata({
      title: source.title,
      heading_path: source.heading_path,
      repo: source.repo,
      path: source.path
    })
  };
}

export function normalizeSourceMetadata(input: {
  title?: string | null;
  heading_path?: string | null;
  repo?: string | null;
  path?: string | null;
  sourceType?: string | null;
}): DisplayMetadata {
  return normalizeDisplayMetadata(input);
}

export function normalizeDisplayMetadata(input: {
  title?: string | null;
  heading_path?: string | null;
  repo?: string | null;
  path?: string | null;
  sourceType?: string | null;
}): DisplayMetadata {
  const path = normalizePath(input.path);
  const headingSegments = dedupeSegments(splitHeading(input.heading_path));
  const rawTitle = input.title || headingSegments.at(-1) || fileName(path) || "Untitled source";
  const title = cleanTitle(rawTitle, input.heading_path);
  const section = cleanSection(headingSegments.at(-1), title);
  const parts = [section ? `Section: ${section}` : null, path, input.repo].filter(Boolean) as string[];
  const cleanPath = formatCanonicalPath({ section, filePath: path, repo: input.repo ?? undefined });
  return {
    title,
    section,
    repo: input.repo ?? undefined,
    filePath: path,
    sourceType: input.sourceType ?? undefined,
    cleanPath: parts.join(" | "),
    displayTitle: title,
    displaySection: section,
    displayFile: path,
    displayRepo: input.repo ?? undefined,
    canonicalPath: cleanPath
  };
}

export function formatCanonicalPath(input: { section?: string; filePath?: string; repo?: string }): string {
  return [
    input.section ? `Section: ${input.section}` : null,
    input.filePath ? `File: ${input.filePath}` : null,
    input.repo ? `Repo: ${input.repo}` : null
  ].filter(Boolean).join(" | ");
}

export function selectPrimarySource(answer: AnswerResponse | null, evidence: FormattedEvidence[] = []): FormattedSource | null {
  if (answer?.best_source) {
    return formatSource(answer.best_source);
  }
  const primary = evidence[0];
  if (primary) {
    return formatSource({
      title: primary.title,
      url: primary.reader_url,
      link_label: primary.link_label,
      repo: primary.repo,
      path: primary.path,
      heading_path: primary.heading_path
    });
  }
  return answer?.links?.[0] ? formatSource(answer.links[0]) : null;
}

export function buildAnswerSummary(answer: AnswerResponse | null, evidence: FormattedEvidence[] = []): string {
  if (!answer) {
    return "Run a search to get a direct, source-backed answer.";
  }
  const topic = topicFromEvidence(answer, evidence);
  if (isChunkLinkTopic(answer, evidence)) {
    return "Index documentation as section-aware chunks with stable metadata and separate reader/source links.";
  }
  if (isReleaseIntelligenceTopic(answer, evidence)) {
    const primary = evidence[0];
    const topicLabel = primary ? topicLabelFor(primary.topic) : "the selected area";
    const version = primary?.version ? ` ${primary.version}` : "";
    const impact = engineeringImpactPhrase(primary);
    return `Elasticsearch${version} changes ${topicLabel}${impact ? ` with impact on ${impact}` : ""}.`;
  }
  if (isFailureStoreTopic(answer, evidence)) {
    return "Use a failure store for indexing failures that need review, and handle ingest-pipeline errors separately.";
  }
  if (isHybridRerankTopic(answer, evidence)) {
    return "Use hybrid retrieval to gather candidates, then rerank the strongest set when final precision matters.";
  }
  if (isRerankPerformanceTopic(answer, evidence)) {
    return "Use reranking when you need better ordering of already-relevant results and can afford the extra latency.";
  }
  if (topic) {
    return `${topic} is the clearest place to start.`;
  }
  return "The current results point to a relevant source, but the evidence is still thin.";
}

export function buildExplanationSummary(answer: AnswerResponse | null, evidence: FormattedEvidence[] = []): string {
  if (!answer || evidence.length === 0) {
    return "The system did not retrieve enough grounded evidence to explain the answer yet. Try syncing sources or narrowing the query to a specific product area.";
  }
  const primary = evidence[0];
  const location = sourceLocationPhrase(primary.display);
  if (isChunkLinkTopic(answer, evidence)) {
    return `The strongest evidence is about documentation links, anchors, and page-level source locations. In practice, each chunk should carry the file path, heading, stable anchor, license, content type, reader URL, and source URL so the UI can open ${location} and highlight the exact passage instead of showing a raw path.`;
  }
  if (isReleaseIntelligenceTopic(answer, evidence)) {
    const primary = evidence[0];
    const releasePhrase = primary?.version ? `Elasticsearch ${primary.version}` : "the selected Elasticsearch version";
    return `Read this as a change briefing for ${releasePhrase}. The useful signal is whether the change affects query latency, ranking quality, recall, memory use, indexing behavior, mapping choices, resilience, or upgrade risk. Serverless-specific material stays secondary unless the query asks for it.`;
  }
  if (isFailureStoreTopic(answer, evidence)) {
    return `Failure store docs separate two problems: errors raised inside ingest pipelines and documents rejected during indexing. The useful workflow is to capture failed indexing operations, inspect why they failed, and recover or replay the affected documents instead of losing them in logs. Start with ${location} to see which failure path applies.`;
  }
  if (isHybridRerankTopic(answer, evidence)) {
    return `Hybrid search is the broad first pass: it gathers candidates from lexical and semantic retrieval. Reranking is the narrower second pass that improves the order of a smaller candidate set. Start with ${location} to see where recall ends and precision tuning begins.`;
  }
  if (isRerankPerformanceTopic(answer, evidence)) {
    return `Reranking improves the order of results that are already plausible matches; it is not a replacement for first-stage retrieval. The tradeoff is latency, because each candidate needs extra comparison work. Open ${location} first to check the recommendation and constraints.`;
  }
  return `Start with ${location}. It has the clearest connection to the question, while the other sources are useful only when they add an example, caveat, or implementation detail.`;
}

export function buildWhatNewSummary(answer: AnswerResponse | null, evidence: FormattedEvidence[] = []): string[] {
  const text = allAnswerText(answer, evidence);
  if (!/(new|change|changed|improve|improvement|performance|release|update|workflow|rerank|8\.|9\.|version)/i.test(text)) {
    return [];
  }
  if (isReleaseIntelligenceTopic(answer, evidence)) {
    return releaseWhatNewItems(evidence);
  }
  const explicit = answer?.what_new_items?.map((item) => cleanClaim(item)).filter(Boolean) ?? [];
  if (explicit.length > 0) {
    return dedupeText(explicit).slice(0, 3);
  }
  if (isHybridRerankTopic(answer, evidence)) {
    return [
      "The workflow separates broad candidate retrieval from final relevance ordering.",
      "Reranking is treated as a precision step over a smaller top-k set, not as the first retrieval stage."
    ];
  }
  if (isChunkLinkTopic(answer, evidence)) {
    return [
      "Stable anchors and canonical source metadata become part of every indexed chunk.",
      "Reader-facing documentation links and source file links are kept separate."
    ];
  }
  if (isReleaseIntelligenceTopic(answer, evidence)) {
    return releaseLookForItems(evidence);
  }
  if (isFailureStoreTopic(answer, evidence)) {
    return [
      "The important distinction is between ingest-pipeline failures and indexing failures.",
      "Failure stores help you review and recover rejected indexing operations."
    ];
  }
  return ["The retrieved sources point to an updated workflow; read the first source before changing implementation."];
}

export function buildWhatToNotice(answer: AnswerResponse | null, evidence: FormattedEvidence[] = []): string[] {
  const primary = evidence[0];
  if (isChunkLinkTopic(answer, evidence)) {
    return [
      "Look for stable anchors and section-level links, not only page URLs.",
      "Check whether reader-facing docs links and source file links are stored separately.",
      "Notice whether metadata fields are consistent enough to support filtering and deduplication."
    ];
  }
  if (isReleaseIntelligenceTopic(answer, evidence)) {
    return releaseLookForItems(evidence);
  }
  if (isFailureStoreTopic(answer, evidence)) {
    return [
      "Separate ingest-pipeline exceptions from documents rejected during indexing.",
      "Focus on the step that captures failed operations in the failure store.",
      "Check how the docs reconstruct or replay the original document after review.",
      "Watch for support limits around data streams, mappings, or index mode."
    ];
  }
  if (isHybridRerankTopic(answer, evidence)) {
    return [
      "Look for the split between first-stage retrieval and final-stage ranking.",
      "Check the candidate limit before reranking; that is where latency and quality trade off.",
      "Notice whether the source describes recall, precision, or final ordering."
    ];
  }
  if (isRerankPerformanceTopic(answer, evidence)) {
    return [
      "Look for the performance claim and the conditions under which it applies.",
      "Check whether the source is describing ranking quality, latency, or both."
    ];
  }
  return [
    primary?.whatToLookFor ?? "Focus on the recommendation, caveat, or implementation detail in the first source.",
    "Keep the other sources only if they add an example, caveat, or implementation detail."
  ];
}

export function buildWhyItMattersSummary(answer: AnswerResponse | null, evidence: FormattedEvidence[] = []): string {
  if (isChunkLinkTopic(answer, evidence)) {
    return "This matters because stable metadata prevents duplicate evidence, supports reliable filters, and lets users jump directly to the exact documentation section.";
  }
  if (isFailureStoreTopic(answer, evidence)) {
    return "This matters because the right failure path determines whether you fix a pipeline, inspect rejected indexing operations, or build a replay workflow.";
  }
  if (isHybridRerankTopic(answer, evidence)) {
    return "This matters because users get broader recall from hybrid search and cleaner final ordering from reranking without scanning repetitive result cards.";
  }
  if (isReleaseIntelligenceTopic(answer, evidence)) {
    const primary = evidence[0];
    const impact = engineeringImpactPhrase(primary) || "query behavior, operations, or upgrade planning";
    return `This matters because the change can affect ${impact}. Treat feature notes and caveats together before changing production search behavior.`;
  }
  if (answer?.important) {
    return cleanClaim(answer.important) || answer.important;
  }
  return "This matters because the answer is tied to a verifiable source location instead of unsupported generated text.";
}

export function dedupeClaims(evidence: FormattedEvidence[], existingClaims: string[] = []): FormattedEvidence[] {
  const seen = new Set(existingClaims.map(normalizeForCompare).filter(Boolean));
  return evidence.map((item) => {
    const claimKey = normalizeForCompare(item.claim);
    const excerptKey = normalizeForCompare(item.excerpt);
    const claim = claimKey && !seen.has(claimKey) && claimKey !== excerptKey ? item.claim : "";
    if (claim) {
      seen.add(claimKey);
    }
    return { ...item, claim };
  });
}

function dedupeResults(results: NormalizedSearchResult[]): NormalizedSearchResult[] {
  const seen = new Set<string>();
  return results.filter((result) => {
    const key = [result.display.title, result.display.section, result.display.filePath, result.repo].join("|").toLowerCase();
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
}

function prioritizeEvidence(evidence: FormattedEvidence[]): FormattedEvidence[] {
  return [...evidence].sort((a, b) => sourceQualityScore(b) - sourceQualityScore(a));
}

function sourceQualityScore(item: FormattedEvidence): number {
  const text = `${item.title} ${item.heading_path ?? ""} ${item.excerpt} ${item.path ?? ""} ${item.source_url}`.toLowerCase();
  let score = item.score ?? 0;
  if (item.repo === "elastic/docs-content") {
    score += 0.12;
  }
  if (item.content_type === "release_note" || /release-notes|breaking-changes|whats-new/.test(text)) {
    score += 0.16;
  }
  if (/serverless/.test(text)) {
    score -= 0.2;
  }
  if (item.sourceType === "conceptual" || item.sourceType === "procedural" || item.sourceType === "troubleshooting") {
    score += 0.08;
  }
  if (item.display.section && !normalizedEquals(item.display.section, item.display.title)) {
    score += 0.04;
  }
  if (/archive|deprecated|legacy/.test(text)) {
    score -= 0.25;
  }
  if (isBoilerplateClaim(item.excerpt, item.title, item.heading_path)) {
    score -= 0.2;
  }
  return score;
}

function evidenceTags(item: AnswerResponse["evidence"][number]): string[] {
  return Array.from(new Set([
    item.repo === "elastic/docs-content" ? "docs" : null,
    item.repo?.includes("labs") ? "lab" : null,
    item.content_type,
    item.license_family
  ].filter(Boolean) as string[]));
}

function buildSupportingContext(evidence: FormattedEvidence[]): string {
  if (evidence.length <= 1) {
    return "No related source adds a clearly different angle yet.";
  }
  const supporting = evidence.slice(1, 4).map((item) => item.display.title).join(", ");
  return `${supporting} add examples, edge cases, or implementation detail.`;
}

function sourceLocationPhrase(display: DisplayMetadata): string {
  if (display.section && display.filePath) {
    return `${display.section} in ${display.filePath}`;
  }
  if (display.filePath) {
    return display.filePath;
  }
  return display.title;
}

function buildSourceInsight(input: {
  title: string;
  section?: string;
  text: string;
  contentType?: string | null;
  score?: number;
}): { concept: string; summary: string; takeaway: string; whatToLookFor: string; sourceType: SourceKind } {
  const text = input.text.toLowerCase();
  const sourceType = classifySourceType(input);
  if (/failure store|failed indexing|indexing failure|ingest pipeline|rejected/.test(text)) {
    return {
      concept: "Failure handling decision point",
      summary: "This source explains how failure stores capture rejected indexing operations so they can be inspected and recovered later.",
      takeaway: "The practical choice is whether to fix the ingest pipeline, review failed documents, or replay corrected data.",
      whatToLookFor: "Focus on the recovery step that reconstructs or replays the original document.",
      sourceType: "troubleshooting"
    };
  }
  if (/rerank|reranking/.test(text) && /performance|improv|latency|precision|quality/.test(text)) {
    return {
      concept: "Reranking quality and cost",
      summary: "Reranking improves the final order after retrieval has already found plausible matches.",
      takeaway: "Focus on whether the source is claiming better precision, acceptable latency, or both.",
      whatToLookFor: "Look for the performance claim, candidate-set size, and any latency caveat.",
      sourceType: "performance"
    };
  }
  if (/hybrid|bm25|semantic|dense|vector/.test(text) && /rerank|rank/.test(text)) {
    return {
      concept: "Two-stage retrieval workflow",
      summary: "This result explains the pattern of retrieving broadly first, then applying a narrower ranking step.",
      takeaway: "Use it to decide where recall ends and precision-oriented reranking begins.",
      whatToLookFor: "Look for the workflow step, top-k candidate count, and final-ordering recommendation.",
      sourceType: "conceptual"
    };
  }
  if (/anchor|source_url|reader_url|source link|links|path|chunk/.test(text)) {
    return {
      concept: "Stable source linking",
      summary: "This source shows how to keep enough metadata to reopen the exact documentation location.",
      takeaway: "Store links, headings, and anchors with each chunk so the UI can take users directly to the right section.",
      whatToLookFor: "Look for anchors, page links, source URLs, and section-level linking guidance.",
      sourceType: "procedural"
    };
  }
  if (/performance|latency|faster|speed|throughput/.test(text)) {
    return {
      concept: "Performance tradeoff",
      summary: "This source explains the condition where performance changes.",
      takeaway: "Compare the gain with the latency or resource cost before changing the workflow.",
      whatToLookFor: "Look for the metric, benchmark condition, and limitation.",
      sourceType: "performance"
    };
  }
  if (/step|configure|create|add|use|install|enable/.test(text)) {
    return {
      concept: "Implementation guidance",
      summary: "This source lays out the setup or workflow step that matters next.",
      takeaway: "Find the decision point, then follow the next concrete action.",
      whatToLookFor: "Look for required fields, configuration values, or ordered steps.",
      sourceType: "procedural"
    };
  }
  return {
    concept: input.contentType === "lab" ? "Applied example" : sourceType === "reference" ? "Documented setting" : "Documentation page",
    summary: sourceTypeSummary(sourceType, input.contentType),
    takeaway: input.score && input.score < 0.015 ? "Keep this only as background." : "Use this for the concrete detail it documents.",
    whatToLookFor: sourceTypeLookFor(sourceType),
    sourceType
  };
}

function classifySourceType(input: { title: string; section?: string; text: string; contentType?: string | null }): SourceKind {
  const text = `${input.title} ${input.section ?? ""} ${input.text}`.toLowerCase();
  if (input.contentType === "lab") {
    return "example";
  }
  if (/troubleshoot|failure|failed|error|exception|recover|fix|diagnos/.test(text)) {
    return "troubleshooting";
  }
  if (/performance|latency|throughput|benchmark|faster|speed|cost/.test(text)) {
    return "performance";
  }
  if (/step|configure|create|add|install|enable|set up|workflow|pipeline/.test(text)) {
    return "procedural";
  }
  if (/overview|concept|introduction|what is|how .* works|architecture|ranking|retrieval/.test(text)) {
    return "conceptual";
  }
  return "reference";
}

function sourceTypeSummary(sourceType: SourceKind, contentType?: string | null): string {
  switch (sourceType) {
    case "troubleshooting":
      return "This source explains what failed, why it matters, and how to move toward recovery.";
    case "performance":
      return "This source explains the gain, the tradeoff, and the condition where it applies.";
    case "procedural":
      return "This source shows the order of steps and the point where you choose the next action.";
    case "conceptual":
      return "This source explains the idea, how the parts relate, and what follows from that.";
    case "example":
      return "This source gives an applied example that can make the docs easier to translate into implementation.";
    default:
      return contentType === "lab" ? "This source gives a concrete example." : "This source documents a specific setting or capability.";
  }
}

function sourceTypeLookFor(sourceType: SourceKind): string {
  switch (sourceType) {
    case "troubleshooting":
      return "Focus on the step that fixes, recovers, or replays the failed data.";
    case "performance":
      return "Look for the metric, the condition behind the gain, and the latency or resource caveat.";
    case "procedural":
      return "Look for the ordered step, required field, and the point where you choose one path over another.";
    case "conceptual":
      return "Look for the distinction between concepts and the implication for how you design the workflow.";
    case "example":
      return "Look for the concrete implementation detail that shows how the idea is applied.";
    default:
      return "Focus on the specific condition, field, or limitation that changes what you should do.";
  }
}

function classifyTopic(text: string): ChangeTopicName {
  const lower = text.toLowerCase();
  if (/vector|semantic|knn|dense|sparse|rerank|inference/.test(lower)) {
    return "vector_search";
  }
  if (/relevance|ranking|scoring|query rules|bm25/.test(lower)) {
    return "relevance";
  }
  if (/ingest|pipeline|bulk|failure store|data freshness/.test(lower)) {
    return "ingestion";
  }
  if (/mapping|field|schema|template|data model/.test(lower)) {
    return "data_modeling";
  }
  if (/latency|performance|memory|faster|throughput|scaling/.test(lower)) {
    return "performance";
  }
  if (/resilien|recover|retry|backoff|circuit breaker|failure/.test(lower)) {
    return "resilience";
  }
  if (/es\|ql|esql|join|lookup/.test(lower)) {
    return "esql";
  }
  if (/search application|search app/.test(lower)) {
    return "search_applications";
  }
  if (/observability|monitor|metric|profile|slow log/.test(lower)) {
    return "observability";
  }
  return "release_notes";
}

function extractVersion(text: string): string | undefined {
  return text.match(/\b(?:elasticsearch\s*)?([89]\.\d{1,2}(?:\.\d+)?)\b/i)?.[1];
}

function extractDate(text: string): string | undefined {
  return text.match(/\b(20\d{2}-\d{2}-\d{2})\b/)?.[1];
}

function topicLabelFor(topic: ChangeTopicName): string {
  return {
    relevance: "relevance and ranking",
    ingestion: "ingestion",
    data_modeling: "data modeling",
    performance: "performance",
    resilience: "resilience",
    esql: "ES|QL",
    vector_search: "vector search",
    search_applications: "search application",
    observability: "search observability",
    release_notes: "release-note"
  }[topic];
}

function isReleaseIntelligenceTopic(answer: AnswerResponse | null, evidence: FormattedEvidence[]): boolean {
  const text = allAnswerText(answer, evidence);
  return /release|what changed|what is new|latest|breaking|8\.|9\.|version|elasticsearch/.test(text)
    || evidence.some((item) => item.content_type === "release_note" || /release-notes|breaking-changes|whats-new/.test(`${item.path ?? ""} ${item.source_url}`));
}

function releaseWhatNewItems(evidence: FormattedEvidence[]): string[] {
  const items = evidence
    .filter(isUsefulSecondaryEvidence)
    .slice(0, 5)
    .map((item) => {
      const topic = topicLabelFor(item.topic);
      const version = item.version ? ` in ${item.version}` : "";
      const impact = engineeringImpactPhrase(item);
      if (item.topic === "vector_search") {
        return `Vector search${version}: review changes to ${impact || "memory use, filtered retrieval, reranking, or inference behavior"}.`;
      }
      if (item.topic === "performance") {
        return `Performance${version}: review ${impact || "latency, memory, and query-execution impact"}, including any tradeoff.`;
      }
      if (item.topic === "ingestion") {
        return `Ingestion${version}: review ${impact || "pipeline behavior, failure handling, mapping impact, or data freshness"}.`;
      }
      if (item.topic === "esql") {
        return `ES|QL${version}: inspect ${impact || "joins, lookup behavior, query syntax, or execution limits"}.`;
      }
      return `${capitalize(topic)}${version}: identify the behavior change${impact ? ` and its impact on ${impact}` : " and its operational impact"}.`;
    });
  return dedupeText(items).slice(0, 5);
}

function releaseLookForItems(evidence: FormattedEvidence[]): string[] {
  const topics = new Set(evidence.map((item) => item.topic));
  const items = [
    topics.has("vector_search") ? "Check whether the vector-search change affects recall, memory, filtered retrieval, or reranking quality." : null,
    topics.has("performance") ? "Look for the measured speedup and the condition where it applies." : null,
    topics.has("ingestion") ? "Inspect any mapping, pipeline, or failure-recovery detail that changes ingestion behavior." : null,
    topics.has("data_modeling") ? "Check whether the mapping or field choice changes query behavior later." : null,
    topics.has("resilience") ? "Look for retry, recovery, circuit-breaker, or graceful-degradation implications." : null,
    topics.has("esql") ? "Check the exact ES|QL syntax or execution behavior before using it in production." : null,
    "Prefer release-note sections that state a concrete behavior change over generic overview pages."
  ].filter(Boolean) as string[];
  return dedupeText(items).slice(0, 5);
}

function engineeringImpactPhrase(item?: FormattedEvidence | null): string {
  if (!item) {
    return "";
  }
  const text = `${item.title} ${item.heading_path ?? ""} ${item.claim} ${item.excerpt}`.toLowerCase();
  const impacts = [
    /latency|faster|speed|throughput/.test(text) ? "query latency" : null,
    /ranking|rerank|scoring|precision|quality/.test(text) ? "ranking quality" : null,
    /recall|hybrid|semantic|knn|vector/.test(text) ? "recall" : null,
    /memory|bbq|quant/.test(text) ? "memory use" : null,
    /indexing|ingest|pipeline|bulk/.test(text) ? "indexing behavior" : null,
    /mapping|field|schema|template/.test(text) ? "mapping consequences" : null,
    /recover|resilien|failure|retry|circuit breaker/.test(text) ? "resilience" : null,
    /breaking|upgrade|deprecat|removed/.test(text) ? "upgrade risk" : null,
  ].filter(Boolean) as string[];
  return dedupeText(impacts).slice(0, 3).join(", ");
}

function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function topicFromEvidence(answer: AnswerResponse, evidence: FormattedEvidence[]): string {
  return evidence[0]?.display.title ?? answer.best_source?.title ?? answer.links?.[0]?.title ?? "";
}

function isHybridRerankTopic(answer: AnswerResponse | null, evidence: FormattedEvidence[]): boolean {
  const text = allAnswerText(answer, evidence);
  return /hybrid/.test(text) && /rerank|reranking|rank/.test(text);
}

function isRerankPerformanceTopic(answer: AnswerResponse | null, evidence: FormattedEvidence[]): boolean {
  const text = allAnswerText(answer, evidence);
  return /rerank|reranking/.test(text) && /performance|latency|precision|quality|improv/.test(text);
}

function isChunkLinkTopic(answer: AnswerResponse | null, evidence: FormattedEvidence[]): boolean {
  const text = allAnswerText(answer, evidence);
  return /chunk|anchor|source link|source_url|reader_url|stable metadata|documentation links/.test(text);
}

function isFailureStoreTopic(answer: AnswerResponse | null, evidence: FormattedEvidence[]): boolean {
  const text = allAnswerText(answer, evidence);
  return /failure store|failed indexing|indexing failure|ingest pipeline error|rejected indexing/.test(text);
}

function allAnswerText(answer: AnswerResponse | null, evidence: FormattedEvidence[]): string {
  return [
    answer?.summary,
    answer?.direct_answer,
    answer?.explanation,
    answer?.important,
    answer?.what_new,
    ...(answer?.what_new_items ?? []),
    ...evidence.flatMap((item) => [item.title, item.heading_path, item.claim, item.excerpt, item.path])
  ].filter(Boolean).join(" ").toLowerCase();
}

function shortestFaithfulExcerpt(text: string, maxChars = 260): string {
  const cleaned = cleanText(text)
    .replace(/:::\{[^}]+\}|:::/g, " ")
    .replace(/<br\s*\/?>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s*[✅❌]\s*/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (cleaned.length <= maxChars) {
    return cleaned;
  }
  const boundary = cleaned.slice(0, maxChars).lastIndexOf(" ");
  return `${cleaned.slice(0, boundary > 120 ? boundary : maxChars).replace(/[,:; ]+$/, "")}...`;
}

function dedupeText(items: string[]): string[] {
  const seen = new Set<string>();
  const output: string[] = [];
  for (const item of items) {
    const key = normalizeForCompare(item);
    if (!key || seen.has(key)) {
      continue;
    }
    seen.add(key);
    output.push(item);
  }
  return output;
}

function polishText(text: string): string {
  return cleanText(text)
    .replace(/best source-backed direction from the current results/gi, "clearest place to start")
    .replace(/Use this to verify the main idea in context\./gi, "Use this for the concrete detail it documents.")
    .replace(/This result is about operational behavior, so the useful part is/gi, "This source explains")
    .replace(/supporting context/gi, "additional detail")
    .replace(/related context rather than primary proof/gi, "background")
    .replace(/The primary result gives the most relevant source location, and the supporting results add adjacent context\./gi, "")
    .replace(/\s+/g, " ")
    .trim();
}

function inferWhatNew(answer: AnswerResponse | null): string[] {
  const summary = answer?.summary.toLowerCase() ?? "";
  if (!/(new|improve|improvement|update|release|feature|workflow|approach)/.test(summary)) {
    return [];
  }
  const text = answer?.evidence?.[0]?.claim ?? answer?.evidence?.[0]?.excerpt;
  return text ? [text] : [];
}

function inferExplanation(answer: AnswerResponse | null): string {
  if (!answer?.evidence?.length) {
    return "No evidence has been retrieved yet. Run a search to generate a source-backed explanation.";
  }
  const primary = answer.evidence[0];
  return `${cleanClaim(primary.claim ?? primary.excerpt, primary.title, primary.heading_path)} This is the clearest place to start because it connects the answer to a specific documentation section.`;
}

function inferImportance(answer: AnswerResponse | null): string {
  if (!answer?.evidence?.length) {
    return "The system will explain why the result matters once it has grounded evidence.";
  }
  return "The answer is grounded in specific documentation sections, so you can verify the claim and jump directly to the source.";
}

function inferTakeaways(answer: AnswerResponse | null): string[] {
  if (!answer?.evidence?.length) {
    return ["Run a search to see source-backed takeaways."];
  }
  return [
    "Open the read-first source before scanning related matches.",
    "Use the other sources to verify adjacent workflows or implementation details."
  ];
}

function inferConfidence(answer: AnswerResponse | null): ConfidenceLevel {
  const evidence = answer?.evidence ?? [];
  const topScore = evidence[0]?.score ?? 0;
  if (evidence.length >= 2 && topScore >= 0.03) {
    return "high";
  }
  if (evidence.length > 0) {
    return "medium";
  }
  return "low";
}

function cleanTitle(title: string, headingPath?: string | null): string {
  const segments = dedupeSegments(splitHeading(headingPath));
  let cleaned = stripTrailingDocumentation(cleanText(title));
  for (const segment of segments) {
    if (normalizedEquals(cleaned, `${segment} ${segment}`)) {
      cleaned = segment;
    }
  }
  const words = cleaned.split(/\s+/);
  const half = Math.floor(words.length / 2);
  if (half > 0 && words.length % 2 === 0 && normalizedEquals(words.slice(0, half).join(" "), words.slice(half).join(" "))) {
    cleaned = words.slice(0, half).join(" ");
  }
  return cleaned || "Untitled source";
}

function cleanSection(section: string | undefined, title: string): string | undefined {
  if (!section) {
    return undefined;
  }
  const cleaned = stripTrailingDocumentation(cleanText(section));
  return normalizedEquals(cleaned, title) ? cleaned : cleaned;
}

function cleanClaim(text: string, title?: string | null, headingPath?: string | null): string {
  let cleaned = cleanText(text);
  const titleText = cleanTitle(title ?? "", headingPath);
  const section = splitHeading(headingPath).at(-1);
  for (const prefix of [titleText, section]) {
    if (prefix && cleaned.toLowerCase().startsWith(`${prefix} ${prefix}`.toLowerCase())) {
      cleaned = cleaned.slice(prefix.length).trim();
    }
    if (prefix && cleaned.toLowerCase().startsWith(`${prefix} > ${prefix} documentation.`.toLowerCase())) {
      cleaned = `${prefix}.`;
    }
    if (prefix && cleaned.toLowerCase().startsWith(`${prefix} > ${prefix}`.toLowerCase())) {
      cleaned = cleaned.slice(prefix.length + 3).trim();
    }
    if (prefix && cleaned.toLowerCase().startsWith(`${prefix} documentation.`.toLowerCase())) {
      cleaned = `${prefix}.`;
    }
  }
  cleaned = stripRepeatedLeadingPhrase(cleaned);
  if (isBoilerplateClaim(cleaned, titleText, section)) {
    return "";
  }
  return cleaned;
}

function isBoilerplateClaim(text: string, title?: string | null, section?: string | null): boolean {
  const cleaned = stripTrailingDocumentation(cleanText(text)).replace(/\.$/, "");
  if (!cleaned) {
    return true;
  }
  return [title, section]
    .filter(Boolean)
    .some((value) => normalizedEquals(cleaned, value ?? "") || normalizedEquals(cleaned, `${value} documentation`));
}

function stripRepeatedLeadingPhrase(text: string): string {
  const words = text.split(/\s+/);
  for (let size = Math.min(6, Math.floor(words.length / 2)); size >= 1; size -= 1) {
    const first = words.slice(0, size).join(" ");
    const second = words.slice(size, size * 2).join(" ");
    if (normalizedEquals(first, second)) {
      return words.slice(size).join(" ");
    }
  }
  return text;
}

function splitHeading(headingPath?: string | null): string[] {
  return (headingPath ?? "")
    .split(">")
    .map(cleanText)
    .filter(Boolean);
}

function dedupeSegments(segments: string[]): string[] {
  const output: string[] = [];
  for (const segment of segments) {
    if (!output.some((item) => normalizedEquals(item, segment))) {
      output.push(segment);
    }
  }
  return output;
}

function normalizePath(path?: string | null): string | undefined {
  return path?.replace(/\\/g, "/").replace(/^\/+/, "") || undefined;
}

function fileName(path?: string): string | undefined {
  return path?.split("/").filter(Boolean).at(-1);
}

function stripTrailingDocumentation(text: string): string {
  return text.replace(/\s+documentation\.?$/i, "").trim();
}

function cleanText(text: string): string {
  return text.replace(/\s*>\s*/g, " > ").replace(/\s+/g, " ").trim();
}

function normalizedEquals(a: string, b: string): boolean {
  return normalizeForCompare(a) === normalizeForCompare(b);
}

function normalizeForCompare(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}
