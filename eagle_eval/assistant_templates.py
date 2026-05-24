"""Assistant workflow templates written by install-assistants."""

def agents_md() -> str:
    return """
# Eagle Eval Agent Guide

Use Eagle Eval when the user asks to create, check, run, compare, or explain agent evaluations.

## First Checks

- Run `eagle-eval doctor` before live runs so missing SDKs, keys, and config are visible.
- Run `eagle-eval services --verbose` before paid APIs or hosted result storage so the exact configured services are visible.
- Run `eagle-eval context view` before judging quality so the app use case and North Star are visible.
- Use `eagle-eval generate --dry-run`, `eagle-eval gate --dry-run`, or `eagle-eval run --dry-run` before commands that call paid APIs or a real agent.
- Store service keys in project `.env.eagle-eval` or global `~/.eagle-eval/.env`; Vertex AI Gemini is the Google default, and `GOOGLE_API_KEY` is only for the explicit Gemini Developer API path.
- Never overwrite generated data unless the user asks for it.

## Eval Flow

1. `eagle-eval generate --languages tier1` writes multilingual user test cases.
2. `eagle-eval gate` checks those cases and adds quality status.
3. `eagle-eval upload` stores passing cases in the configured result destination.
4. `eagle-eval run --languages tier1` runs the real agent and scores outputs.
5. `eagle-eval compare --baseline '{...}' --candidate '{...}'` catches regressions.

## Custom Scorers

- `eagle-eval scorer list` shows configured metrics and starter templates.
- `eagle-eval scorer init farmer_query_resolution --sample` creates a project-owned scorer.
- `eagle-eval scorer test farmer_query_resolution --sample examples/scorer_sample.json` runs the scorer locally.
- `eagle-eval services --verbose` shows test-case writer, scoring service, and result storage readiness.

## Product Vocabulary

- Test-case writer: the model service that creates eval conversations.
- Scorer: the model service or deterministic code that grades agent outputs.
- Result destination: where datasets, run output, score summaries, and debug context are stored. Local files are the default.
- App context: the app use case, user, North Star, and resolution policy that make scoring domain-specific.
- Custom metric: a developer-owned `module:function` scorer listed in `scoring.custom_metrics`.
- Agent wrapper: the SDK-neutral `run_conversation(messages, language, prompt_versions=None)` function Eagle Eval imports.
"""


def codex_skill() -> str:
    return """
---
name: eagle-eval
description: Operate Eagle Eval from Codex for local-first agent evaluation, scoring, reports, and regression checks.
---

# Eagle Eval

Use this skill whenever the user asks Codex to set up, run, inspect, compare, or improve agent evaluations.

## Operating Model

Eagle Eval is a CLI execution engine. Codex is the interface.

- Inspect the repository first. Find the agent entrypoint, prompts, tools, README, routes, and deployment config.
- Derive app context from the source when possible.
- Ask the user only for missing product context: target users, North Star metric, failure cases, and supported languages.
- Do not require the user to hand-edit YAML; create or update `eval_config.yaml` yourself.
- If an agent wrapper is needed, expose `run_conversation(messages, language, prompt_versions=None)`.
- Prefer local results first.
- Ask before large multilingual generation or paid API calls.
- Never print secrets back to the user.

## Safe Credential Handling

If the user provides service keys in chat, place them in a local ignored file such as `.env.eagle-eval`.
Use `~/.eagle-eval/.env` only for machine-wide defaults the user wants across projects.
Make sure `.env.eagle-eval` is ignored by git. Store service names and models in `eval_config.yaml`, not secrets.
Prefer Vertex AI Gemini for Google-backed writing/scoring:
`GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION`.
Use `GOOGLE_API_KEY` only when the config explicitly selects the Gemini Developer API path.
Use `eagle-eval services --verbose` and `eagle-eval doctor` to report set/missing state without revealing values.

## Commands

- `eagle-eval init --minimal`
- `eagle-eval doctor`
- `eagle-eval services --verbose`
- `eagle-eval context view`
- `eagle-eval upload --languages en`
- `eagle-eval run --languages en`
- `eagle-eval run --target target-name --languages en`
- `eagle-eval compare-targets --orchestrator full-flow --sub-targets sub-flow --languages en`
- `eagle-eval status`
- `eagle-eval scorer list`
- `eagle-eval scorer init farmer_query_resolution --sample`
- `eagle-eval scorer test farmer_query_resolution --sample examples/scorer_sample.json`
- `eagle-eval compare --baseline '{"router":13}' --candidate '{"router":14}'`

## Recommended User Prompts

```text
Set up Eagle Eval for this repo. Inspect the codebase, find the agent entrypoint, create the eval config, add any needed wrapper, install Codex/Claude instructions, and keep results local first. Ask me only for missing product context.
```

```text
Run a small local Eagle Eval for English only. Use the current agent behavior, inspect the latest report, and explain failures in terms of user outcomes.
```

```text
Configure Eagle Eval with these credentials. Store them safely in the local ignored Eagle Eval env file. Do not print the secrets back to me. Then run eagle-eval doctor and tell me what is ready.
```
"""


def claude_md() -> str:
    return """
# Eagle Eval

This project uses Eagle Eval for local-first agent evaluation.

Run `/eagle-eval` in Claude Code for the project workflow. Use `eagle-eval doctor` first when you need to inspect SDKs, API keys, config roles, or next steps.

Key terms:
- Test-case writer: creates realistic multilingual eval cases.
- Scorer: grades the agent output using code checks or a stronger model.
- Result destination: stores datasets, run output, score summaries, and debug context. Local files are the default.
- App context: defines the product use case and North Star so scoring is not generic.
- Custom metric: a developer-owned scorer declared in `scoring.custom_metrics`.
- Agent wrapper: the SDK-neutral `run_conversation(messages, language, prompt_versions=None)` function Eagle Eval imports.

Google provider default:
- Use Vertex AI Gemini for Google-backed writing/scoring.
- Required env: `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION`.
- Store credentials in project `.env.eagle-eval` or global `~/.eagle-eval/.env`.
- Use `GOOGLE_API_KEY` only when `eval_config.yaml` explicitly selects the Gemini Developer API path.

Prefer dry runs before commands that call paid APIs or external services.
"""


def claude_skill() -> str:
    return """
---
name: eagle-eval
description: Plan, run, and explain Eagle Eval workflows for this project
---

Use this skill whenever the user asks Claude Code to set up, run, inspect, compare, or improve agent evaluations.

Operating model:
- Eagle Eval is a CLI execution engine. Claude Code is the interface.
- Inspect the repository first. Find the agent entrypoint, prompts, tools, README, routes, and deployment config.
- Derive app context from the source when possible.
- Ask the user only for missing product context: target users, North Star metric, failure cases, and supported languages.
- Do not require the user to hand-edit YAML; create or update `eval_config.yaml` yourself.
- If an agent wrapper is needed, expose `run_conversation(messages, language, prompt_versions=None)`.
- Prefer local results first.
- Ask before large multilingual generation or paid API calls.
- Never print secrets back to the user.

Safe credential handling:
- If the user provides service keys in chat, place them in a local ignored file such as `.env.eagle-eval`.
- Use `~/.eagle-eval/.env` only for machine-wide defaults the user wants across projects.
- Make sure `.env.eagle-eval` is ignored by git.
- Store service names and models in `eval_config.yaml`, not secrets.
- Prefer Vertex AI Gemini for Google-backed writing/scoring:
  `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, and `GOOGLE_CLOUD_LOCATION`.
- Use `GOOGLE_API_KEY` only when the config explicitly selects the Gemini Developer API path.
- Use `eagle-eval services --verbose` and `eagle-eval doctor` to report set/missing state without revealing values.

Commands:
- `eagle-eval init --minimal`
- `eagle-eval doctor`
- `eagle-eval services --verbose`
- `eagle-eval context view`
- `eagle-eval scorer list`
- `eagle-eval scorer init farmer_query_resolution --sample`
- `eagle-eval scorer test farmer_query_resolution --sample examples/scorer_sample.json`
- `eagle-eval generate --languages tier1`
- `eagle-eval gate`
- `eagle-eval upload`
- `eagle-eval run --languages tier1`
- `eagle-eval run --target target-name --languages en`
- `eagle-eval compare-targets --orchestrator full-flow --sub-targets sub-flow --languages en`
- `eagle-eval compare --baseline '{"router":13}' --candidate '{"router":14}'`

Recommended user prompts:
```text
Set up Eagle Eval for this repo. Inspect the codebase, find the agent entrypoint, create the eval config, add any needed wrapper, install Codex/Claude instructions, and keep results local first. Ask me only for missing product context.
```

```text
Run a small local Eagle Eval for English only. Use the current agent behavior, inspect the latest report, and explain failures in terms of user outcomes.
```

```text
Configure Eagle Eval with these credentials. Store them safely in the local ignored Eagle Eval env file. Do not print the secrets back to me. Then run eagle-eval doctor and tell me what is ready.
```

Scoring model:
- `goal_achievement`: headline 0 or 1 score for whether the response satisfies the case goal.
- `next_action_match`: headline 0 or 1 score for answer/clarify/confirm/escalate behavior.
- `goal_achievement_judge`: optional model-scored goal check for nuanced cases.
- Generic metrics such as language consistency, completeness, relevance, safety, quality, and pass rate are supporting signals.
"""
