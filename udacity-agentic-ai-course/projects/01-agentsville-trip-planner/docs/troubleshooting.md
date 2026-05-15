# Troubleshooting

## Notebook Does Not Run

Possible causes:
- Missing dependency.
- Missing local environment variable.
- Kernel mismatch.

Resolution:
- TODO: Add exact dependency setup after inspection.
- Restart the notebook kernel and rerun from the first cell.

## Output Quality Is Weak

Possible causes:
- Prompt lacks hard constraints.
- The model is optimizing for fluent text instead of valid itinerary structure.

Resolution:
- Add explicit itinerary schema.
- Add validation prompts or deterministic checks.

## TODO

- Add observed errors and fixes from actual runs.

