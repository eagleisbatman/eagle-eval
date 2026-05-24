# Getting Started with Eagle Eval

Eagle Eval is a **local-first, goal-first evaluation runner** for agentic applications. It is designed to be driven primarily by coding agents (Claude Code, Codex, Grok Build) rather than used directly as a heavy CLI.

## The Recommended Path (Fastest + Best Results)

1. Install Eagle Eval once (see [Installation Guide](installation.md))
2. Install the assistant helpers (`install-assistants`)
3. Let your coding agent do the heavy lifting on your actual projects

This is the experience Eagle Eval is optimized for.

## 1. Install Eagle Eval

Follow the [Installation Guide](installation.md) for the recommended approach when testing with coding agents.

The fastest path for most people right now:

```bash
git clone https://github.com/eagleisbatman/eagle-eval.git
cd eagle-eval
python -m pip install -e ".[dev,vertex]"
eagle-eval install-assistants --tool all --scope global --yes
```

After this one-time setup, you can use Eagle Eval on any of your agent projects.

## 2. One-Time Setup for Your Coding Agents

```bash
eagle-eval install-assistants --tool all --yes
```

This writes:

- `AGENTS.md` (for Codex)
- `CLAUDE.md` (for Claude Code)
- `.claude/skills/eagle-eval/SKILL.md` → gives you the `/eagle-eval` command in Claude Code
- `.codex/skills/eagle-eval/SKILL.md` (for Codex)

You can also install globally so every project can use it:

```bash
eagle-eval install-assistants --tool claude --scope global --yes
eagle-eval install-assistants --tool codex --scope global --yes
```

## 3. Let the Coding Agent Set It Up

The best experience is:

**In Claude Code**, just type:

```
/eagle-eval
```

Or give it a clear instruction:

> "Using the eagle-eval skill, inspect this repository, create a minimal eval config, add any needed agent wrapper, and run a small English-only local baseline eval. Ask me only for the North Star and the most important failure modes."

**In Codex or Grok Build**, say:

> "Set up Eagle Eval for this project using the eagle-eval skill. Create a minimal config, find or create the `run_conversation` wrapper, then run a tiny local eval so we have a baseline."

The agent will:
- Read your code
- Create `eval_config.yaml`
- Create the thin adapter if needed
- Run `doctor` and `services`
- Generate a small local eval

## 4. The Core Loop (What Actually Happens)

```
generate → gate → upload → run → (compare or status)
```

- `generate`: Creates realistic test conversations (goal-aware)
- `gate`: Quality review so bad cases don't become regression data
- `upload`: Stores passing cases locally (or in Langfuse)
- `run`: Runs **your real agent**, scores with goal achievement + next action match
- `compare` / `compare-targets`: Detects regressions or weak sub-flows

All results are readable JSON + Markdown by default.

## Next Steps

- Read the tutorial for your preferred coding environment:
  - [Using with Claude Code](using-with-claude-code.md)
  - [Using with Codex](using-with-codex.md)
  - [Using with Grok Build](using-with-grok-build.md)
- For complex multi-agent systems (orchestrators, sequential flows, async workers), read:
  - [Multi-Agent & Sequential Workflows](multi-agent-sequential-workflows.md)
- For deep customization, see the main [README](../README.md#custom-scorers)
- If you're struggling with what to put in `app_context`, read the [North Star + Resolution Policy guide](north-star-resolution-policy.md) — it is the highest-leverage concept in the entire system.

## When to Use Eagle Eval

Use it when you want to:
- Know whether a prompt, model, or routing change actually improved real user outcomes
- Compare an orchestrator against its sub-agents
- Maintain a regression suite that is tied to your actual product North Star

Do **not** use it if you want a fully autonomous eval agent that writes tests for you — that is explicitly out of scope (Claude Code / Codex / Grok do that part).
