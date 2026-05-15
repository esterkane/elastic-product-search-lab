# Key Concepts

## Agent

An agent is a system component that uses a model plus instructions, tools, memory, routing logic, or evaluation criteria to complete a task. In this repo, document each agent by its responsibility, inputs, outputs, and failure modes.

## Prompt Chaining

Prompt chaining breaks a larger problem into ordered steps. Each step should produce a concrete intermediate artifact that the next step can consume.

## ReAct Pattern

ReAct combines reasoning and action. The useful engineering question is not whether the model "thinks", but whether each action has enough context, tool access, and validation to be reliable.

## Routing

Routing selects the next agent, tool, or workflow path based on task type, confidence, or evaluation results. Routing should be explicit enough that a reviewer can explain why a branch was selected.

## Evaluation

Evaluation agents check whether an output satisfies requirements. They should use clear criteria and return structured results when possible.

## TODO

- Add examples from Project 01 and Project 02 after reviewing the actual code and notebooks.

