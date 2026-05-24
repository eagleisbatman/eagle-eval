# Agent Prompt Templates for Eagle Eval

These are battle-tested, copy-paste-ready prompts you can give to Grok Build, Claude Code, or Codex right after installing Eagle Eval.

They are designed to get you from "just installed" to "I have real data to judge whether this tool is actually useful" as quickly as possible.

---

## 1. First-Time Setup Prompt (Use This First)

```text
I just installed Eagle Eval and ran the global install-assistants command.

Using the eagle-eval skill, help me set it up properly on this project so we can evaluate one of our real agents.

Please:
1. Inspect the repository and understand the main agent flow(s).
2. Create a minimal but good eval_config.yaml using `eagle-eval init --minimal` if needed.
3. Make sure there is a proper `run_conversation(messages, language, prompt_versions=None)` wrapper (create one in the project if it doesn't exist).
4. If credentials are needed, store them in `.env.eagle-eval` for this project or `~/.eagle-eval/.env` for global defaults. Do not print secrets back to me.
5. Run `eagle-eval doctor --verbose` and `services --verbose` and report what is ready vs missing.
6. Ask me only for the most important product context: the North Star and the 2-3 failure modes that would hurt users the most.

Once the config looks good, propose running a small English-only local baseline evaluation so we can see what kind of signal we actually get.
```

**Best used with:** Grok Build, Claude Code, Codex

---

## 2. "Is This Actually Useful?" Evaluation Prompt

This is the prompt that directly answers your real question.

```text
I want to test whether Eagle Eval actually provides value for our agent development process.

Using the eagle-eval skill:

1. Set up a basic evaluation on this project (or improve the existing one).
2. Run a small but meaningful local evaluation on English (or our main language).
3. After the run completes, read the generated Markdown report(s) in data/results/runs/.
4. Give me an honest assessment:
   - Did the goal achievement and next-action match scores tell us anything useful?
   - Did the scenario breakdowns and recommended fixes point to real problems we should fix?
   - Would this have caught regressions or weak behavior that we care about?

Be direct. Tell me whether you think continuing to use Eagle Eval would meaningfully improve how we ship this agent, or if it's mostly noise.
```

---

## 3. Quick Baseline Prompt (Fastest Way to Get Data)

```text
Using the eagle-eval skill, do the following on this project:

- Create or update a minimal eval_config.yaml focused on English.
- Ensure a working `run_conversation` wrapper exists.
- Run a small local baseline: generate → gate → upload → run (English only).
- After it finishes, read the latest report and give me a concise summary of:
  - Goal achievement rate
  - Next action match rate
  - Top 2-3 failure patterns
  - Whether the recommended fixes seem actionable

Keep it lightweight. I just want to see what the output looks like.
```

---

## 4. Multi-Agent / Orchestrator Evaluation Prompt

Use this if your system has routing, handoffs, or async workers.

```text
This project uses a multi-agent architecture (orchestrator + sub-agents + possibly async workers).

Using the eagle-eval skill and the multi-agent documentation:

1. Help me define good `eval_targets` in eval_config.yaml (one for the full flow + separate targets for key sub-flows).
2. Set up the necessary wrappers.
3. Run evaluations on the main orchestrator and at least 2-3 sub-flows.
4. Run `compare-targets` and analyze the results.
5. Tell me where the orchestrator is stronger or weaker than the individual agents.

Focus especially on whether this helps us debug routing and handoff quality.
```

---

## 5. Custom Scorer Creation Prompt

Once you have a baseline and want to go deeper.

```text
We now have some eval data from Eagle Eval.

Help me create a high-quality custom scorer that directly measures our real North Star (instead of relying only on the built-in goal_achievement).

Steps:
1. Look at our North Star definition in the current eval_config.yaml.
2. Create a new scorer using `eagle-eval scorer init <name> --sample`.
3. Implement a good version of the scorer based on our actual product logic.
4. Register it in eval_config.yaml under `scoring.custom_metrics`.
5. Run a new evaluation and show me the difference in the reports.

Make the scorer as close as possible to how a human would judge success for this product.
```

---

## 6. Post-Run Analysis Prompt (Use After Any Evaluation)

```text
I just ran an Eagle Eval on this project.

Please:
1. Find the most recent report(s) in `data/results/runs/`.
2. Read the Markdown report in detail.
3. Give me a clear analysis focused on:
   - Goal achievement and next-action performance
   - The most painful failure scenarios
   - Whether the "Recommended fixes" are actually good suggestions
   - What we should do next (prompt changes, routing fixes, custom scorer, more languages, etc.)

Be honest about the quality of the signal we got.
```

---

## How to Use These Prompts Effectively

- Paste the prompt **after** you have run `eagle-eval install-assistants`.
- Be specific about which agent/flow you want to evaluate first.
- If the agent gets stuck on setup, point it to `docs/multi-agent-sequential-workflows.md` or `docs/north-star-resolution-policy.md`.
- After the first real run, always use Prompt #6 (Post-Run Analysis) — this is where you get the real signal.

---

## Pro Tip for Grok Build Users

In this environment, you can combine direct CLI commands with agent reasoning very effectively.

Example flow:

1. Run `eagle-eval doctor --verbose` yourself.
2. Then paste Prompt #2 or #6 and let Grok analyze the actual reports.

This hybrid approach (you drive the CLI, Grok does deep analysis) is currently one of the strongest ways to use Eagle Eval.

---

Would you like me to also create a shorter "one-line" version of the most important prompts that you can keep in a notes file?
