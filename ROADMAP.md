# Eagle Eval Roadmap

Eagle Eval is an evaluation runner/runtime, not an autonomous eval agent.
Claude Code and Codex are the agent harnesses: they inspect the developer's
repo, infer context, configure wrappers, and operate Eagle Eval through CLI
primitives.

This roadmap keeps that product boundary explicit. Eagle Eval should become
easy, memorable, and goal-first without taking over the harness role.

## P0 - Goal-First Evaluation

The current generation layer is goal-aware, but default scoring and reporting
still lean too generic. This is the most important product gap.

- [x] Add a built-in `goal_achievement` scorer.
- [x] Score against `resolution_goal`, `expected_next_action`, `scenario`, and
      `required_clarification_slots`.
- [x] Add a deterministic next-action check where possible.
- [ ] Add a model-judged goal-achievement check for nuanced cases.
- [x] Keep generic metrics as supporting signals, not the headline result.
- [x] Add tests for answerable, unclear-intent, missing-context, and high-risk
      scenarios.

## P0 - Goal-First Reports

The report should answer whether the agent fulfilled its purpose, not only
whether abstract metrics passed.

- [x] Add headline goal achievement rate: `goals_met / total`.
- [x] Add next-action match rate.
- [x] Add scenario breakdowns.
- [x] Highlight failed goal cases with the reason and conversation id.
- [x] Add concise recommended fixes based on failed scenarios.
- [x] Make Markdown and JSON reports expose the same goal-first summary.

## P1 - Guided Configuration For Claude Code And Codex

Setup should be guided, not zero-config. Claude Code/Codex should infer what
they can from the repo, then Eagle Eval should validate and make missing
context obvious.

- [x] Add `eagle-eval init --minimal` for harness-operated setup.
- [x] Reduce the default `init` questionnaire feel.
- [x] Improve config validation with actionable missing-field messages.
- [x] Extend `doctor` with "what to ask the user next" guidance.
- [x] Improve installed Codex/Claude skill prompts for repo-derived setup.
- [x] Document a recommended harness workflow: inspect repo, draft config, run
      doctor, ask only for missing product context, run a small local eval.

## P1 - Branded Terminal And Success UX

The terminal should feel polished and recognizably Eagle Eval while staying
serious and useful.

- [x] Add a tasteful Eagle Eval first-run banner and tagline.
- [x] Improve command help text to say "evaluation runner/runtime" clearly.
- [x] Add progress states for `generate`, `gate`, and `run`.
- [x] Add success summaries after generation, upload, and run.
- [x] Lead success output with goal achievement once P0 scoring exists.
- [x] Keep colors and brand moments restrained enough for professional use.

## P2 - Named Eval Targets And Flows

Production agent apps may have orchestrators, sub-agents, and workflows. Eagle
Eval should support that through runner primitives, not built-in architecture
discovery.

- [x] Add named eval targets/flows to config.
- [x] Let each target map to a wrapper function.
- [x] Allow per-target app context or goal overrides.
- [x] Run and report targets independently.
- [ ] Compare orchestrated flow results against sub-flow results.

## Non-Goals For Now

- Do not build autonomous codebase analysis into Eagle Eval.
- Do not position Eagle Eval as an eval agent.
- Do not over-model arbitrary sub-agent graphs.
- Do not prioritize visual polish before goal-first scoring and reports.
