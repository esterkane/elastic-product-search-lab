import type { AnswerResponse, SearchHit, Source } from "./api";

export type ConfidenceLevel = "high" | "medium" | "low";

export type FormattedEvidence = AnswerResponse["evidence"][number] & {
  claim: string;
  concept: string;
  takeaway: string;
  whatToLookFor: string;
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
  links: {
    source: string;
  };
};

export type SearchResult = NormalizedSearchResult;

export function formatAnswer(answer: AnswerResponse | null): AnswerViewModel {
  const rawEvidence = (answer?.evidence ?? []).map(formatEvidence);
  const bestSource = selectPrimarySource(answer, rawEvidence);
  const links = (answer?.links?.slice(0, 3) ?? []).map(formatSource);
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
  return {
    directAnswer: synthesis.answer,
    explanation: synthesis.explanation,
    whatNew: synthesis.whatNew,
    important: synthesis.whyItMatters,
    keyTakeaways: answer?.key_takeaways?.length ? answer.key_takeaways : inferTakeaways(answer),
    whatToNotice: buildWhatToNotice(answer, evidence),
    supportingContext: synthesis.supportingContext,
    confidence: answer?.confidence ?? inferConfidence(answer),
    bestSource,
    supportingSources: answer?.supporting_sources?.length ? answer.supporting_sources.map(formatSource) : links.slice(1),
    primaryEvidence: evidence.find((item) => item.role === "primary") ?? evidence[0] ?? null,
    supportingEvidence: evidence.filter((item, index) => item.role === "supporting" || index > 0),
    sourceNavigator: links
  };
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
    claim: claim || `Matched ${display.title}; open the cited section to verify the exact passage.`,
    excerpt: shortestFaithfulExcerpt(excerpt || item.excerpt),
    concept: insight.concept,
    takeaway: insight.takeaway,
    whatToLookFor: insight.whatToLookFor,
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
  const primary = evidence.find((item) => item.role === "primary") ?? evidence[0];
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
  if (isHybridRerankTopic(answer, evidence)) {
    return "Use hybrid retrieval to gather candidates, then rerank the strongest set when final precision matters.";
  }
  if (isRerankPerformanceTopic(answer, evidence)) {
    return "Use reranking when you need better ordering of already-relevant results and can afford the extra latency.";
  }
  if (topic) {
    return `${topic} is the best source-backed direction from the current results.`;
  }
  return "The current results point to a relevant source, but the evidence is not strong enough for a high-confidence answer.";
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
  if (isHybridRerankTopic(answer, evidence)) {
    return `The evidence describes a two-stage retrieval pattern: first collect candidates with lexical and semantic search, then apply reranking to the smaller candidate set. That keeps broad recall from hybrid retrieval while using reranking only where it improves the final ordering users see. Verify the details in ${location}.`;
  }
  if (isRerankPerformanceTopic(answer, evidence)) {
    return `The evidence indicates that reranking is a quality step, not a replacement for first-stage retrieval. It is most useful after search has already found plausible matches, because the reranker spends extra work comparing the query with each candidate. Open ${location} first to check the exact recommendation and constraints.`;
  }
  return `The primary result gives the most relevant source location, and the supporting results add adjacent context. Start with ${location}, then use the secondary sources only to confirm related details or edge cases.`;
}

export function buildWhatNewSummary(answer: AnswerResponse | null, evidence: FormattedEvidence[] = []): string[] {
  const explicit = answer?.what_new_items?.map((item) => cleanClaim(item)).filter(Boolean) ?? [];
  if (explicit.length > 0) {
    return dedupeText(explicit).slice(0, 3);
  }
  const text = allAnswerText(answer, evidence);
  if (!/(new|change|changed|improve|improvement|performance|release|update|workflow|rerank)/i.test(text)) {
    return [];
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
      "Reader-facing documentation links and source-code provenance are kept separate."
    ];
  }
  return ["The retrieved sources point to an improvement or updated workflow; verify the primary source before changing implementation."];
}

export function buildWhatToNotice(answer: AnswerResponse | null, evidence: FormattedEvidence[] = []): string[] {
  const primary = evidence[0];
  if (isChunkLinkTopic(answer, evidence)) {
    return [
      "Look for stable anchors and section-level links, not only page URLs.",
      "Check whether reader-facing docs links and source-code provenance are stored separately.",
      "Notice whether metadata fields are consistent enough to support filtering and deduplication."
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
    primary?.whatToLookFor ?? "Look for the recommendation, caveat, or implementation detail in the primary source.",
    "Use supporting sources to confirm adjacent cases rather than rereading the same claim."
  ];
}

export function buildWhyItMattersSummary(answer: AnswerResponse | null, evidence: FormattedEvidence[] = []): string {
  if (isChunkLinkTopic(answer, evidence)) {
    return "This matters because stable metadata prevents duplicate evidence, supports reliable filters, and lets users jump directly to the exact documentation section.";
  }
  if (isHybridRerankTopic(answer, evidence)) {
    return "This matters because users get broader recall from hybrid search and cleaner final ordering from reranking without scanning repetitive result cards.";
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

function evidenceTags(item: AnswerResponse["evidence"][number]): string[] {
  return Array.from(new Set([
    item.repo === "elastic/docs-content" ? "docs" : null,
    item.repo?.includes("labs") ? "lab" : null,
    item.content_type,
    item.license_family,
    item.role === "primary" ? "primary evidence" : "supporting evidence"
  ].filter(Boolean) as string[]));
}

function buildSupportingContext(evidence: FormattedEvidence[]): string {
  if (evidence.length <= 1) {
    return "There is one primary source; use it as the main verification point.";
  }
  const supporting = evidence.slice(1, 3).map((item) => item.display.title).join(" and ");
  return `Supporting evidence from ${supporting} is related context, not a replacement for the primary proof.`;
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
}): { concept: string; summary: string; takeaway: string; whatToLookFor: string } {
  const text = input.text.toLowerCase();
  if (/rerank|reranking/.test(text) && /performance|improv|latency|precision|quality/.test(text)) {
    return {
      concept: "Reranking quality and cost",
      summary: "This result is about using reranking to improve the final ordering after retrieval has already found plausible matches.",
      takeaway: "Focus on whether the source is claiming better precision, acceptable latency, or both.",
      whatToLookFor: "Look for the performance claim, candidate-set size, and any latency caveat."
    };
  }
  if (/hybrid|bm25|semantic|dense|vector/.test(text) && /rerank|rank/.test(text)) {
    return {
      concept: "Two-stage retrieval workflow",
      summary: "This result explains the pattern of retrieving broadly first, then applying a narrower ranking step.",
      takeaway: "Use it to decide where recall ends and precision-oriented reranking begins.",
      whatToLookFor: "Look for the workflow step, top-k candidate count, and final-ordering recommendation."
    };
  }
  if (/anchor|source_url|reader_url|source link|links|path|chunk/.test(text)) {
    return {
      concept: "Stable source linking",
      summary: "This result is about preserving enough source metadata to reopen the exact documentation location.",
      takeaway: "Use it to verify how links, headings, and provenance should be stored with chunks.",
      whatToLookFor: "Look for anchors, page links, source URLs, and section-level linking guidance."
    };
  }
  if (/performance|latency|faster|speed|throughput/.test(text)) {
    return {
      concept: "Performance tradeoff",
      summary: "This result is about operational behavior, so the useful part is the condition under which performance changes.",
      takeaway: "Use it to understand the practical cost or benefit before changing the workflow.",
      whatToLookFor: "Look for the metric, benchmark condition, and limitation."
    };
  }
  if (/step|configure|create|add|use|install|enable/.test(text)) {
    return {
      concept: "Implementation guidance",
      summary: "This result appears procedural; the useful part is the decision point or setup step.",
      takeaway: "Use it to identify the next concrete action to try.",
      whatToLookFor: "Look for required fields, configuration values, or ordered steps."
    };
  }
  return {
    concept: input.contentType === "lab" ? "Supporting example" : "Documentation guidance",
    summary: `This source provides ${input.contentType === "lab" ? "an example" : "documentation context"} related to the query.`,
    takeaway: input.score && input.score < 0.015 ? "Treat this as related context rather than primary proof." : "Use this to verify the primary idea in context.",
    whatToLookFor: "Look for the recommendation, caveat, or implementation detail that connects to your question."
  };
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
  return `The primary evidence says: ${cleanClaim(primary.claim ?? primary.excerpt, primary.title, primary.heading_path)} This is the best place to start because it is the highest-ranked grounded source for the query.`;
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
    "Open the primary source first.",
    "Use supporting evidence to verify adjacent workflows or implementation details."
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
