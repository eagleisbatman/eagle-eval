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

- [ ] Add a built-in `goal_achievement` scorer.
- [ ] Score against `resolution_goal`, `expected_next_action`, `scenario`, and
      `required_clarification_slots`.
- [ ] Add a deterministic next-action check where possible.
- [ ] Add a model-judged goal-achievement check for nuanced cases.
- [ ] Keep generic metrics as supporting signals, not the headline result.
- [ ] Add tests for answerable, unclear-intent, missing-context, and high-risk
      scenarios.

## P0 - Goal-First Reports

The report should answer whether the agent fulfilled its purpose, not only
whether abstract metrics passed.

- [ ] Add headline goal achievement rate: `goals_met / total`.
- [ ] Add next-action match rate.
- [ ] Add scenario breakdowns.
- [ ] Highlight failed goal cases with the reason and conversation id.
- [ ] Add concise recommended fixes based on failed scenarios.
- [ ] Make Markdown and JSON reports expose the same goal-first summary.

## P1 - Guided Configuration For Claude Code And Codex

Setup should be guided, not zero-config. Claude Code/Codex should infer what
they can from the repo, then Eagle Eval should validate and make missing
context obvious.

- [ ] Add `eagle-eval init --minimal` for harness-operated setup.
- [ ] Reduce the default `init` questionnaire feel.
- [ ] Improve config validation with actionable missing-field messages.
- [ ] Extend `doctor` with "what to ask the user next" guidance.
- [ ] Improve installed Codex/Claude skill prompts for repo-derived setup.
- [ ] Document a recommended harness workflow: inspect repo, draft config, run
      doctor, ask only for missing product context, run a small local eval.

## P1 - Branded Terminal And Success UX

The terminal should feel polished and recognizably Eagle Eval while staying
serious and useful.

- [ ] Add a tasteful Eagle Eval first-run banner and tagline.
- [ ] Improve command help text to say "evaluation runner/runtime" clearly.
- [ ] Add progress states for `generate`, `gate`, and `run`.
- [ ] Add success summaries after generation, upload, and run.
- [ ] Lead success output with goal achievement once P0 scoring exists.
- [ ] Keep colors and brand moments restrained enough for professional use.

## P2 - Named Eval Targets And Flows

Production agent apps may have orchestrators, sub-agents, and workflows. Eagle
Eval should support that through runner primitives, not built-in architecture
discovery.

- [ ] Add named eval targets/flows to config.
- [ ] Let each target map to a wrapper function.
- [ ] Allow per-target app context or goal overrides.
- [ ] Run and report targets independently.
- [ ] Compare orchestrated flow results against sub-flow results.

## Non-Goals For Now

- Do not build autonomous codebase analysis into Eagle Eval.
- Do not position Eagle Eval as an eval agent.
- Do not over-model arbitrary sub-agent graphs.
- Do not prioritize visual polish before goal-first scoring and reports.
