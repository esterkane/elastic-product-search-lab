import type { AnswerResponse, SearchHit, Source } from "./api";

export type ConfidenceLevel = "high" | "medium" | "low";

export type FormattedEvidence = AnswerResponse["evidence"][number] & {
  claim: string;
  role: "primary" | "supporting";
  tags: string[];
  provenanceLabel: string;
};

export type AnswerViewModel = {
  directAnswer: string;
  whatNew: string | null;
  important: string;
  confidence: ConfidenceLevel;
  bestSource: Source | null;
  supportingSources: Source[];
  primaryEvidence: FormattedEvidence | null;
  supportingEvidence: FormattedEvidence[];
  sourceNavigator: Source[];
};

export function formatAnswer(answer: AnswerResponse | null): AnswerViewModel {
  const evidence = (answer?.evidence ?? []).map(formatEvidence);
  const links = answer?.links?.slice(0, 3) ?? [];
  return {
    directAnswer: answer?.direct_answer ?? answer?.summary ?? "Run a search to see one clear answer with highlighted proof.",
    whatNew: answer?.what_new ?? inferWhatNew(answer),
    important: answer?.important ?? inferImportance(answer),
    confidence: answer?.confidence ?? inferConfidence(answer),
    bestSource: answer?.best_source ?? links[0] ?? null,
    supportingSources: answer?.supporting_sources ?? links.slice(1),
    primaryEvidence: evidence.find((item) => item.role === "primary") ?? evidence[0] ?? null,
    supportingEvidence: evidence.filter((item, index) => item.role === "supporting" || index > 0),
    sourceNavigator: links
  };
}

export function groupRelatedResults(hits: SearchHit[]): { primary: SearchHit | null; related: SearchHit[] } {
  return {
    primary: hits[0] ?? null,
    related: hits.slice(1)
  };
}

export function formatEvidence(item: AnswerResponse["evidence"][number]): FormattedEvidence {
  return {
    ...item,
    claim: item.claim ?? item.excerpt,
    role: item.role ?? "supporting",
    tags: evidenceTags(item),
    provenanceLabel: [item.heading_path, item.path, item.repo].filter(Boolean).join(" - ")
  };
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

function inferWhatNew(answer: AnswerResponse | null): string | null {
  const summary = answer?.summary.toLowerCase() ?? "";
  if (!/(new|improve|improvement|update|release|feature|workflow|approach)/.test(summary)) {
    return null;
  }
  return answer?.evidence?.[0]?.claim ?? answer?.evidence?.[0]?.excerpt ?? null;
}

function inferImportance(answer: AnswerResponse | null): string {
  if (!answer?.evidence?.length) {
    return "The system will explain why the result matters once it has grounded evidence.";
  }
  return "The answer is grounded in specific documentation sections, so you can verify the claim and jump directly to the source.";
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
