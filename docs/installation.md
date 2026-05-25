# Installation Guide

This guide explains how to install Eagle Eval so you can actually use it on your own agent projects with Claude Code, Codex, or Grok Build.

## Quick Recommendation

**If you want to test Eagle Eval right now with your coding agents:**

```bash
# 1. Clone the repo somewhere (you only need to do this once)
git clone https://github.com/eagleisbatman/eagle-eval.git
cd eagle-eval

# 2. Install in editable mode with the extras you need
python -m pip install -e ".[dev,vertex,bedrock]"

# 3. Install the assistant skills (very important)
eagle-eval install-assistants --tool all --scope global --yes
```

Then go to any of your agent projects and start using `/eagle-eval` (Claude Code) or ask your coding agent to set it up.

---

## Installation Methods

### 1. For Daily Use with Coding Agents (Recommended)

This is the path most people should take when they want to evaluate real agents.

```bash
# Clone Eagle Eval (do this once)
git clone https://github.com/eagleisbatman/eagle-eval.git
cd eagle-eval

# Install with Vertex AI Gemini (recommended Google path) and Amazon Bedrock Claude
python -m pip install -e ".[dev,vertex,bedrock]"

# Or install with everything if you experiment a lot
python -m pip install -e ".[all]"
```

After installation, run this once:

```bash
eagle-eval install-assistants --tool all --scope global --yes
```

This gives you:
- The `/eagle-eval` command in Claude Code
- The eagle-eval skill in Codex
- Good instructions for Grok Build

From then on, you can use Eagle Eval on **any** of your agent projects without reinstalling.

### 2. Install Specific Extras Only

```bash
# Just OpenAI
python -m pip install -e ".[openai]"

# Just Anthropic / Claude
python -m pip install -e ".[anthropic]"

# Amazon Bedrock Claude through AWS
python -m pip install -e ".[bedrock]"

# Langfuse + Vertex AI Gemini
python -m pip install -e ".[vertex,langfuse]"

# Gemini Developer API key path, if you explicitly choose it
python -m pip install -e ".[gemini]"
```

### 3. Using the Latest Version from Git (Without Cloning)

If you don't want to keep a local clone, you can install directly from Git:

```bash
# Latest main
python -m pip install "git+https://github.com/eagleisbatman/eagle-eval.git@main"

# With extras
python -m pip install "eagle-eval[vertex,bedrock] @ git+https://github.com/eagleisbatman/eagle-eval.git@main"
```

**Note:** This method is less convenient for running `install-assistants` globally because the package is not in editable mode.

### 4. Using pipx from Git

Until Eagle Eval is on PyPI, you can still install the CLI globally from Git:

```bash
pipx install "eagle-eval[vertex,bedrock] @ git+https://github.com/eagleisbatman/eagle-eval.git@main"
eagle-eval install-assistants --tool all --scope global --yes
```

This keeps Eagle Eval isolated from your project environments while still making the command and assistant skills available globally.

---

## Google Credentials

Eagle Eval defaults Google-backed writing and scoring to Gemini on Vertex AI.
Use your normal Google Cloud Application Default Credentials or service account
flow, then put the following in either project `.env.eagle-eval` or global
`~/.eagle-eval/.env`:

```bash
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_CLOUD_LOCATION=us-central1
```

If you intentionally use the Gemini Developer API key path instead, configure
`test_cases.writer: gemini` or `scoring.scorer: gemini`, then add:

```bash
GOOGLE_API_KEY=your-gemini-developer-api-key
```

## Amazon Bedrock Claude Credentials

Use this path when your Claude access comes through AWS Bedrock. Install the
Bedrock extra, then store non-secret runtime defaults in project
`.env.eagle-eval` or global `~/.eagle-eval/.env`:

```bash
AWS_PROFILE=eagle-bedrock
AWS_REGION=us-east-1
AWS_BEDROCK_CLAUDE_MODEL_ID=global.anthropic.claude-sonnet-4-5-20250929-v1:0
AWS_BEDROCK_CLAUDE_FAST_MODEL_ID=global.anthropic.claude-haiku-4-5-20251001-v1:0
```

If your environment already has default AWS credentials or an instance role,
omit `AWS_PROFILE` and keep `AWS_REGION` plus the model id. Configure
`test_cases.writer: bedrock` or `scoring.scorer: bedrock` in
`eval_config.yaml`.

Eagle Eval automatically loads env files in this order:

1. `~/.eagle-eval/.env`
2. `.env` in the evaluated project
3. `.env.eagle-eval` in the evaluated project

Later files override earlier values, so project-specific credentials can safely
override machine-wide defaults. `doctor --verbose` and `services --verbose`
show which files were loaded without printing secret values.

---

## Setting Up the Coding Agent Integration

After installing Eagle Eval, run this command **once** (highly recommended):

```bash
eagle-eval install-assistants --tool all --scope global --yes
```

This is what makes the tool feel magical with Claude Code, Codex, and Grok Build.

You can also install it per-project:

```bash
eagle-eval install-assistants --tool all --yes          # project scope
```

---

## Current Limitations (Be Honest With Yourself)

As of version 0.2.0, Eagle Eval has these installation realities:

- It is **not yet published** to PyPI.
- You must install it from source (or git) for now.
- The cleanest experience is still cloning the repo once and using editable installs.
- `pipx` works from Git, but there is no short PyPI install command yet.

This is acceptable while you're testing whether the tool actually provides value on your real agents. Once you decide it's worth using long-term, we can prioritize a proper PyPI release.

---

## Recommended Workflow for Testing on Real Projects

1. Install Eagle Eval once using the method in "For Daily Use with Coding Agents".
2. Run `eagle-eval install-assistants --tool all --scope global --yes`.
3. Go to one of your real agent projects.
4. Ask your coding agent:

   > "Using the eagle-eval skill, set up evaluation for this project and run a small local English baseline so we can see if it actually helps."

5. Evaluate the experience and the quality of the results.
6. Decide whether to continue using it or invest in a PyPI release + more polish.

This is the pragmatic way to answer the question: *"Does this actually make sense for our agents?"*

---

## Ready-to-Use Prompts for Your Coding Agent

After installation, the fastest way to get value is to use well-written prompts with your coding agent.

See the full set of copy-paste templates here:

→ **[Agent Prompt Templates](agent-prompt-templates.md)**

The two most useful ones to start with are:
- Prompt #1 (First-Time Setup)
- Prompt #2 ("Is This Actually Useful?" Evaluation)

---

## Troubleshooting

**"eagle-eval command not found"**
- Make sure you installed it with `pip install -e ...` in the environment where you are running the command.
- If using multiple Python environments, activate the correct one.

**Coding agent can't find the `eagle-eval` skill**
- Run `eagle-eval install-assistants --tool all --scope global --yes` again.
- Restart Claude Code / Codex if necessary.

**Want to use a specific branch or commit?**
Use the git install method with `@branch` or `@commit-sha`.

---

## Next Steps After Installation

- Read [Getting Started](getting-started.md)
- Read [Using with Grok Build](using-with-grok-build.md) (especially relevant if you're in this environment)
- Read [North Star + Resolution Policy](north-star-resolution-policy.md) before doing serious work

The goal of good installation documentation is to get you to the point where you can actually test the tool on real agents as quickly as possible — without fighting the setup.
