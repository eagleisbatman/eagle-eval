# Using Eagle Eval with Grok Build

Grok Build (this environment) has excellent compatibility with Eagle Eval because it can run shell commands, read/write files, and reason about your codebase.

## Installation

See the [Installation Guide](installation.md) first if you haven't installed Eagle Eval yet.

The recommended one-time setup for Grok Build users is:

```bash
git clone https://github.com/eagleisbatman/eagle-eval.git
cd eagle-eval
python -m pip install -e ".[dev,vertex,bedrock]"
eagle-eval install-assistants --tool all --scope global --yes
```

After that, you can use it on any project.

## Two Ways to Use It in Grok Build

### 1. Direct CLI Mode (Recommended for Speed)

You (or Grok) can just run the commands directly in the terminal:

```bash
eagle-eval doctor --verbose
eagle-eval services --verbose
eagle-eval generate --languages en --dry-run
eagle-eval run --languages en
eagle-eval status
```

This is often the fastest when you want to iterate quickly or debug something specific.

**Best practices in Grok Build:**

- Always run `eagle-eval doctor --verbose` and `services --verbose` before anything that makes API calls.
- Use `--dry-run` liberally.
- After a run, ask Grok to read the latest Markdown report in `data/results/runs/` and explain the failures in terms of the North Star.

### 2. Agent-Driven Mode (Recommended for Setup + Interpretation)

This is the highest-leverage way:

1. First run (once per machine or per project):

```bash
eagle-eval install-assistants --tool all --yes
```

2. Then talk to Grok like this:

> "Using the eagle-eval skill, set up proper evaluation for this project. Inspect the agent code, create or update eval_config.yaml, add the wrapper if needed, and run a small local English baseline. Only ask me for the North Star definition and the 2-3 failure modes that would be most painful for users."

Grok will use the installed skill guidance + its ability to explore your codebase.

## Grok Build Specific Tips

- Grok can read the generated Markdown reports directly and give you excellent analysis.
- For multi-agent systems, Grok is particularly good at helping you decide how to split `eval_targets`.
- You can keep results 100% local (no Langfuse) and still get very high signal.
- When you want to share a run with someone, switch to Langfuse and let Grok help you interpret the traces.

## Realistic Example Session in Grok Build

Here's what excellent day-to-day usage looks like:

```bash
# 1. You just made a change to the orchestrator's routing logic
git diff HEAD~1 -- app/orchestrator.py

# 2. You ask Grok (in this chat):
#    "Run a quick targeted Eagle Eval on English for the full-flow target and compare goal achievement against the previous baseline. Read the latest report."

# 3. Grok does this in the terminal:
eagle-eval doctor --verbose
eagle-eval run --target full-flow --languages en --run-prefix "post-routing-change"

# 4. After it finishes, you ask:
#    "Read the newest Markdown report in data/results/runs/ and give me the goal achievement delta vs last time, plus the top failing scenarios and recommended fixes."

# 5. You look at the compare-targets output if you're tuning handoffs:
eagle-eval compare-targets \
  --orchestrator full-flow \
  --sub-targets intent,specialist \
  --languages en
```

This loop (make change → let Grok run targeted eval → reason over the goal-first report) is extremely powerful and fast.

**Pro tip**: Keep the last 3–4 run names in a small note. When you want to understand long-term trends, ask Grok to summarize goal achievement movement across those specific reports.

This is currently one of the highest-leverage ways to use Eagle Eval in the world.

### Best Starting Prompt After Installation

Paste this directly in Grok Build:

> "I just installed Eagle Eval and ran the global `install-assistants` command. Using the eagle-eval skill and the agent prompt templates in docs/agent-prompt-templates.md, help me set this up on the current project and run a meaningful first evaluation so we can judge whether it's actually useful for our real agents."

Full collection of ready-to-use prompts: [Agent Prompt Templates](agent-prompt-templates.md)
