# Architecture

## Workflow Summary

TODO: Confirm from code. The expected design is a project-management workflow where specialized agents transform a product request into structured planning artifacts.

## Candidate Components

| Component | Responsibility | Input | Output |
| --- | --- | --- | --- |
| Direct prompt agent | TODO: confirm | TODO | TODO |
| Augmented prompt agent | TODO: confirm | TODO | TODO |
| Knowledge-augmented prompt agent | TODO: confirm | TODO | TODO |
| RAG knowledge prompt agent | TODO: confirm | TODO | TODO |
| Evaluation agent | TODO: confirm | Generated artifact | Evaluation result |
| Routing agent | TODO: confirm | Task/request | Selected route |
| Workflow orchestrator | TODO: confirm | Product spec | Project-management artifacts |

## Data Flow

1. TODO: User or product spec enters the workflow.
2. TODO: Routing or orchestration chooses an agent path.
3. TODO: Agents generate intermediate artifacts.
4. TODO: Evaluation checks quality or format.
5. TODO: Final output is written to `outputs/`.

## External Dependencies

TODO: Confirm model provider, SDKs, and runtime dependencies from `requirements.txt` and source imports.

## Risks

- Agent outputs can drift from the requested schema.
- Evaluator prompts can miss product-management quality issues.
- Generated outputs can look plausible without being implementation-ready.

