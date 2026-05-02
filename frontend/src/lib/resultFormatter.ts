import type { AnswerResponse, SearchHit, Source } from "./api";

export type ConfidenceLevel = "high" | "medium" | "low";

export type FormattedEvidence = AnswerResponse["evidence"][number] & {
  claim: string;
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
};

export type FormattedSource = Source & {
  display: DisplayMetadata;
};

export type NormalizedSearchResult = SearchHit & {
  display: DisplayMetadata;
  explanation: string;
  takeaway: string;
  links: {
    source: string;
  };
};

export type SearchResult = NormalizedSearchResult;

export function formatAnswer(answer: AnswerResponse | null): AnswerViewModel {
  const evidence = (answer?.evidence ?? []).map(formatEvidence);
  const links = (answer?.links?.slice(0, 3) ?? []).map(formatSource);
  return {
    directAnswer: answer?.direct_answer ?? answer?.summary ?? "Run a search to see one clear answer with highlighted proof.",
    explanation: answer?.explanation ?? inferExplanation(answer),
    whatNew: answer?.what_new_items?.length ? answer.what_new_items : inferWhatNew(answer),
    important: answer?.important ?? inferImportance(answer),
    keyTakeaways: answer?.key_takeaways?.length ? answer.key_takeaways : inferTakeaways(answer),
    confidence: answer?.confidence ?? inferConfidence(answer),
    bestSource: answer?.best_source ? formatSource(answer.best_source) : links[0] ?? null,
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
  return {
    ...item,
    title: cleanTitle(item.title, item.heading_path),
    claim: cleanClaim(item.claim ?? item.excerpt, item.title, item.heading_path),
    excerpt: cleanClaim(item.excerpt, item.title, item.heading_path),
    role: item.role ?? "supporting",
    tags: evidenceTags(item),
    display: normalizeDisplayMetadata({
      title: item.title,
      heading_path: item.heading_path,
      repo: item.repo,
      path: item.path,
      sourceType: item.content_type
    })
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
  return {
    ...hit,
    title: display.title,
    snippet: excerpt,
    display,
    explanation: explainResult(hit, display),
    takeaway: resultTakeaway(hit, display),
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
  return {
    title,
    section,
    repo: input.repo ?? undefined,
    filePath: path,
    sourceType: input.sourceType ?? undefined,
    cleanPath: parts.join(" | ")
  };
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

function explainResult(hit: SearchHit, display: DisplayMetadata): string {
  const channel = hit.match_reason ?? "Matched by indexed evidence.";
  return `${channel} The clean source location is ${display.cleanPath || display.title}.`;
}

function resultTakeaway(hit: SearchHit, display: DisplayMetadata): string {
  if ((hit.score ?? 0) < 0.015) {
    return "Treat this as related context rather than primary proof.";
  }
  return `Use this result to verify the answer in ${display.section ? `the ${display.section} section` : "the cited source"}.`;
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
  return stripRepeatedLeadingPhrase(cleaned);
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
