# Eagle Eval

This project provides the Eagle Eval CLI for agent evaluation. Langfuse is the first supported backend adapter.

## Setup

```bash
cd eagle-eval && python -m pip install -e ".[dev,langfuse,gemini]"
eagle-eval init
```

## Commands

```bash
eagle-eval generate --languages tier1
eagle-eval gate
eagle-eval upload
eagle-eval run --languages tier1
eagle-eval compare --baseline '{"router":13}' --candidate '{"router":14}'
eagle-eval status
eagle-eval update --dry-run
```

Every command has `--help`. All config lives in `eval_config.yaml`. All commands support `--dry-run` and `--verbose`. Use `--project-dir` when running the installed CLI from outside the eval workspace.

## Execution Rule

Run commands one at a time. After each command, report what happened and wait for the user before proceeding. Do not chain `generate -> gate -> upload -> run` in one shot unless the user explicitly asks.

## Key Constraints

- Eagle Eval is the product; backend names should not define the product identity.
- Langfuse is a data store/reporting backend, not the whole product and not a runner. All execution happens locally.
- `eval_config.yaml` is the single source of truth for agent module, prompt names, languages, provider choices, and backend settings.
- Gemini is the default broad multilingual generation/judge provider.
- OpenAI and Claude are valid generation/judge providers, but should be used where their language coverage fits the target eval set.
- Braintrust, Phoenix, and Promptfoo are backend backlog items only for now.
- The `run` command imports and calls the actual agent defined in config. The agent must be importable from wherever this runs.
- Updates run through `python -m pip install --upgrade`; set `updates.source` to a GitHub `git+https://...@branch` URL for push-to-update workflows.

## Env Vars

- `GOOGLE_API_KEY` for Gemini generation/judging.
- `OPENAI_API_KEY` if OpenAI generation/judging is configured.
- `ANTHROPIC_API_KEY` if Claude generation/judging is configured.
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` when using the Langfuse backend.
