# Eagle Eval

Eagle Eval is a local-first CLI for evaluating agentic AI applications. It generates multilingual eval cases, quality-gates them, runs your real agent, scores outputs with a stronger judge model, and reports results to an eval backend.

Langfuse is the first supported backend adapter. It is not the product identity.

## Why It Exists

Agent evals are easy to talk about and hard to operate well. Eagle Eval is meant to make the full loop repeatable:

- generate realistic multilingual conversations
- preserve known failure cases as regression data
- run the actual agent code, not a mock
- judge outputs with a stronger model than the agent
- compare prompt/model versions before shipping
- keep datasets, traces, and scores in a backend such as Langfuse

## Current Scope

| Area | Current support |
| --- | --- |
| CLI command | `eagle-eval` |
| Python package | `eagle_eval` |
| Generation providers | Gemini primary; OpenAI and Claude supported where useful |
| Judge providers | Gemini primary; OpenAI and Claude supported where useful |
| Eval backend | Langfuse |
| Backlog backends | Braintrust, Phoenix, Promptfoo |

Gemini remains the default for broad multilingual generation and judging because OpenAI and Claude may not cover every supported language with the same consistency. OpenAI and Claude are still valid provider options for narrower language sets, adversarial cases, and judge comparisons.

## Install

```bash
cd eagle-eval
python -m pip install -e ".[dev,langfuse,gemini]"
```

Optional provider extras:

```bash
python -m pip install -e ".[openai]"
python -m pip install -e ".[anthropic]"
```

## Configure

Run the interactive setup:

```bash
eagle-eval init
```

Or start from the example config:

```bash
cp examples/eval_config.example.yaml eval_config.yaml
```

Set env vars for the providers you use:

```bash
export GOOGLE_API_KEY="..."
export LANGFUSE_PUBLIC_KEY="pk-..."
export LANGFUSE_SECRET_KEY="sk-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"
```

Optional:

```bash
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

## Run The Loop

```bash
eagle-eval generate --languages tier1
eagle-eval gate
eagle-eval upload
eagle-eval run --languages tier1
eagle-eval compare \
  --baseline '{"router":13}' \
  --candidate '{"router":14}'
eagle-eval status
```

All commands support `--help`, `--dry-run`, and `--verbose`.

Use `--project-dir /path/to/project` when the installed CLI should read or write a specific eval workspace instead of the current directory.

## Config Shape

```yaml
synthetic:
  provider: gemini
  model: gemini-2.0-flash

evaluation:
  judge_provider: gemini
  judge_model: gemini-3.1-pro

backends:
  primary: langfuse
```

Generation and judging are separate provider decisions. Your agent can use one model, the synthetic-data generator can use another, and the judge should usually be stronger than the agent model.

## Update

For a published package:

```bash
eagle-eval update
```

For a repo-backed private tool that should update when you push to `main`, add this to `eval_config.yaml`:

```yaml
updates:
  source: "git+https://github.com/YOUR_ORG/eagle-eval.git@main"
```

Then run:

```bash
eagle-eval update --dry-run
eagle-eval update
```

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall eagle_eval tests
```

## Repository Status

This repo should stay private until the provider/backends have been exercised with real credentials and sample agents.

Before making it public:

- verify Gemini generation and Gemini judge runs end to end
- verify OpenAI and Claude generation/judge paths on representative language subsets
- verify Langfuse upload/run/status behavior with live credentials
- add any necessary docs for public users
- decide the public license

## Backlog

- Braintrust backend adapter
- Phoenix backend adapter
- Promptfoo export/run adapter

## License

TBD before public release.
