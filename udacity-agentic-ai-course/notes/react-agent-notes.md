# ReAct Agent Notes

## Working Definition

ReAct-style workflows alternate between reasoning about the next step and taking an action. In implementation, the important parts are tool boundaries, action logging, and verification of results.

## Do

- Keep tool outputs visible enough for debugging.
- Validate tool results before continuing.
- Stop when the next action is unsupported.

## Don't

- Let the model invent tool results.
- Continue after a failed action without recording the failure.

## TODO

- Identify whether Project 01 uses a ReAct-style pattern and document the exact cells or files.

