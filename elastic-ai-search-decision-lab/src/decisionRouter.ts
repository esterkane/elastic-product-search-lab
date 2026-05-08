import { tokenize } from "./search.ts";

export interface ConversationTurn {
  turn_id: string;
  user: string;
  judgments: Record<string, number>;
}

export interface RoutedTurn {
  strategy: "isolated" | "contextual";
  effectiveQuery: string;
  contextTerms: string[];
}

const followUpMarkers = new Set([
  "it",
  "its",
  "that",
  "this",
  "they",
  "them",
  "those",
  "filters",
  "follow",
  "metrics",
  "tune",
  "tuning",
]);

export function routeTurn(turn: ConversationTurn, priorTurns: ConversationTurn[]): RoutedTurn {
  if (priorTurns.length === 0 || !looksLikeFollowUp(turn.user)) {
    return { strategy: "isolated", effectiveQuery: turn.user, contextTerms: [] };
  }

  const contextTerms = salientContextTerms(priorTurns);
  return {
    strategy: "contextual",
    effectiveQuery: `${contextTerms.join(" ")} ${turn.user}`.trim(),
    contextTerms,
  };
}

export function looksLikeFollowUp(query: string): boolean {
  const terms = tokenize(query);
  if (terms.length <= 5) {
    return true;
  }
  return terms.some((term) => followUpMarkers.has(term));
}

function salientContextTerms(priorTurns: ConversationTurn[]): string[] {
  const counts = new Map<string, number>();
  for (const turn of priorTurns) {
    for (const term of tokenize(turn.user)) {
      counts.set(term, (counts.get(term) ?? 0) + 1);
    }
  }
  return [...counts]
    .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
    .map(([term]) => term)
    .filter((term) => term.length > 2)
    .slice(0, 6);
}
