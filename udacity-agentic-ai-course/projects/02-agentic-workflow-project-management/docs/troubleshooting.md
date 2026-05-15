# Troubleshooting

## Missing Credentials

Symptom: Scripts fail before a model response is returned.

Resolution:
- Set required environment variables locally.
- Do not commit `.env` files.
- Keep only placeholder examples if needed.

## Agent Output Fails Evaluation

Symptom: The evaluation agent reports missing fields or weak quality.

Resolution:
- Inspect the generated artifact.
- Tighten the generator prompt.
- Make the evaluator criteria explicit and measurable.

## Routing Failure

Symptom: The routing agent selects the wrong specialized agent.

Resolution:
- Add route examples.
- Make route definitions mutually exclusive.
- Add fallback behavior for ambiguous tasks.

## TODO

- Add observed command failures and fixes after running the workflow.

