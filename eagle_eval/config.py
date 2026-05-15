"""Load eval_config.yaml and generate config/languages.json + config/topics.json."""

import json
from pathlib import Path

import yaml

from eagle_eval.languages import ALL_LANGUAGES


def load_config(config_path: Path) -> dict:
    """Load and validate eval_config.yaml."""
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config not found at {config_path}. Run 'eagle-eval init' first."
        )

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not isinstance(config, dict):
        raise ValueError("eval_config.yaml must contain a YAML mapping/object")

    required_keys = [
        "app_name",
        "domain",
        "user_persona",
        "app_context",
        "agent",
        "languages",
        "prompt_versions",
        "test_cases",
        "scoring",
        "results",
    ]
    missing = [k for k in required_keys if k not in config]
    if missing:
        raise ValueError(f"Missing required config keys: {missing}")

    if not isinstance(config["agent"], dict) or "module" not in config["agent"] or "function" not in config["agent"]:
        raise ValueError("agent.module and agent.function are required in config")

    if not isinstance(config["languages"], dict):
        raise ValueError("languages must be a mapping with tier1/tier2 lists")
    if not config["languages"].get("tier1"):
        raise ValueError("languages.tier1 must contain at least one language code")

    if not isinstance(config["prompt_versions"], dict) or not isinstance(config["prompt_versions"].get("current"), dict):
        raise ValueError("prompt_versions.current must be a mapping of prompt names to versions")

    for section in ("test_cases", "scoring", "results"):
        if not isinstance(config[section], dict):
            raise ValueError(f"{section} must be a mapping")

    if "writer" not in config["test_cases"] or "writer_model" not in config["test_cases"]:
        raise ValueError("test_cases.writer and test_cases.writer_model are required in config")

    if "scorer" not in config["scoring"] or "scorer_model" not in config["scoring"]:
        raise ValueError("scoring.scorer and scoring.scorer_model are required in config")

    if not isinstance(config["app_context"], dict):
        raise ValueError("app_context must be a mapping")
    north_star = config["app_context"].get("north_star")
    if not isinstance(north_star, dict) or "name" not in north_star or "definition" not in north_star:
        raise ValueError("app_context.north_star.name and app_context.north_star.definition are required")

    custom_metrics = config["scoring"].get("custom_metrics", [])
    if custom_metrics is None:
        custom_metrics = []
    if not isinstance(custom_metrics, list):
        raise ValueError("scoring.custom_metrics must be a list")
    for index, metric in enumerate(custom_metrics):
        if not isinstance(metric, dict):
            raise ValueError(f"scoring.custom_metrics[{index}] must be a mapping")
        if "name" not in metric or "path" not in metric:
            raise ValueError(f"scoring.custom_metrics[{index}] requires name and path")

    if "destination" not in config["results"]:
        raise ValueError("results.destination is required in config")

    return config


def generate_config_files(config: dict, config_dir: Path):
    """Generate languages.json and topics.json from config."""
    config_dir.mkdir(parents=True, exist_ok=True)

    # Build languages.json
    tier1_codes = set(config["languages"].get("tier1", []))
    tier2_codes = set(config["languages"].get("tier2", []))
    target_count = config["languages"].get("count", 50)

    languages = []
    used_codes = set()

    for lang in ALL_LANGUAGES:
        code = lang["code"]
        if code in tier1_codes:
            languages.append({**lang, "tier": 1})
            used_codes.add(code)
        elif code in tier2_codes:
            languages.append({**lang, "tier": 2})
            used_codes.add(code)

    # Fill tier 3 up to target count
    for lang in ALL_LANGUAGES:
        if len(languages) >= target_count:
            break
        if lang["code"] not in used_codes:
            languages.append({**lang, "tier": 3})
            used_codes.add(lang["code"])

    languages.sort(key=lambda x: (x["tier"], x["code"]))

    langs_path = config_dir / "languages.json"
    langs_path.write_text(json.dumps(languages, indent=2, ensure_ascii=False))

    # Build topics.json
    topics = []
    for i, topic_name in enumerate(config.get("domain_topics", [])):
        topics.append({
            "id": topic_name.lower().replace(" ", "_").replace("-", "_"),
            "name": topic_name.title(),
            "description": f"User needs help with {topic_name}",
            "difficulty_distribution": {"easy": 3, "medium": 5, "hard": 2},
        })

    # Add adversarial topics
    topics.append({
        "id": "out_of_scope",
        "name": "Out of Scope Request",
        "description": "User asks something completely outside the domain",
        "difficulty_distribution": {"easy": 0, "medium": 0, "hard": 10},
    })
    topics.append({
        "id": "ambiguous",
        "name": "Ambiguous Query",
        "description": "User asks something vague or unclear that could mean multiple things",
        "difficulty_distribution": {"easy": 0, "medium": 5, "hard": 5},
    })

    topics_path = config_dir / "topics.json"
    topics_path.write_text(json.dumps(topics, indent=2, ensure_ascii=False))


def get_language_name(code: str, config_dir: Path = None) -> str:
    """Get English name for a language code."""
    for lang in ALL_LANGUAGES:
        if lang["code"] == code:
            return lang["name"]
    return code
