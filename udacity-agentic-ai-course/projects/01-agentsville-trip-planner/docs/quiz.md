# Quiz

1. What fields should be validated before accepting a generated trip itinerary?

   Answer: Dates, destination, budget, travel constraints, required activities, unavailable options, and any user-specific restrictions.

2. Why should itinerary generation and itinerary validation be separate steps?

   Answer: Separation makes failures easier to inspect and prevents the generator from silently accepting its own unsupported assumptions.

3. What is the risk of leaving notebook outputs unreviewed before committing?

   Answer: Outputs can contain credentials, private paths, raw API responses, or unsupported claims.

4. How would structured output improve a trip planner?

   Answer: It allows downstream validation, easier rendering, and clearer checks for missing fields.

5. What evidence would support a claim that the notebook ran successfully?

   Answer: Saved command or notebook execution evidence, visible outputs, and any relevant test or validation logs.

## TODO

- Add questions tied to the exact agents and prompts in this project.

