# Quiz Bank

## Difficult Questions

1. Why can an evaluation agent improve output quality but still fail to guarantee correctness?

   Answer: It evaluates against its prompt and available evidence. If the criteria are incomplete, ambiguous, or unsupported by source data, it can approve an incorrect answer.

2. What is the main engineering risk of chaining prompts without structured intermediate outputs?

   Answer: Each step may produce ambiguous text that the next step interprets differently, causing silent drift across the workflow.

3. When should routing logic be implemented outside the LLM instead of inside a routing prompt?

   Answer: When the decision can be made deterministically from known fields, rules, or confidence thresholds.

4. What evidence is needed before writing "tests passed" in project documentation?

   Answer: A saved command, output, timestamp or artifact showing the test run and result.

5. Why is `.env.example` safer than `.env`, and what still needs review?

   Answer: `.env.example` should contain only placeholder values. It still needs review because placeholders can accidentally be replaced with real credentials.

## TODO

- Add at least five project-specific quiz questions per project.

