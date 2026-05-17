"""Generate synthetic multilingual conversations using a configured model service."""

import json
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)


GENERATION_PROMPT = """You are generating a realistic conversation between a {user_persona} and an AI assistant.

CONTEXT:
- The user speaks {language_name} ({language_code})
- Domain: {domain}
- Primary topic: {topic_name} — {topic_description}
- Difficulty: {difficulty}
- Number of user turns to generate: {num_turns}
- App North Star: {north_star_name} — {north_star_definition}
- Resolution policy: {resolution_policy}

INSTRUCTIONS:
- Generate ONLY the user's messages, not the assistant's responses
- Write ALL messages in {language_name} using natural, colloquial style
- Do NOT translate from English — think and write natively in {language_name}
- For "easy": straightforward single-topic questions
- For "medium": follow-ups requiring context, mild topic drift, some incomplete sentences
- For "hard": ambiguous queries, code-switching with English, typos, multiple topics in one message
- Make it realistic: greetings, thanks, confusion, the way a real {user_persona} types on a basic phone
- Include at least one message that is slightly out of scope or ambiguous
- Vary message length naturally
- Pick the expected scenario from: answerable_now, unclear_intent, missing_critical_context, unsafe_or_high_risk
- Set expected_next_action to one of: answer, ask_clarification, confirm, refuse_or_escalate

OUTPUT FORMAT (strict JSON only, no markdown fences, no preamble):
{{"conversation_turns": [{{"role": "user", "content": "...message in {language_name}..."}}, ...], "topic_tags": ["{topic_id}"], "difficulty_actual": "{difficulty}", "scenario": "missing_critical_context", "expected_next_action": "ask_clarification", "required_clarification_slots": ["crop", "location"], "resolution_goal": "Brief description of what resolved means for this case", "notes": "Brief English description of the conversation"}}"""


def run_generation(config: dict, lang_codes: list[str], proj_dir: Path, verbose: bool = False) -> dict:
    """Generate synthetic conversations and save to data/synthetic/."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    data_dir = proj_dir / "data" / "synthetic"
    data_dir.mkdir(parents=True, exist_ok=True)

    topics = _load_topics(proj_dir / "config" / "topics.json")
    test_cases = config["test_cases"]
    from eagle_eval.generation_clients import call_generation_model
    from eagle_eval.providers import infer_provider

    writer = test_cases.get("writer") or infer_provider(test_cases["writer_model"])
    model = test_cases["writer_model"]
    convs_per_lang = test_cases["conversations_per_language"]
    turns = test_cases["turns_per_conversation"]
    max_concurrency = test_cases.get("max_concurrency", 5)
    domain = config["domain"]
    persona = config.get("user_persona", "user")
    app_context = config["app_context"]
    north_star = app_context.get("north_star", {})
    resolution_policy = app_context.get("resolution_policy", {})

    from eagle_eval.config import get_language_name

    generated = 0
    failed = 0
    sample = None
    manifest_entries = []

    for lang_code in lang_codes:
        lang_name = get_language_name(lang_code)
        lang_dir = data_dir / lang_code
        lang_dir.mkdir(parents=True, exist_ok=True)

        # Distribute conversations across topics
        assignments = _assign_topics(topics, convs_per_lang)

        for idx, (topic, difficulty) in enumerate(assignments):
            conv_id = f"{lang_code}_conv_{idx+1:02d}"
            out_path = lang_dir / f"{conv_id}.json"

            if out_path.exists():
                log.info(f"Skipping {conv_id} — already exists")
                manifest_entries.append(_manifest_entry(conv_id, lang_code, topic, out_path))
                generated += 1
                continue

            prompt = GENERATION_PROMPT.format(
                user_persona=persona,
                language_name=lang_name,
                language_code=lang_code,
                domain=domain,
                topic_name=topic["name"],
                topic_description=topic["description"],
                topic_id=topic["id"],
                difficulty=difficulty,
                num_turns=turns,
                north_star_name=north_star.get("name", "unknown"),
                north_star_definition=north_star.get("definition", ""),
                resolution_policy=json.dumps(resolution_policy, ensure_ascii=False),
            )

            log.info(f"Generating {conv_id} ({lang_name}, {topic['name']}, {difficulty})")

            conversation = call_generation_model(writer, model, prompt, retries=3)
            if conversation is None:
                log.error(f"Failed to generate {conv_id} after 3 retries")
                failed += 1
                continue

            # Enrich and save
            conversation["conversation_id"] = conv_id
            conversation["language"] = lang_code
            conversation["language_name"] = lang_name
            conversation["primary_topic"] = topic["id"]
            conversation["difficulty_requested"] = difficulty
            conversation["generated_by"] = model
            conversation["generated_at"] = datetime.now(timezone.utc).isoformat()

            out_path.write_text(json.dumps(conversation, indent=2, ensure_ascii=False))
            manifest_entries.append(_manifest_entry(conv_id, lang_code, topic, out_path))
            generated += 1

            if sample is None:
                sample = {
                    "language": lang_code,
                    "topic": topic["name"],
                    "turns": conversation.get("conversation_turns", []),
                }

            # Rate limiting
            time.sleep(0.5)

    # Write manifest
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "conversations": manifest_entries,
    }
    (data_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False))

    return {"generated": generated, "failed": failed, "sample": sample}


def _load_topics(topics_path: Path) -> list[dict]:
    """Load topics from config/topics.json."""
    if not topics_path.exists():
        raise FileNotFoundError(f"Topics file not found: {topics_path}. Run 'init' first.")
    return json.loads(topics_path.read_text())


def _assign_topics(topics: list[dict], count: int) -> list[tuple[dict, str]]:
    """Distribute conversations across topics and difficulties."""
    assignments = []
    for topic in topics:
        dist = topic.get("difficulty_distribution", {"easy": 3, "medium": 5, "hard": 2})
        total_weight = sum(dist.values())
        for diff, weight in dist.items():
            n = max(1, round(count * weight / (total_weight * len(topics))))
            assignments.extend([(topic, diff)] * n)

    random.shuffle(assignments)
    return assignments[:count]


def _manifest_entry(conv_id: str, lang_code: str, topic: dict, path: Path) -> dict:
    return {
        "conversation_id": conv_id,
        "language": lang_code,
        "topic": topic["id"],
        "path": str(path),
    }
