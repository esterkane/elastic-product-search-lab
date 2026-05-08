import { mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { type ConversationTurn, routeTurn } from "./decisionRouter.ts";
import { loadPages, searchPages } from "./search.ts";

interface Conversation {
  id: string;
  description: string;
  turns: ConversationTurn[];
}

interface EvaluationRow {
  conversation_id: string;
  turn_id: string;
  turn_index: number;
  strategy: "isolated" | "contextual";
  query: string;
  effective_query: string;
  context_terms: string[];
  ranked_ids: string[];
  top_result: string | null;
  ndcg_at_5: number;
  mrr_at_5: number;
  precision_at_3: number;
  recall_at_5: number;
}

const rootDir = dirname(fileURLToPath(import.meta.url)).replace(/\\src$/, "").replace(/\/src$/, "");

export async function evaluateConversationPack(baseDir = rootDir): Promise<Record<string, unknown>> {
  const pages = await loadPages(join(baseDir, "content", "pages"));
  const conversations = await loadConversations(join(baseDir, "data", "conversations.json"));
  const rows: EvaluationRow[] = [];

  for (const conversation of conversations) {
    const priorTurns: ConversationTurn[] = [];
    conversation.turns.forEach((turn, index) => {
      const routed = routeTurn(turn, priorTurns);
      const results = searchPages(routed.effectiveQuery, pages, 5);
      const rankedIds = results.map((result) => result.page.id);
      const relevantIds = new Set(Object.entries(turn.judgments).filter(([, grade]) => grade > 0).map(([id]) => id));
      rows.push({
        conversation_id: conversation.id,
        turn_id: turn.turn_id,
        turn_index: index + 1,
        strategy: routed.strategy,
        query: turn.user,
        effective_query: routed.effectiveQuery,
        context_terms: routed.contextTerms,
        ranked_ids: rankedIds,
        top_result: rankedIds[0] ?? null,
        ndcg_at_5: ndcgAtK(rankedIds, turn.judgments, 5),
        mrr_at_5: mrrAtK(rankedIds, relevantIds, 5),
        precision_at_3: precisionAtK(rankedIds, relevantIds, 3),
        recall_at_5: recallAtK(rankedIds, relevantIds, 5),
      });
      priorTurns.push(turn);
    });
  }

  return {
    generated_at: new Date().toISOString(),
    corpus_pages: pages.length,
    conversations: conversations.length,
    turns: rows,
    aggregate: aggregate(rows),
    by_turn_index: groupMetrics(rows, (row) => `turn_${row.turn_index}`),
    by_strategy: groupMetrics(rows, (row) => row.strategy),
  };
}

export async function writeReports(baseDir = rootDir): Promise<Record<string, unknown>> {
  const report = await evaluateConversationPack(baseDir);
  const jsonPath = join(baseDir, "reports", "conversation-eval-report.json");
  const mdPath = join(baseDir, "reports", "conversation-eval-report.md");
  await mkdir(dirname(jsonPath), { recursive: true });
  await writeFile(jsonPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  await writeFile(mdPath, markdownReport(report), "utf8");
  return report;
}

async function loadConversations(path: string): Promise<Conversation[]> {
  const data = JSON.parse(await readFile(path, "utf8"));
  return data.conversations;
}

function aggregate(rows: EvaluationRow[]): Record<string, number> {
  return {
    ndcg_at_5: mean(rows.map((row) => row.ndcg_at_5)),
    mrr_at_5: mean(rows.map((row) => row.mrr_at_5)),
    precision_at_3: mean(rows.map((row) => row.precision_at_3)),
    recall_at_5: mean(rows.map((row) => row.recall_at_5)),
  };
}

function groupMetrics(rows: EvaluationRow[], keyFn: (row: EvaluationRow) => string): Record<string, Record<string, number>> {
  const groups = new Map<string, EvaluationRow[]>();
  for (const row of rows) {
    const key = keyFn(row);
    groups.set(key, [...(groups.get(key) ?? []), row]);
  }
  return Object.fromEntries([...groups].map(([key, groupedRows]) => [key, aggregate(groupedRows)]));
}

function ndcgAtK(rankedIds: string[], relevance: Record<string, number>, k: number): number {
  const dcg = rankedIds.slice(0, k).reduce((sum, id, index) => {
    const gain = relevance[id] ?? 0;
    return sum + (2 ** gain - 1) / Math.log2(index + 2);
  }, 0);
  const ideal = Object.values(relevance)
    .sort((left, right) => right - left)
    .slice(0, k)
    .reduce((sum, gain, index) => sum + (2 ** gain - 1) / Math.log2(index + 2), 0);
  return ideal === 0 ? 0 : dcg / ideal;
}

function mrrAtK(rankedIds: string[], relevantIds: Set<string>, k: number): number {
  const index = rankedIds.slice(0, k).findIndex((id) => relevantIds.has(id));
  return index === -1 ? 0 : 1 / (index + 1);
}

function precisionAtK(rankedIds: string[], relevantIds: Set<string>, k: number): number {
  return rankedIds.slice(0, k).filter((id) => relevantIds.has(id)).length / k;
}

function recallAtK(rankedIds: string[], relevantIds: Set<string>, k: number): number {
  return relevantIds.size === 0 ? 0 : rankedIds.slice(0, k).filter((id) => relevantIds.has(id)).length / relevantIds.size;
}

function mean(values: number[]): number {
  return values.length === 0 ? 0 : values.reduce((sum, value) => sum + value, 0) / values.length;
}

function markdownReport(report: Record<string, unknown>): string {
  const rows = report.turns as EvaluationRow[];
  const aggregateMetrics = report.aggregate as Record<string, number>;
  const lines = [
    "# Conversational Retrieval Evaluation",
    "",
    f("Generated: `{0}`", report.generated_at),
    f("Corpus pages: `{0}`", report.corpus_pages),
    f("Conversations: `{0}`", report.conversations),
    "",
    "## Aggregate",
    "",
    "| Metric | Value |",
    "| --- | ---: |",
    metricRow("nDCG@5", aggregateMetrics.ndcg_at_5),
    metricRow("MRR@5", aggregateMetrics.mrr_at_5),
    metricRow("Precision@3", aggregateMetrics.precision_at_3),
    metricRow("Recall@5", aggregateMetrics.recall_at_5),
    "",
    "## By Turn Index",
    "",
    "| Turn | nDCG@5 | MRR@5 | Precision@3 | Recall@5 |",
    "| --- | ---: | ---: | ---: | ---: |",
    ...groupTableRows(report.by_turn_index as Record<string, Record<string, number>>),
    "",
    "## By Strategy",
    "",
    "| Strategy | nDCG@5 | MRR@5 | Precision@3 | Recall@5 |",
    "| --- | ---: | ---: | ---: | ---: |",
    ...groupTableRows(report.by_strategy as Record<string, Record<string, number>>),
    "",
    "## Turn Metrics",
    "",
    "| Conversation | Turn | Strategy | Top result | nDCG@5 | MRR@5 | Precision@3 | Recall@5 | Effective query |",
    "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | --- |",
  ];

  for (const row of rows) {
    lines.push(
      `| ${row.conversation_id} | ${row.turn_index} | ${row.strategy} | ${row.top_result ?? "none"} | ${row.ndcg_at_5.toFixed(3)} | ${row.mrr_at_5.toFixed(3)} | ${row.precision_at_3.toFixed(3)} | ${row.recall_at_5.toFixed(3)} | ${row.effective_query} |`,
    );
  }

  lines.push("", "## Retrieval Insight", "");
  lines.push(
    "Contextual follow-up turns carry prior terms into retrieval. This prevents short turns such as `How do I tune it?` and `What should I watch for in filters?` from being evaluated as isolated keyword queries.",
  );
  return `${lines.join("\n")}\n`;
}

function metricRow(name: string, value: number): string {
  return `| ${name} | ${value.toFixed(3)} |`;
}

function groupTableRows(groups: Record<string, Record<string, number>>): string[] {
  return Object.entries(groups).map(
    ([name, metrics]) =>
      `| ${name} | ${metrics.ndcg_at_5.toFixed(3)} | ${metrics.mrr_at_5.toFixed(3)} | ${metrics.precision_at_3.toFixed(3)} | ${metrics.recall_at_5.toFixed(3)} |`,
  );
}

function f(template: string, value: unknown): string {
  return template.replace("{0}", String(value));
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  await writeReports();
}
