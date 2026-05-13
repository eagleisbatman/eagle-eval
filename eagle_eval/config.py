"""Load eval_config.yaml and generate config/languages.json + config/topics.json."""

import json
from pathlib import Path

import yaml

# ISO 639-1 language database (subset — enough to fill 50+ languages)
ALL_LANGUAGES = [
    {"code": "en", "name": "English", "direction": "ltr"},
    {"code": "hi", "name": "Hindi", "direction": "ltr"},
    {"code": "sw", "name": "Swahili", "direction": "ltr"},
    {"code": "fr", "name": "French", "direction": "ltr"},
    {"code": "pt", "name": "Portuguese", "direction": "ltr"},
    {"code": "am", "name": "Amharic", "direction": "ltr"},
    {"code": "ha", "name": "Hausa", "direction": "ltr"},
    {"code": "yo", "name": "Yoruba", "direction": "ltr"},
    {"code": "zu", "name": "Zulu", "direction": "ltr"},
    {"code": "ig", "name": "Igbo", "direction": "ltr"},
    {"code": "ar", "name": "Arabic", "direction": "rtl"},
    {"code": "bn", "name": "Bengali", "direction": "ltr"},
    {"code": "ta", "name": "Tamil", "direction": "ltr"},
    {"code": "te", "name": "Telugu", "direction": "ltr"},
    {"code": "mr", "name": "Marathi", "direction": "ltr"},
    {"code": "gu", "name": "Gujarati", "direction": "ltr"},
    {"code": "kn", "name": "Kannada", "direction": "ltr"},
    {"code": "ml", "name": "Malayalam", "direction": "ltr"},
    {"code": "ur", "name": "Urdu", "direction": "rtl"},
    {"code": "pa", "name": "Punjabi", "direction": "ltr"},
    {"code": "ne", "name": "Nepali", "direction": "ltr"},
    {"code": "si", "name": "Sinhala", "direction": "ltr"},
    {"code": "my", "name": "Burmese", "direction": "ltr"},
    {"code": "km", "name": "Khmer", "direction": "ltr"},
    {"code": "lo", "name": "Lao", "direction": "ltr"},
    {"code": "th", "name": "Thai", "direction": "ltr"},
    {"code": "vi", "name": "Vietnamese", "direction": "ltr"},
    {"code": "id", "name": "Indonesian", "direction": "ltr"},
    {"code": "ms", "name": "Malay", "direction": "ltr"},
    {"code": "tl", "name": "Filipino", "direction": "ltr"},
    {"code": "zh", "name": "Chinese (Simplified)", "direction": "ltr"},
    {"code": "ja", "name": "Japanese", "direction": "ltr"},
    {"code": "ko", "name": "Korean", "direction": "ltr"},
    {"code": "es", "name": "Spanish", "direction": "ltr"},
    {"code": "de", "name": "German", "direction": "ltr"},
    {"code": "it", "name": "Italian", "direction": "ltr"},
    {"code": "ru", "name": "Russian", "direction": "ltr"},
    {"code": "uk", "name": "Ukrainian", "direction": "ltr"},
    {"code": "pl", "name": "Polish", "direction": "ltr"},
    {"code": "ro", "name": "Romanian", "direction": "ltr"},
    {"code": "nl", "name": "Dutch", "direction": "ltr"},
    {"code": "tr", "name": "Turkish", "direction": "ltr"},
    {"code": "fa", "name": "Persian", "direction": "rtl"},
    {"code": "he", "name": "Hebrew", "direction": "rtl"},
    {"code": "rw", "name": "Kinyarwanda", "direction": "ltr"},
    {"code": "sn", "name": "Shona", "direction": "ltr"},
    {"code": "so", "name": "Somali", "direction": "ltr"},
    {"code": "lg", "name": "Luganda", "direction": "ltr"},
    {"code": "ny", "name": "Chichewa", "direction": "ltr"},
    {"code": "xh", "name": "Xhosa", "direction": "ltr"},
    {"code": "af", "name": "Afrikaans", "direction": "ltr"},
    {"code": "mg", "name": "Malagasy", "direction": "ltr"},
    {"code": "wo", "name": "Wolof", "direction": "ltr"},
    {"code": "ff", "name": "Fula", "direction": "ltr"},
    {"code": "om", "name": "Oromo", "direction": "ltr"},
    {"code": "ti", "name": "Tigrinya", "direction": "ltr"},
]


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

    required_keys = ["app_name", "domain", "agent", "languages", "prompt_versions", "test_cases", "scoring", "results"]
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
