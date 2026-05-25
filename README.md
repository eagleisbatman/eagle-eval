# Eagle Eval

**Goal-first evaluation for real agentic systems.**

Eagle Eval is a local-first CLI that generates realistic, goal-aware test cases, runs your actual agent, scores outcomes against your product's North Star, and produces inspectable reports — all without requiring a hosted service for the core loop.

It is designed primarily to be driven by coding agents (Claude Code, Codex, Grok Build) rather than used as a heavy manual tool.

Local JSON + Markdown reports are the excellent default. Langfuse is the first supported hosted result destination. Vertex AI Gemini, Amazon Bedrock Claude, optional Gemini Developer API, OpenAI, and direct Claude are active writer/scorer services.

## Getting Started & Tutorials

**Recommended path:** Let your coding agent (Claude Code, Codex, or Grok Build) drive Eagle Eval.

**Start here:**
- [Installation Guide](docs/installation.md) — How to get Eagle Eval on your machine (current reality while not on PyPI)

Then:
- [Getting Started Guide](docs/getting-started.md)
- [Using with Grok Build](docs/using-with-grok-build.md)
- [Using with Claude Code](docs/using-with-claude-code.md)
- [Using with Codex](docs/using-with-codex.md)
- [Multi-Agent & Sequential Workflows](docs/multi-agent-sequential-workflows.md)
- [North Star + Resolution Policy](docs/north-star-resolution-policy.md) — read this early for real value
- [Agent Prompt Templates](docs/agent-prompt-templates.md) — ready-to-use prompts for Grok, Claude Code, and Codex after installation

## What You Actually Get

After running the loop, you get something rare in the eval space:

- Test cases that are aware of your resolution policy and expected agent behavior
- Clear headline metrics: **Goal Achievement** and **Next Action Match** (not just generic scores)
- Scenario breakdowns + recommended fixes based on real failures
- The ability to compare an orchestrator against its sub-flows (`compare-targets`)
- Beautiful, readable local Markdown + JSON reports by default
- A system that gets dramatically more powerful the moment you add one custom scorer tied to your actual North Star

This is evaluation that protects real user outcomes, not just LLM metrics.

**Core belief:** The best eval system is one that makes your coding agents dramatically more effective at shipping reliable agentic software.

The product roadmap is tracked in [ROADMAP.md](ROADMAP.md). The current
priority is moving from generic metric-first output to goal-first scoring and
reports.

This is the mental model used across the major eval tools: Langfuse describes evals as repeatable checks that catch regressions, LangSmith centers datasets, experiments, and evaluator scores, OpenAI uses traces, graders, datasets, and eval runs, Vertex AI returns task-specific metrics, and Claude's evaluation flow uses test cases plus prompt-version comparison.

## Plain English Roles

| Role | Meaning | Common choices |
| --- | --- | --- |
| Test-case writer | The model service that writes realistic user conversations for your domain and languages. | Vertex AI Gemini by default; Amazon Bedrock Claude, OpenAI, or direct Claude for narrower language sets or adversarial case writing. |
| Scorer | The code or stronger model that grades your agent's answers. | Deterministic checks plus Vertex AI Gemini, Amazon Bedrock Claude, optional Gemini Developer API, OpenAI, or direct Claude. Use a stronger model than the agent when possible. |
| Result destination | Where Eagle Eval stores datasets, run output, score summaries, and debug context. | Local files by default; Langfuse for hosted review; LangSmith, OpenAI Evals, Vertex AI Gemini, and Claude workflows are being prepared. |

Vertex AI Gemini is the default for broad multilingual case writing and scoring. Amazon Bedrock Claude, OpenAI, and direct Claude are valid choices when their language coverage fits the eval set or when you want a second opinion from a different model family.

## Scoring

Eagle Eval uses two score layers.

Quality gate scores the generated test cases before they become regression data:

- `naturalness`: 1-5, whether the user messages sound realistic
- `topic_coverage`: 1-5, whether the conversation explores the intended topic
- `difficulty_match`: 1-5, whether the generated difficulty matches the request
- `language_quality`: 1-5, whether the language is natural and not translated English
- `overall`: 1-5, used against `test_cases.quality_threshold`

Agent-run headline scores measure whether the agent did what the test case
needed:

- `goal_achievement`: 0 or 1, whether the response satisfies the case's
  `resolution_goal`
- `next_action_match`: 0 or 1, whether the agent answered, clarified,
  confirmed, or escalated as expected by `expected_next_action`
- `goal_achievement_judge`: 0 to 1, optional model-judged check for nuanced
  cases when model scorers are enabled

Supporting scores help explain failures and regressions:

- `language_consistency`: 0 or 1
- `response_completeness`: 0 to 1
- `topic_relevance`: 0 to 1, model-scored
- `safety_check`: 0 or 1, model-scored
- `response_quality`: 0 to 1, model-scored
- `pass_rate`: 0 to 1 aggregate

Local runs use deterministic built-ins and custom scorers by default. Set `results.local.include_model_scorers: true` when you want local runs to call the configured Vertex AI Gemini, Amazon Bedrock Claude, optional Gemini Developer API, OpenAI, or direct Claude scorer model for model-judged supporting metrics.

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
  scorer: vertex
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

See the full [Installation Guide](docs/installation.md) for practical instructions.

**Quick version (recommended for testing with coding agents):**

```bash
git clone https://github.com/eagleisbatman/eagle-eval.git
cd eagle-eval
python -m pip install -e ".[dev,vertex,bedrock]"
eagle-eval install-assistants --tool all --scope global --yes
```

After this, you can use Eagle Eval on any of your agent projects.

## One Setup For CLI, Codex, And Claude Code

Create `eval_config.yaml`:

```bash
eagle-eval init
```

`init` starts with a small harness-friendly config so Claude Code or Codex can
refine the app context and wrapper path from the repo:

```bash
eagle-eval doctor
```

For the full guided questionnaire, use `eagle-eval init --full`.

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

## Named Eval Targets

For orchestrators, sub-agents, or separate product flows, define named targets
instead of forcing everything through one wrapper:

```yaml
eval_targets:
  - name: research-flow
    agent:
      module: app.research_agent
      function: run_conversation
    app_context:
      north_star:
        name: high_quality_research_briefs
```

Run one target at a time:

```bash
eagle-eval run --target research-flow --languages en
```

Codex or Claude Code can add these targets after inspecting your repo; Eagle
Eval simply runs the named wrapper and applies any target-specific app context.

Compare an orchestrated target against sub-flow targets:

```bash
eagle-eval compare-targets \
  --orchestrator full-flow \
  --sub-targets research-flow,synthesis-flow \
  --languages en
```

The comparison highlights cases where a sub-flow scores stronger than the
orchestrated flow, which helps Codex or Claude Code focus debugging on routing,
handoff, or synthesis behavior.

## Configure

Start from the example config if you want a complete sample instead of the
generated minimal config:

```bash
cp examples/eval_config.example.yaml eval_config.yaml
```

Use `doctor` before live or service-backed runs:

```bash
eagle-eval doctor --verbose
eagle-eval services --verbose
```

`doctor` also prints Codex/Claude setup guidance: what product context to ask
for, whether the wrapper path still looks like a placeholder, and whether the
language set should be confirmed before broad generation.

Local result files do not require service keys. For live services, prefer env
files over shell exports so Eagle Eval does not accidentally use unrelated keys
from your terminal.

Eagle Eval loads these files automatically, in this order:

1. `~/.eagle-eval/.env` for machine-wide defaults
2. `.env` in the evaluated project
3. `.env.eagle-eval` in the evaluated project for Eagle Eval-specific overrides

```bash
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_CLOUD_LOCATION=us-central1
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=your-langfuse-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
AWS_PROFILE=eagle-bedrock
AWS_REGION=us-east-1
AWS_BEDROCK_CLAUDE_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0
LANGSMITH_API_KEY=...
```

Use `GOOGLE_API_KEY` only when you deliberately configure the optional Gemini
Developer API path with `test_cases.writer: gemini` or `scoring.scorer: gemini`.
Use `AWS_PROFILE` when you want Eagle Eval to use a named AWS profile. If you
already use default AWS credentials or an instance role, keep the region and
model id but omit the profile.
Run `eagle-eval doctor --verbose` or `eagle-eval services --verbose` to see
which env files were loaded without printing secret values.

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
eagle-eval run --target research-flow --languages en
eagle-eval compare-targets --orchestrator full-flow --sub-targets research-flow,synthesis-flow --languages en
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

- `data/results/runs/<run-name>.json` with full inputs, outputs, scores, comments, metadata, and the goal-first summary
- `data/results/runs/<run-name>.md` with goal achievement, next-action match, scenario breakdowns, failed cases, recommended fixes, and per-item notes

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
  writer: vertex
  writer_model: gemini-2.0-flash

scoring:
  scorer: vertex
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

Your agent can use one model, the test-case writer can use another, and the scorer should usually be stronger than the agent model. For Bedrock, set `test_cases.writer: bedrock` or `scoring.scorer: bedrock`, then use an Amazon Bedrock Claude model id such as `global.anthropic.claude-sonnet-4-5-20250929-v1:0`.

## Update

For a published package:

```bash
eagle-eval update
```

For a repo-backed private tool that should update when you push to `main`, add this to `eval_config.yaml`:

```yaml
updates:
  source: "git+https://github.com/eagleisbatman/eagle-eval.git@main"
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
- [Google Gen AI SDK on Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/sdks/overview)
- [Amazon Bedrock InvokeModel](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-invoke.html)
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
- verify Amazon Bedrock Claude, OpenAI, and direct Claude writing/scoring paths on representative language subsets
- verify the Twitter/X content agent in live mode with Google ADK, OpenAI Agents SDK, and Claude SDK credentials
- verify Langfuse upload/run/status behavior with live credentials
- verify LangSmith, OpenAI Evals, Vertex AI Gemini, optional Gemini Developer API, and Claude workflows
- validate tier assignment and language-consistency scoring on lower-resource languages where language detection may be unreliable
- decide the public license

## License

TBD before public release.
