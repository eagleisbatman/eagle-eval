"""Helpers for importing and calling project agent wrappers."""

import importlib
import inspect


def load_agent(config: dict):
    module_name = config["agent"]["module"]
    function_name = config["agent"]["function"]
    try:
        module = importlib.import_module(module_name)
        return getattr(module, function_name)
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(
            f"Cannot import agent: {module_name}.{function_name} — {exc}\n\n"
            "Common fixes:\n"
            "  • Run from the project root (or use --project-dir)\n"
            "  • Make sure the module path in eval_config.yaml matches your actual file structure\n"
            "  • The wrapper must be named exactly 'run_conversation(messages, language, prompt_versions=None)'\n"
            "  • For packages, ensure __init__.py exists and the path is importable\n\n"
            "Run 'eagle-eval doctor' for more diagnostics."
        ) from exc


def call_agent(agent_fn, item_input: dict, prompt_versions: dict) -> dict:
    messages = item_input.get("conversation_turns", [])
    language = item_input.get("language", "en")
    if _accepts_prompt_versions(agent_fn):
        result = agent_fn(messages=messages, language=language, prompt_versions=prompt_versions)
    else:
        result = agent_fn(messages=messages, language=language)

    if not isinstance(result, dict):
        return {"responses": [str(result)], "tools_called": [], "metadata": {}}
    return result


def _accepts_prompt_versions(agent_fn) -> bool:
    try:
        signature = inspect.signature(agent_fn)
    except (TypeError, ValueError):
        return True
    return "prompt_versions" in signature.parameters or any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
