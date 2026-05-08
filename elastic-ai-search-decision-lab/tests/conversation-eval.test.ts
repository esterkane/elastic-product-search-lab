import assert from "node:assert/strict";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import test from "node:test";

import { routeTurn } from "../src/decisionRouter.ts";
import { evaluateConversationPack } from "../src/evaluate.ts";

const rootDir = dirname(fileURLToPath(import.meta.url)).replace(/\\tests$/, "").replace(/\/tests$/, "");

test("follow-up turns are expanded with conversation context", () => {
  const first = {
    turn_id: "t1",
    user: "How should I combine keyword and semantic search?",
    judgments: {},
  };
  const followUp = {
    turn_id: "t2",
    user: "How do I tune it?",
    judgments: {},
  };

  const routed = routeTurn(followUp, [first]);

  assert.equal(routed.strategy, "contextual");
  assert.match(routed.effectiveQuery, /keyword|semantic|combine|search/);
  assert.match(routed.effectiveQuery, /tune it/);
});

test("conversation evaluation reports every turn with metrics", async () => {
  const report = await evaluateConversationPack(rootDir);
  const turns = report.turns as Array<Record<string, unknown>>;

  assert.equal(turns.length, 6);
  assert.ok(turns.every((turn) => typeof turn.ndcg_at_5 === "number"));
  assert.ok(turns.some((turn) => turn.strategy === "contextual"));
  assert.deepEqual(Object.keys(report.by_turn_index as Record<string, unknown>), ["turn_1", "turn_2", "turn_3"]);
});
