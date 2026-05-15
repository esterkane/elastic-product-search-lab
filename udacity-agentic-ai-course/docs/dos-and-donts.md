# Do And Don't

## Do

- Write prompts with role, task, input, constraints, and output format.
- Save representative outputs when they are needed as evidence.
- Keep run instructions reproducible.
- Document assumptions before conclusions.
- Check notebooks and logs for secrets before committing.
- Use structured outputs when another agent or script consumes the result.

## Don't

- Do not commit real `.env` files, API keys, tokens, or local credentials.
- Do not claim tests passed without saved evidence.
- Do not use an agent when a deterministic script is simpler and more reliable.
- Do not let one prompt perform planning, execution, evaluation, and formatting if those steps need separate review.
- Do not overwrite generated outputs without noting which command produced the replacement.

## Review Checklist

- [ ] No secrets or private paths are present.
- [ ] README explains purpose, setup, and known gaps.
- [ ] Architecture doc identifies agents, tools, inputs, and outputs.
- [ ] Troubleshooting doc includes observed symptoms and fixes.
- [ ] Quiz includes difficult questions with answers.

