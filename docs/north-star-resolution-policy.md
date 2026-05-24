# North Star + Resolution Policy — The Most Important Part of Your Config

This is the single highest-leverage concept in Eagle Eval. Getting this right turns Eagle Eval from "just another eval tool" into something that actually protects your product's real user outcomes.

## Why This Matters So Much

Most eval systems score things like "helpfulness", "toxicity", "relevance", or generic LLM-as-a-judge rubrics.

Eagle Eval is different. It asks:

> "Did the agent do what it was *supposed* to do for this specific product?"

That question only becomes answerable when you clearly define:

1. **North Star** — The one metric that actually matters for the business / user success.
2. **Resolution Policy** — What "good" looks like in different situations (answerable, unclear, missing context, high-risk).

Without these, your scores become generic and lose their power.

## The North Star

```yaml
north_star:
  name: monthly_unique_farmer_queries_resolved
  definition: >
    A farmer query is resolved when the assistant either gives a safe,
    actionable answer or correctly asks for the minimum clarification needed
    and then resolves the query after clarification.
```

**Characteristics of a good North Star:**
- It is a real business or user outcome (not an LLM metric).
- It is measurable from the conversation.
- It is specific enough that you can write a scorer for it later.
- It is something you would be willing to defend in a product review.

Bad examples:
- "User satisfaction" (too vague)
- "Accuracy" (too generic)
- "Be helpful" (not actionable for scoring)

## Resolution Policy

This is where you encode your product's actual decision logic.

```yaml
resolution_policy:
  answerable_now:
    expectation: "Answer directly with safe, actionable advice using the information available."

  unclear_intent:
    expectation: "Ask one focused clarification question. Do not guess the user's crop, location, or problem."

  missing_critical_context:
    expectation: "Ask for the minimum set of facts required to give safe advice (crop, location, symptoms, timing, etc.). Never recommend a treatment without them."

  unsafe_or_high_risk:
    expectation: "Refuse to give advice. Clearly recommend the user contact a qualified local expert or emergency service."
```

This policy is used in two places:
- During test case generation (so the generated cases actually test the right behaviors)
- During scoring (`goal_achievement` and custom scorers)

## How to Write a Good One

1. Start with your real product requirements / PRDs / user research.
2. List the 3–5 most common situations the agent encounters.
3. For each situation, write what a *good* response looks like in one sentence.
4. Be specific about what the agent should **not** do (this is often more important).

## Pro Move: Tie Custom Scorers to the North Star

Once you have a solid North Star + policy, create a custom scorer that directly measures it:

```bash
eagle-eval scorer init farmer_query_resolved --sample
```

Then register it:

```yaml
scoring:
  custom_metrics:
    - name: farmer_query_resolved
      path: eval_scorers.farmer_query_resolved:score
      weight: 1.0
      required: true
```

This is how you make Eagle Eval measure *your* product, not a generic chatbot.

## Checklist Before You Run Your First Serious Eval

- [ ] Can I explain the North Star to a non-technical stakeholder in one sentence?
- [ ] Does the resolution policy cover the situations that actually cause user harm or business pain?
- [ ] Would a custom scorer written against this policy be obviously valuable?
- [ ] Have I removed all the placeholder text from `app_context`?

If the answer to any of these is "no", spend time here before generating large test sets.

This is the part that separates teams that get real signal from their evals versus teams that just get pretty numbers.