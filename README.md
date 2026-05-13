# Eagle Eval

Eagle Eval is a local-first CLI for evaluating agentic AI applications. It creates realistic multilingual test cases, checks test-case quality, runs your real agent, scores the agent's answers, and keeps the results in the workspace you choose.

The product is Eagle Eval. Langfuse is currently the first live result destination; LangSmith, OpenAI Evals, Gemini / Vertex AI evaluation, and Claude workflows are active design targets.

## What You Get

After a complete eval run, you should have:

- generated test cases in `data/synthetic/`
- `quality_report.json` showing which generated cases are good enough to use
- a stored dataset of passing test cases
- scored agent runs broken down by language and metric
- a compare result that tells you whether a prompt/model change regressed
- enough trace/run context to debug why the agent failed

This is the mental model used across the major eval tools: Langfuse describes evals as repeatable checks that catch regressions, LangSmith centers datasets, experiments, and evaluator scores, OpenAI uses traces, graders, datasets, and eval runs, Vertex AI returns task-specific metrics, and Claude's evaluation flow uses test cases plus prompt-version comparison.

## Plain English Roles

| Role | Meaning | Common choices |
| --- | --- | --- |
| Test-case writer | The model service that writes realistic user conversations for your domain and languages. | Gemini by default; OpenAI or Claude for narrower language sets or adversarial case writing. |
| Scorer | The code or stronger model that grades your agent's answers. | Deterministic checks plus Gemini, OpenAI, or Claude. Use a stronger model than the agent when possible. |
| Result destination | The place where datasets, runs, traces, and scores are stored and reviewed. | Langfuse now; LangSmith, OpenAI Evals, Gemini / Vertex AI evaluation, and Claude workflows are being prepared. |

Gemini remains the default for broad multilingual case writing and scoring. OpenAI and Claude are valid choices when their language coverage fits the eval set or when you want a second opinion from a different model family.

## Scoring

Eagle Eval uses two score layers.

Quality gate scores the generated test cases before they become regression data:

- `naturalness`: 1-5, whether the user messages sound realistic
- `topic_coverage`: 1-5, whether the conversation explores the intended topic
- `difficulty_match`: 1-5, whether the generated difficulty matches the request
- `language_quality`: 1-5, whether the language is natural and not translated English
- `overall`: 1-5, used against `test_cases.quality_threshold`

Agent-run scores measure the actual agent output:

- `language_consistency`: 0 or 1
- `response_completeness`: 0 to 1
- `topic_relevance`: 0 to 1, model-scored
- `safety_check`: 0 or 1, model-scored
- `response_quality`: 0 to 1, model-scored
- `pass_rate`: 0 to 1 aggregate

OpenAI's grader guidance also uses 0 to 1 grades, Langfuse supports numeric, categorical, boolean, and text scores, LangSmith evaluator feedback contains a metric key plus score/value and optional comment, Vertex AI supports model-based and computation-based metrics, and Claude recommends code-based, human, and LLM-based grading depending on reliability needs.

## App Context

Eagle Eval is meant to score your app, not a generic chatbot. Put the app's use case and North Star in `app_context`:

```yaml
app_context:
  product: Agriculture advisory assistant
  user: smallholder farmer using a basic phone
  north_star:
    name: monthly_unique_farmer_queries_resolved
    definition: >
      A farmer query is resolved when the assistant either gives a safe,
      actionable answer or correctly asks for the minimum clarification needed
      and then resolves the query after clarification.
  resolution_policy:
    answerable_now:
      expectation: Answer directly with actionable, safe, local advice.
    unclear_intent:
      expectation: Ask a focused clarification question instead of guessing.
    missing_critical_context:
      expectation: Ask for crop, location, symptom, stage, timing, or other minimum missing facts needed to answer safely.
    unsafe_or_high_risk:
      expectation: Avoid unsafe advice and recommend qualified local support.
```

View it any time:

```bash
eagle-eval context view
```

`doctor` also shows the app context and North Star so builders can quickly confirm what the eval is really optimizing.

## Custom Scorers

Developers can add domain-specific metrics from their own project without editing Eagle Eval. Configure a metric:

```yaml
scoring:
  scorer: gemini
  scorer_model: gemini-3.1-pro
  custom_metrics:
    - name: farmer_query_resolution
      path: eval_scorers.farmer_resolution:score
      weight: 0.45
      required: true
```

Then create the scorer in the evaluated project:

```python
# eval_scorers/farmer_resolution.py

def score(input, output, expected_output, metadata, context):
    responses = output.get("responses", [])
    scenario = metadata.get("scenario") or expected_output.get("scenario")

    if scenario == "unclear_intent":
        value = 1.0 if any("?" in str(response) for response in responses) else 0.0
        comment = "Asked for clarification" if value else "Guessed instead of clarifying"
    else:
        value = 1.0 if responses else 0.0
        comment = "Produced an answer" if value else "No answer"

    return {
        "name": "farmer_query_resolution",
        "value": value,
        "comment": f"{comment}; North Star={context['north_star']['name']}",
    }
```

A custom scorer receives `input`, `output`, `expected_output`, `metadata`, and `context`. It can return a number, boolean, `{"value": ..., "comment": ...}`, or an `Evaluation` object.

## Install

```bash
cd eagle-eval
python -m pip install -e ".[dev,langfuse,gemini]"
```

Install every planned SDK check:

```bash
python -m pip install -e ".[all]"
```

Install individual SDKs:

```bash
python -m pip install -e ".[openai]"
python -m pip install -e ".[anthropic]"
python -m pip install -e ".[langsmith]"
python -m pip install -e ".[vertex]"
```

## One Setup For CLI, Codex, And Claude Code

Create `eval_config.yaml`:

```bash
eagle-eval init
```

Install project helper files for both coding agents:

```bash
eagle-eval install-assistants --tool all --yes
```

That writes:

- `AGENTS.md` for Codex project instructions
- `CLAUDE.md` for Claude Code project memory
- `.claude/skills/eagle-eval/SKILL.md` for a Claude Code `/eagle-eval` workflow

Codex documents project guidance through `AGENTS.md`. Claude Code documents project memory through `CLAUDE.md` and supports project skills/custom commands under `.claude/skills/`.

## Configure

Start from the example config if you do not want the prompt flow:

```bash
cp examples/eval_config.example.yaml eval_config.yaml
```

Use `doctor` before live runs:

```bash
eagle-eval doctor --verbose
```

Set only the keys for the services you use:

```bash
export GOOGLE_API_KEY="..."
export LANGFUSE_PUBLIC_KEY="pk-..."
export LANGFUSE_SECRET_KEY="sk-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
export LANGSMITH_API_KEY="..."
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

All commands support `--help`, `--dry-run`, and `--verbose`. Use `--project-dir /path/to/project` when the installed CLI should read or write a specific eval workspace instead of the current directory.

## Config Shape

```yaml
app_context:
  product: Agriculture advisory assistant
  user: smallholder farmer using a basic phone
  north_star:
    name: monthly_unique_farmer_queries_resolved
    definition: Farmer query resolved after safe answer or needed clarification.

test_cases:
  writer: gemini
  writer_model: gemini-2.0-flash

scoring:
  scorer: gemini
  scorer_model: gemini-3.1-pro
  custom_metrics:
    - name: farmer_query_resolution
      path: eval_scorers.farmer_resolution:score

results:
  destination: langfuse
```

Your agent can use one model, the test-case writer can use another, and the scorer should usually be stronger than the agent model.

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

## Design References

- [Codex AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md)
- [Claude Code skills and custom commands](https://code.claude.com/docs/en/slash-commands)
- [Claude Code settings and CLAUDE.md](https://code.claude.com/docs/en/settings)
- [Langfuse evaluation overview](https://langfuse.com/docs/evaluation/overview)
- [Langfuse score types](https://langfuse.com/docs/evaluation/scores/overview)
- [LangSmith evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [OpenAI agent evals](https://developers.openai.com/api/docs/guides/agent-evals)
- [OpenAI graders](https://developers.openai.com/api/docs/guides/graders)
- [Vertex AI Gen AI evaluation service](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/evaluation)
- [Claude evaluation tool](https://platform.claude.com/docs/en/test-and-evaluate/eval-tool)
- [Claude eval design principles](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests)

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall eagle_eval tests
```

## Repository Status

This repo should stay private until the integrations have been exercised with real credentials and sample agents.

Before making it public:

- verify Gemini test-case writing and scoring end to end
- verify OpenAI and Claude writing/scoring paths on representative language subsets
- verify Langfuse upload/run/status behavior with live credentials
- verify LangSmith, OpenAI Evals, Gemini / Vertex AI evaluation, and Claude workflows
- decide the public license

## License

TBD before public release.
