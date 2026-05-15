"""Registry of services Eagle Eval knows how to inspect."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Integration:
    key: str
    label: str
    purpose: str
    packages: tuple[str, ...]
    env_vars: tuple[str, ...]
    docs_url: str


INTEGRATIONS = {
    "local": Integration("local", "Local files", "Store datasets, run JSON, and Markdown summaries on disk.", (), (), "README.md#local-results"),
    "langfuse": Integration("langfuse", "Langfuse", "Store datasets, experiment runs, traces, and scores.", ("langfuse",), ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"), "https://langfuse.com/docs/evaluation/overview"),
    "langsmith": Integration("langsmith", "LangSmith", "Run experiments on datasets and inspect scores in LangSmith.", ("langsmith",), ("LANGSMITH_API_KEY",), "https://docs.langchain.com/langsmith/evaluation"),
    "openai": Integration("openai", "OpenAI", "Create test cases, score outputs, and optionally use OpenAI Evals.", ("openai",), ("OPENAI_API_KEY",), "https://developers.openai.com/api/docs/guides/agent-evals"),
    "gemini": Integration("gemini", "Gemini", "Create multilingual test cases and score outputs with Gemini.", ("google.genai",), ("GOOGLE_API_KEY",), "https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/evaluation"),
    "vertex": Integration("vertex", "Vertex AI evaluation", "Use Google's Gen AI evaluation service for task-specific metrics.", ("vertexai",), ("GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION"), "https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/evaluation"),
    "claude": Integration("claude", "Claude", "Create test cases and score outputs with Claude.", ("anthropic",), ("ANTHROPIC_API_KEY",), "https://platform.claude.com/docs/en/test-and-evaluate/develop-tests"),
}

SERVICE_ALIASES = {
    "anthropic": "claude",
    "claude": "claude",
    "gemini": "gemini",
    "google": "gemini",
    "google-gemini": "gemini",
    "gpt": "openai",
    "langfuse": "langfuse",
    "langsmith": "langsmith",
    "local": "local",
    "openai": "openai",
    "vertex": "vertex",
    "vertexai": "vertex",
    "vertex-ai": "vertex",
}

ACTIVE_ROLE_SERVICES = {
    "test_case_writer": {"gemini", "openai", "claude"},
    "scoring_service": {"gemini", "openai", "claude"},
    "result_storage": {"local", "langfuse"},
}
