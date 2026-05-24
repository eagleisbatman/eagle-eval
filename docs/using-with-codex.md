# Using Eagle Eval with Codex

## Initial Setup

First, follow the [Installation Guide](installation.md).

Then run:

```bash
eagle-eval install-assistants --tool codex --yes
```

This creates:

- `AGENTS.md` in the repo
- `.codex/skills/eagle-eval/SKILL.md`

Global install is also supported and recommended if you work across many agent projects.

## How to Drive It

In Codex, use prompts like:

> "Using the eagle-eval skill, set up evaluation for this repository. Create the config, the wrapper, and run a minimal local baseline. Ask only for product context (North Star + painful failure modes)."

Codex is particularly good at:
- Discovering the real agent entrypoint
- Writing high-quality custom scorers once it understands your North Star
- Maintaining the `eval_targets` definitions as your architecture evolves

## Pro Tip

After Codex creates the initial setup, ask it to add a custom scorer that directly measures your real North Star metric. This is where Eagle Eval becomes dramatically more useful than generic tools.