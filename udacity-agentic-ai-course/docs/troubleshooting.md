# Troubleshooting

## Missing API Key

Symptom: The script fails before making a model call or reports missing credentials.

Likely cause: Environment variables were not set in the local shell.

Resolution:
- Create local environment variables outside the repository.
- Do not commit `.env` files.
- Document only variable names and placeholder values.

## Model Output Has Wrong Format

Symptom: A downstream agent or parser fails on the previous agent's output.

Likely cause: The prompt did not define a strict schema or the model returned extra prose.

Resolution:
- Add a clear output schema.
- Add validation before passing data downstream.
- Capture the failing output as evidence if it is safe to commit.

## Routing Picks The Wrong Agent

Symptom: The workflow sends a task to an agent that cannot complete it.

Likely cause: Route labels overlap or the routing prompt lacks examples.

Resolution:
- Make route definitions mutually exclusive.
- Add a fallback route.
- Save representative inputs and selected routes for review.

## TODO

- Add project-specific errors after running the course notebooks or scripts.

