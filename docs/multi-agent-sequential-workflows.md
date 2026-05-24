# Multi-Agent & Sequential Workflows with Eagle Eval

This is one of Eagle Eval's most powerful (and under-documented) capabilities.

Many real production agents are not single functions. They are graphs:

- Intent classifier / router
- Option presenter
- Specialist agents (transferred to via handoff)
- Async background workers (insight extraction, research, enrichment)
- Synthesis / final response agent

Eagle Eval supports this through **named evaluation targets** + `compare-targets`.

## The Problem This Solves

You want to answer questions like:

- "Is my orchestrator actually better than letting the specialist agents run directly?"
- "Where in the sequential flow are we losing goal achievement?"
- "Did adding the async insight collector improve or hurt the final user outcome?"

Generic eval tools make this painful. Eagle Eval makes it a first-class workflow.

## How It Works

You define multiple wrappers, each exposing the same `run_conversation(...)` contract, then register them as targets.

Example config snippet:

```yaml
eval_targets:
  - name: full-orchestrator
    agent:
      module: app.orchestrator
      function: run_conversation

  - name: intent-classifier
    agent:
      module: app.agents.intent
      function: run_conversation
    app_context:
      north_star:
        name: correct_intent_routing
        definition: "Routes to the right specialist or asks for clarification when truly ambiguous."

  - name: options-agent
    agent:
      module: app.agents.options
      function: run_conversation

  - name: specialist-disease
    agent:
      module: app.agents.specialist_disease
      function: run_conversation

  - name: async-insights
    agent:
      module: app.workers.insight_collector
      function: run_conversation
```

## Recommended Pattern for Sequential + Async Flows

### Your Example (Intent → Options → Transfer → Async Insights)

Define these targets:

1. `full-flow` — the complete orchestrator (what users actually experience)
2. `intent` — just the intent / routing step
3. `options` — the options presentation step
4. `specialist` — the specialist that the user is transferred to
5. `insights` — the async/background insight extraction worker

Then run:

```bash
# Run the full user experience
eagle-eval run --target full-flow --languages en

# Run the pieces independently on the same dataset
eagle-eval run --target intent --languages en
eagle-eval run --target options --languages en
eagle-eval run --target specialist --languages en
eagle-eval run --target insights --languages en
```

Finally compare them:

```bash
eagle-eval compare-targets \
  --orchestrator full-flow \
  --sub-targets intent,options,specialist,insights \
  --languages en
```

The output will show you **goal achievement deltas** between the orchestrated flow and each sub-flow. This is extremely diagnostic for routing and handoff quality.

---

## Full Concrete Example: Intent → Options → Transfer → Async Insights

This is a realistic pattern many production agents follow.

### 1. Project Structure (Recommended)

```
app/
  agents/
    __init__.py
    intent_classifier.py      # returns intent + confidence
    options_presenter.py      # shows choices or asks clarification
    specialist_router.py      # hands off to the right expert
  workers/
    insight_extractor.py      # async/background enrichment
  orchestrator.py             # the main flow users actually talk to
eval_scorers/
  intent_accuracy.py
  handoff_quality.py
  insight_usefulness.py
```

### 2. Full eval_config.yaml Example

```yaml
app_name: AgricultureMultiAgent
domain: agriculture
user_persona: smallholder farmer using a basic phone

app_context:
  product: Multi-agent agriculture advisory system
  user: smallholder farmer in East Africa
  north_star:
    name: farmer_queries_fully_resolved_safely
    definition: >
      A query is resolved when the user receives safe, actionable advice
      (or is correctly routed) without receiving dangerous recommendations
      or being left confused.

  resolution_policy:
    answerable_now: { expectation: "Give safe, specific, actionable advice." }
    unclear_intent: { expectation: "Ask one focused clarification question." }
    missing_critical_context: { expectation: "Ask for the minimum facts required for safe advice." }
    unsafe_or_high_risk: { expectation: "Refuse and direct to qualified local help." }

agent:
  module: app.orchestrator
  function: run_conversation

eval_targets:
  - name: full-flow
    agent:
      module: app.orchestrator
      function: run_conversation

  - name: intent
    agent:
      module: app.agents.intent_classifier
      function: run_conversation
    app_context:
      north_star:
        name: correct_intent_detection
        definition: "Correctly classifies the farmer's primary need and confidence."

  - name: options
    agent:
      module: app.agents.options_presenter
      function: run_conversation

  - name: specialist
    agent:
      module: app.agents.specialist_router
      function: run_conversation

  - name: insights
    agent:
      module: app.workers.insight_extractor
      function: run_conversation
    app_context:
      north_star:
        name: high_quality_insights
        definition: "Extracts facts that would meaningfully improve the final answer."

languages:
  count: 3
  tier1: [en, sw, hi]

test_cases:
  writer: vertex
  writer_model: gemini-2.0-flash
  conversations_per_language: 8
  turns_per_conversation: 6

scoring:
  scorer: vertex
  scorer_model: gemini-3.1-pro
  custom_metrics:
    - name: farmer_query_resolved_safely
      path: eval_scorers.farmer_query_resolved_safely:score
      weight: 1.0
      required: true

results:
  destination: local
  local:
    directory: data/results
    include_model_scorers: false
```

### 3. Wrapper Contract (Every Target Must Implement This)

Each of your agents/workers must expose:

```python
def run_conversation(messages, language, prompt_versions=None) -> dict:
    """
    messages: list of {"role": "user", "content": "..."}
    Returns:
        {
            "responses": [str, ...],
            "tools_called": [...],
            "metadata": {...}
        }
    }
    ```

Even your async `insight_extractor` should accept the conversation history so you can score whether the insights it produced were relevant to the original query.

### 4. How to Actually Run This Setup

```bash
# 1. Create the config and wrappers (let your coding agent do this)
eagle-eval doctor

# 2. Generate cases that test the full range of behaviors
eagle-eval generate --languages tier1

# 3. Gate them
eagle-eval gate

# 4. Run the full experience + each piece independently
eagle-eval run --target full-flow --languages en
eagle-eval run --target intent --languages en
eagle-eval run --target options --languages en
eagle-eval run --target specialist --languages en
eagle-eval run --target insights --languages en

# 5. See where the orchestrator wins or loses vs the pieces
eagle-eval compare-targets \
  --orchestrator full-flow \
  --sub-targets intent,options,specialist,insights \
  --languages en
```

The `compare-targets` report will clearly show you things like:
- "The specialist agent alone scores 18% higher on goal achievement than when called through the orchestrator → handoff is losing context."
- "The async insights worker produces high quality output, but the orchestrator rarely waits for or uses it."

This is the level of diagnostic power that generic eval tools simply do not provide.

Use this pattern. It is one of the best things Eagle Eval offers for real production agent systems.

## How to Handle Async / Background Agents

Async workers are tricky because they don't participate in the real-time conversation.

**Recommended approach:**

- Give the async worker its own target with a modified contract (it can still receive the conversation history + any context the orchestrator would have passed).
- Use a custom scorer that measures whether the insights it produced would have improved the final answer (or matched the resolution policy).
- Run it on the same dataset as the main flow so you can correlate results.

## Best Practices

- Always keep one target called something like `full-flow` or `orchestrator` that represents the actual user experience.
- Use `app_context` overrides per target when the North Star is meaningfully different for a sub-flow.
- Use `run_prefix` when replaying the same dataset across many targets so the run names stay clear.
- The `compare-targets` command will highlight cases where a sub-flow beats the orchestrator — these are your biggest debugging opportunities (bad routing, premature handoff, missing context passing, etc.).

## When to Use This vs Just Running One Target

| Situation | Recommended Approach |
|-----------|----------------------|
| Simple single-agent app | One target is enough |
| Router + 2-3 specialists | `compare-targets` is high value |
| Heavy async / background enrichment | Give async pieces their own targets |
| You are actively tuning handoff logic | Run `compare-targets` after every change |

This feature is one of the strongest reasons to use Eagle Eval instead of generic eval frameworks when you have real production agent architectures.

For a concrete walkthrough, see the `examples/twitter_content_agent/` which has multiple flows you can model as targets.
