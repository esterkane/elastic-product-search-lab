# Routing Agent Notes

## Purpose

A routing agent chooses which path should handle a request. It is useful when the same input channel can receive different task types.

## Design Checklist

- Define each route in one sentence.
- Include a fallback route.
- Record the selected route and reason.
- Keep route labels stable so downstream code can rely on them.

## TODO

- Add the route labels and decision examples from Project 02.

