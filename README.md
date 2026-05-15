# Eagle Eval

Eagle Eval is a local-first CLI for evaluating agentic AI applications. It creates realistic multilingual test cases, checks test-case quality, runs your real agent, scores the agent's answers, and writes inspectable results you can use immediately.

The product is Eagle Eval. Local JSON and Markdown reports are the default. Langfuse is the first hosted results service; LangSmith, OpenAI Evals, Gemini / Vertex AI evaluation, and Claude workflows are active design targets.

## What You Get

After a complete eval run, you should have:

- generated test cases in `data/synthetic/`
- `quality_report.json` showing which generated cases are good enough to use
- a stored dataset of passing test cases, either locally or in the configured service
- scored agent runs broken down by language and metric
- a compare result that tells you whether a prompt/model change regressed
- enough trace/run context to debug why the agent failed

This is the mental model used across the major eval tools: Langfuse describes evals as repeatable checks that catch regressions, LangSmith centers datasets, experiments, and evaluator scores, OpenAI uses traces, graders, datasets, and eval runs, Vertex AI returns task-specific metrics, and Claude's evaluation flow uses test cases plus prompt-version comparison.

## Plain English Roles

| Role | Meaning | Common choices |
| --- | --- | --- |
| Test-case writer | The model service that writes realistic user conversations for your domain and languages. | Gemini by default; OpenAI or Claude for narrower language sets or adversarial case writing. |
| Scorer | The code or stronger model that grades your agent's answers. | Deterministic checks plus Gemini, OpenAI, or Claude. Use a stronger model than the agent when possible. |
| Result destination | Where Eagle Eval stores datasets, run output, score summaries, and debug context. | Local files by default; Langfuse for hosted review; LangSmith, OpenAI Evals, Gemini / Vertex AI evaluation, and Claude workflows are being prepared. |

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

Local runs use deterministic built-ins and custom scorers by default. Set `results.local.include_model_scorers: true` when you want local runs to call the configured Gemini, OpenAI, or Claude scorer model for model-judged metrics.

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
      path: eval_scorers.farmer_query_resolution:score
      weight: 0.45
      required: true
```

Then create the scorer in the evaluated project:

```python
# eval_scorers/farmer_query_resolution.py

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

The CLI can create and test scorer files:

```bash
eagle-eval scorer list
eagle-eval scorer init farmer_query_resolution --sample
eagle-eval scorer test farmer_query_resolution --sample examples/scorer_sample.json
```

`scorer test` can run immediately after `scorer init`; add the metric to `eval_config.yaml` when you want it included in full eval runs.

Available starter templates:

- `farmer_query_resolution`
- `clarification_quality`
- `safe_actionability`
- `resolved_after_clarification`

## Install

```bash
cd eagle-eval
python -m pip install -e ".[dev,gemini]"
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

Install skills and project helper files for both coding agents:

```bash
eagle-eval install-assistants --tool all --yes
```

That writes:

- `AGENTS.md` for Codex project instructions
- `.codex/skills/eagle-eval/SKILL.md` for a Codex project skill
- `CLAUDE.md` for Claude Code project memory
- `.claude/skills/eagle-eval/SKILL.md` for a Claude Code `/eagle-eval` workflow

For one-project installs, use the default project scope. For reusable installs
available across agentic development projects, use global scope:

```bash
eagle-eval install-assistants --tool codex --scope global --yes
eagle-eval install-assistants --tool claude --scope global --yes
```

Global scope writes to `~/.codex/skills/eagle-eval/SKILL.md` and
`~/.claude/skills/eagle-eval/SKILL.md`. Project scope writes inside the current
repo. Codex documents repo-specific guidance through `AGENTS.md`; Claude Code
documents repo-specific memory through `CLAUDE.md`.

## Agent SDK Contract

Eagle Eval does not require your app to use a specific agent SDK. Your app can
be built with Google ADK, OpenAI Agents SDK, Claude Code SDK, direct model APIs,
or your own framework. Eagle Eval only needs one importable function:

```python
def run_conversation(messages, language, prompt_versions=None) -> dict:
    return {
        "responses": ["assistant response text"],
        "tools_called": [],
        "metadata": {"framework": "your-agent-sdk"},
    }
```

`messages` is the generated user conversation. `language` is the test-case
language code. `prompt_versions` is the version map from `eval_config.yaml`.
The returned `responses` are what Eagle Eval scores.

See `examples/minimal_agent_app/` for wrappers that expose this same contract
for:

- an offline deterministic agent
- Google ADK
- OpenAI Agents SDK
- Claude Code SDK
- Anthropic Messages API

See `examples/twitter_content_agent/` for a richer dogfood sample: a
research-backed Twitter/X content generator that drafts a post from current
Generative AI updates and can be replayed through Google ADK, OpenAI Agents SDK,
and Claude Code SDK wrappers.

## Configure

Start from the example config if you do not want the prompt flow:

```bash
cp examples/eval_config.example.yaml eval_config.yaml
```

Use `doctor` before live or service-backed runs:

```bash
eagle-eval doctor --verbose
eagle-eval services --verbose
```

Local result files do not require service keys. Set only the keys for the services you use:

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

Try the SDK-neutral local example first:

```bash
eagle-eval --project-dir examples/minimal_agent_app services
eagle-eval --project-dir examples/minimal_agent_app upload --languages en
eagle-eval --project-dir examples/minimal_agent_app run --languages en
eagle-eval --project-dir examples/minimal_agent_app status
```

Then run the loop in your own eval workspace:

```bash
eagle-eval generate --languages tier1
eagle-eval gate
eagle-eval upload
eagle-eval run --languages tier1
eagle-eval compare \
  --baseline '{"router":13}' \
  --candidate '{"router":14}'
eagle-eval context view
eagle-eval scorer list
eagle-eval services
eagle-eval status
```

All commands support `--help`, `--dry-run`, and `--verbose`. Use `--project-dir /path/to/project` when the installed CLI should read or write a specific eval workspace instead of the current directory.

## Check Services

Before calling paid APIs or hosted result storage, run:

```bash
eagle-eval services --verbose
```

It shows the exact services configured for three roles:

- test-case writer: creates synthetic conversations
- scoring service: grades generated test cases and agent outputs
- result storage: stores datasets, run output, score summaries, and debug context

For each role, the command reports SDK installation, required env vars, and whether that service is active for the role today or planned for later. Local result storage requires no service keys.

## Local Results

Local mode is the default so a developer can generate, run, inspect, and debug an eval before connecting Langfuse or any other hosted service.

```yaml
results:
  destination: local
  local:
    directory: data/results
    include_model_scorers: false
```

`eagle-eval upload` writes passing generated conversations into `data/results/datasets/*.json`. `eagle-eval run` can read those dataset files, run the configured agent, score every item, and write:

- `data/results/runs/<run-name>.json` with full inputs, outputs, scores, comments, and metadata
- `data/results/runs/<run-name>.md` with a human-readable score summary and per-item notes

`eagle-eval status` shows local dataset counts and the latest local run. This makes the default loop useful without Langfuse credentials:

```bash
eagle-eval generate --languages en
eagle-eval gate
eagle-eval upload --languages en
eagle-eval run --languages en
eagle-eval status
```

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
      path: eval_scorers.farmer_query_resolution:score

results:
  destination: local
  local:
    directory: data/results
    include_model_scorers: false
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
- [Google ADK Python quickstart](https://google.github.io/adk-docs/get-started/python/)
- [OpenAI Agents SDK running agents](https://openai.github.io/openai-agents-python/running_agents/)
- [Claude Code SDK overview](https://docs.anthropic.com/en/docs/claude-code/sdk)
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

The test suite includes an architecture guard that keeps Python files under 200 lines.
Split commands, provider clients, templates, and result helpers into focused modules instead of growing large files.

## Repository Status

This repo should stay private until the integrations have been exercised with real credentials and sample agents.

Before making it public:

- verify Gemini test-case writing and scoring end to end
- verify OpenAI and Claude writing/scoring paths on representative language subsets
- verify the Twitter/X content agent in live mode with Google ADK, OpenAI Agents SDK, and Claude SDK credentials
- verify Langfuse upload/run/status behavior with live credentials
- verify LangSmith, OpenAI Evals, Gemini / Vertex AI evaluation, and Claude workflows
- validate tier assignment and language-consistency scoring on lower-resource languages where language detection may be unreliable
- decide the public license

## License

TBD before public release.
