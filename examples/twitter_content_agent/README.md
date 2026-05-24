# Twitter/X Content Agent

This example dogfoods Eagle Eval on a realistic content agent: research the
latest Generative AI updates and draft one publishable Twitter/X post.

It includes three separate wrappers around the same Eagle Eval contract:

- `sample_agents.google_adk`: Google ADK style wrapper
- `sample_agents.openai_agents`: OpenAI Agents SDK wrapper
- `sample_agents.claude_code_sdk`: Claude Code SDK wrapper

The default mode is deterministic and offline, so CI and first-time users can
run the full eval without provider credentials. Set
`EAGLE_EVAL_TWITTER_AGENT_MODE=live` after installing the relevant SDK and API
key when you want the wrapper to call the real provider.

## Research Snapshot

The sample uses `twitter_content_agent/latest_genai_updates.json`, curated on
2026-05-15 from official provider sources:

- OpenAI: Codex in the ChatGPT mobile app preview
- Google: Gemini Intelligence on Android
- Anthropic: Gates Foundation partnership and Claude for Small Business
- OpenAI: realtime voice API models

Refresh that JSON when you want the sample to track newer news. Eagle Eval
does not need to know how the agent researches; it only evaluates the output
shape and the product-specific scoring contract.

## Run All Three Wrappers Locally

From the repository root:

```bash
eagle-eval --project-dir examples/twitter_content_agent services
eagle-eval --project-dir examples/twitter_content_agent upload --languages en --recreate

eagle-eval --project-dir examples/twitter_content_agent run \
  --languages en \
  --agent-module sample_agents.google_adk \
  --run-prefix google-adk

eagle-eval --project-dir examples/twitter_content_agent run \
  --languages en \
  --agent-module sample_agents.openai_agents \
  --run-prefix openai-agents

eagle-eval --project-dir examples/twitter_content_agent run \
  --languages en \
  --agent-module sample_agents.claude_code_sdk \
  --run-prefix claude-code

eagle-eval --project-dir examples/twitter_content_agent status
```

Each run writes JSON and Markdown reports under `data/results/runs/`.

## Live SDK Mode

Install only what you want to test:

```bash
pip install google-adk
pip install openai-agents
pip install claude-code-sdk
npm install -g @anthropic-ai/claude-code
```

Then put the relevant values in `.env.eagle-eval` and enable live mode:

```bash
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_PROJECT=your-gcp-project
GOOGLE_CLOUD_LOCATION=us-central1
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
EAGLE_EVAL_TWITTER_AGENT_MODE=live
```

Run the same commands above. Do not commit local reports or secrets.
