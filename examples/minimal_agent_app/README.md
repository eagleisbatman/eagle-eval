# Minimal Agent App

This workspace proves that Eagle Eval is SDK-neutral. Eagle Eval does not care
whether your real agent is built with Google ADK, OpenAI Agents SDK, Claude Code
SDK, a direct model API, LangGraph, Mastra, or your own framework.

The only contract is one importable Python function:

```python
def run_conversation(messages, language, prompt_versions=None) -> dict:
    return {
        "responses": ["assistant response text"],
        "tools_called": [],
        "metadata": {"framework": "your-agent-sdk"},
    }
```

## Run Locally Without Service Keys

From the repository root:

```bash
eagle-eval --project-dir examples/minimal_agent_app services
eagle-eval --project-dir examples/minimal_agent_app upload --languages en
eagle-eval --project-dir examples/minimal_agent_app run --languages en
eagle-eval --project-dir examples/minimal_agent_app status
```

The default config uses `sample_agents.rule_based`, so the run is deterministic
and does not call a paid API.

## Try A Live SDK Wrapper

Change `eval_config.yaml`:

```yaml
agent:
  module: sample_agents.openai_agents
  function: run_conversation
```

Available sample wrappers:

- `sample_agents.google_adk`: Google ADK style `root_agent` plus runner wrapper.
- `sample_agents.openai_agents`: OpenAI Agents SDK `Agent` plus `Runner.run_sync`.
- `sample_agents.claude_code_sdk`: Claude Code SDK client wrapper.
- `sample_agents.anthropic_messages`: direct Anthropic Messages API wrapper.
- `sample_agents.rule_based`: offline deterministic wrapper for tests and demos.

Then install the SDK and set the required env var for the wrapper you chose.
Use `eagle-eval services --verbose` to check service readiness before live runs.
