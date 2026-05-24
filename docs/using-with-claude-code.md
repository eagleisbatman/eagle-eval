# Using Eagle Eval with Claude Code

## Initial Setup

First, follow the [Installation Guide](installation.md) to get Eagle Eval installed.

Then run:

```bash
eagle-eval install-assistants --tool claude --yes
```

After this, you should have:

- A project-level `.claude/skills/eagle-eval/SKILL.md`
- `CLAUDE.md` in the repo root
- Optionally the global skill if you used `--scope global`

## The Best Way to Use It

Just type:

```
/eagle-eval
```

Or give Claude a high-signal prompt:

> "Run the eagle-eval workflow for this project. Inspect the codebase, create a minimal config if one doesn't exist, make sure the agent wrapper is correct, run doctor and services, then execute a small local English eval so we have a baseline. Only ask me for the North Star and critical failure modes."

Claude will use the installed skill to drive `init`, `doctor`, `generate`, `gate`, `run`, etc.

## Recommended Ongoing Pattern

1. Make a change to prompts, routing, tools, or models.
2. Tell Claude:

   > "Run a targeted eagle-eval on English using the current agent and compare goal achievement against the previous baseline. Read the latest report and summarize what improved or regressed."

3. Let Claude propose fixes based on the actual failed cases and recommended fixes in the report.

This turns Eagle Eval into a very powerful regression + goal-alignment tool inside your normal Claude Code workflow.