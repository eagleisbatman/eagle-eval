# Eagle Eval

This project provides the Eagle Eval CLI for local-first agent evaluation. Local JSON/Markdown results are the default; Langfuse is the first hosted results service; LangSmith, OpenAI Evals, Vertex AI Gemini, optional Gemini Developer API, and Claude workflows are active design targets.

## Setup

```bash
cd eagle-eval && python -m pip install -e ".[dev,vertex]"
eagle-eval init
eagle-eval doctor
eagle-eval services --verbose
```

## Commands

```bash
eagle-eval generate --languages tier1
eagle-eval gate
eagle-eval upload
eagle-eval run --languages tier1
eagle-eval compare --baseline '{"router":13}' --candidate '{"router":14}'
eagle-eval context view
eagle-eval scorer list
eagle-eval scorer init farmer_query_resolution --sample
eagle-eval scorer test farmer_query_resolution --sample examples/scorer_sample.json
eagle-eval services
eagle-eval status
eagle-eval install-assistants --tool all --yes
eagle-eval install-assistants --tool claude --scope global --yes
eagle-eval update --dry-run
```

Every command has `--help`. All config lives in `eval_config.yaml`. All commands support `--dry-run` and `--verbose`. Use `--project-dir` when running the installed CLI from outside the eval workspace.

## Key Constraints

- Eagle Eval is the product; integration names should not define the product identity.
- Codex and Claude skills can be installed per project or globally with `eagle-eval install-assistants --scope project|global`.
- `eval_config.yaml` is the single source of truth for agent module, prompt names, languages, test-case writer, scorer, and result destination.
- `results.destination: local` should work without hosted-service credentials and should write inspectable files under `results.local.directory`.
- `eagle-eval services` should clearly explain the configured test-case writer, scoring service, and result storage readiness before paid or hosted calls.
- Agent examples must stay SDK-neutral: every sample should expose the same `run_conversation(messages, language, prompt_versions=None)` contract, whether it wraps Google ADK, OpenAI Agents SDK, Claude Code SDK, direct APIs, or custom app code.
- `app_context` defines the product use case and North Star. Do not evaluate as a generic chatbot when this context exists.
- Custom scoring functions are declared in `scoring.custom_metrics` with `module:function` paths owned by the evaluated project.
- Vertex AI Gemini is the default broad multilingual test-case writer and scorer.
- `GOOGLE_API_KEY` is only for the optional Gemini Developer API path.
- Prefer `.env.eagle-eval` in the evaluated project or `~/.eagle-eval/.env` globally for credentials. Do not rely on shell exports.
- OpenAI and Claude are valid writer/scorer services where their language coverage fits the target eval set.
- Braintrust, Phoenix, and Promptfoo are deferred items only for now.
- The `run` command imports and calls the actual agent defined in config. The agent must be importable from wherever this runs.
- Updates run through `python -m pip install --upgrade`; set `updates.source` to a GitHub `git+https://...@branch` URL for push-to-update workflows.

## Claude Code Workflow

Run `/eagle-eval` after `eagle-eval install-assistants --tool claude --yes` to load the project skill. Prefer `eagle-eval doctor` before live commands so missing SDKs and env vars are visible.
