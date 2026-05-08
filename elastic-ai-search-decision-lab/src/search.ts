import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

export interface Page {
  id: string;
  title: string;
  topic: string;
  text: string;
}

export interface SearchResult {
  page: Page;
  score: number;
}

const stopWords = new Set([
  "a",
  "after",
  "and",
  "are",
  "do",
  "for",
  "how",
  "i",
  "in",
  "is",
  "it",
  "of",
  "or",
  "should",
  "the",
  "to",
  "what",
  "when",
  "which",
]);

const synonymMap = new Map<string, string[]>([
  ["combine", ["hybrid", "fusion"]],
  ["keyword", ["bm25", "lexical"]],
  ["metrics", ["evaluation", "ndcg", "mrr", "relevance"]],
  ["semantic", ["vector"]],
  ["tune", ["tuning", "rrf", "rank", "constant"]],
  ["filters", ["metadata", "constraints"]],
  ["ranking", ["ranked", "retrieval"]],
  ["improved", ["quality", "evaluation"]],
  ["watch", ["honor", "constraints"]],
  ["questions", ["turns", "conversation"]],
]);

export async function loadPages(contentDir: string): Promise<Page[]> {
  const files = (await readdir(contentDir)).filter((file) => file.endsWith(".md")).sort();
  const pages = [];
  for (const file of files) {
    pages.push(parsePage(await readFile(join(contentDir, file), "utf8")));
  }
  return pages;
}

export function searchPages(query: string, pages: Page[], limit = 5): SearchResult[] {
  const queryTerms = expandedTerms(query);
  return pages
    .map((page) => ({ page, score: scorePage(queryTerms, page) }))
    .filter((result) => result.score > 0)
    .sort((left, right) => right.score - left.score || left.page.id.localeCompare(right.page.id))
    .slice(0, limit);
}

export function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .match(/[a-z0-9]+/g)
    ?.filter((token) => !stopWords.has(token)) ?? [];
}

function expandedTerms(query: string): string[] {
  const terms = tokenize(query);
  const expanded = [...terms];
  for (const term of terms) {
    expanded.push(...(synonymMap.get(term) ?? []));
  }
  return expanded;
}

function scorePage(queryTerms: string[], page: Page): number {
  const titleTerms = new Set(tokenize(page.title));
  const topicTerms = new Set(tokenize(page.topic));
  const bodyTerms = tokenize(page.text);
  const bodyCounts = new Map<string, number>();
  for (const term of bodyTerms) {
    bodyCounts.set(term, (bodyCounts.get(term) ?? 0) + 1);
  }

  let score = 0;
  for (const term of queryTerms) {
    if (titleTerms.has(term)) {
      score += 4;
    }
    if (topicTerms.has(term)) {
      score += 2;
    }
    score += bodyCounts.get(term) ?? 0;
  }
  return score;
}

function parsePage(raw: string): Page {
  const match = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!match) {
    throw new Error("Page is missing front matter");
  }
  const metadata = Object.fromEntries(
    match[1].split("\n").map((line) => {
      const [key, ...rest] = line.split(":");
      return [key.trim(), rest.join(":").trim()];
    }),
  );
  return {
    id: metadata.id,
    title: metadata.title,
    topic: metadata.topic,
    text: match[2].trim(),
  };
}
