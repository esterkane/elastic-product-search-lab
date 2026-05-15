# Agentic AI Patterns

## Direct Prompt Agent

Use for narrow tasks where the model can answer from the prompt alone.

Do:
- Keep the instruction specific.
- Define the expected output format.
- Include constraints that matter for correctness.

Don't:
- Use direct prompting when the task requires external facts, multi-step state, or validation.

## Knowledge-Augmented Agent

Use when the prompt needs a small amount of curated context.

Do:
- Cite or name the source context.
- Keep retrieval or context selection separate from generation.

Don't:
- Mix untrusted context into instructions without boundaries.

## Routing Agent

Use when a request can follow multiple paths.

Do:
- Define route labels.
- Record the selected route.
- Add a fallback for unsupported input.

Don't:
- Hide routing decisions inside vague prose.

## Evaluation Agent

Use when outputs need quality checks before acceptance.

Do:
- Use explicit criteria.
- Return pass/fail plus reasons.
- Keep evaluation separate from generation.

Don't:
- Treat evaluator approval as a substitute for human review when requirements are ambiguous.

## TODO

- Link each pattern to the exact project files that implement it.

