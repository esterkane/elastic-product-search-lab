# Evaluation Agent Notes

## Purpose

An evaluation agent checks a generated artifact against criteria. It is useful for feedback loops, format checks, rubric checks, and coarse quality review.

## Recommended Output

```json
{
  "passed": false,
  "issues": [],
  "evidence": [],
  "recommended_fix": ""
}
```

## Common Failure Modes

- The evaluator checks style but misses factual errors.
- The evaluator accepts unsupported claims.
- The evaluator gives vague feedback that cannot be turned into a code or prompt change.

## TODO

- Add examples from Project 02's evaluation agent after reviewing the code.

