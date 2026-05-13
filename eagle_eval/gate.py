"""Quality gate: automated checks + LLM-as-a-judge review on synthetic data."""

import json
import logging
import time
from pathlib import Path

log = logging.getLogger(__name__)


def run_quality_gate(config: dict, data_dir: Path, dry_run: bool = False, verbose: bool = False) -> dict:
    """Run quality checks on all generated conversations."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    threshold = config["synthetic"].get("quality_threshold", 3.5)
    judge_provider = config["evaluation"].get("judge_provider") or _infer_provider(config["evaluation"]["judge_model"])
    judge_model = config["evaluation"]["judge_model"]
    domain = config["domain"]
    persona = config.get("user_persona", "user")

    conversations = _load_all_conversations(data_dir)
    if not conversations:
        return {"total": 0, "passed": 0, "flagged": 0, "failed": 0, "per_language": {}}

    results = {"total": len(conversations), "passed": 0, "flagged": 0, "failed": 0, "per_language": {}}
    quality_scores = {}

    for conv_path, conv in conversations:
        conv_id = conv.get("conversation_id", conv_path.stem)
        lang = conv.get("language", "unknown")

        if lang not in results["per_language"]:
            results["per_language"][lang] = {"total": 0, "passed": 0, "flagged": 0, "failed": 0, "scores": []}
        results["per_language"][lang]["total"] += 1

        # Automated checks
        auto_issues = _auto_checks(conv)
        if auto_issues:
            log.info(f"{conv_id}: auto-check issues: {auto_issues}")

        # LLM quality review
        if dry_run:
            score = {"overall": 4.0, "naturalness": 4, "topic_coverage": 4, "difficulty_match": 4, "language_quality": 4, "issues": "dry run"}
        else:
            score = _llm_quality_review(conv, judge_provider, judge_model, domain, persona)

        if score is None:
            score = {"overall": 0, "issues": "LLM review failed"}

        overall = score.get("overall", 0)
        quality_scores[conv_id] = score
        results["per_language"][lang]["scores"].append(overall)

        # Classify
        if overall >= threshold:
            results["passed"] += 1
            results["per_language"][lang]["passed"] += 1
            conv["quality_score"] = overall
            conv["quality_status"] = "passed"
        elif overall >= threshold - 1.0:
            results["flagged"] += 1
            results["per_language"][lang]["flagged"] += 1
            conv["quality_score"] = overall
            conv["quality_status"] = "flagged"
        else:
            results["failed"] += 1
            results["per_language"][lang]["failed"] += 1
            conv["quality_score"] = overall
            conv["quality_status"] = "failed"

        # Write quality score back into the conversation file unless this is a preview.
        if not dry_run:
            conv_path.write_text(json.dumps(conv, indent=2, ensure_ascii=False))

        log.info(f"{conv_id}: overall={overall:.1f} status={conv['quality_status']}")
        time.sleep(0.3)

    # Compute per-language averages
    for lang, stats in results["per_language"].items():
        scores = stats.pop("scores")
        stats["avg_quality"] = sum(scores) / len(scores) if scores else 0

    return results


def _load_all_conversations(data_dir: Path) -> list[tuple[Path, dict]]:
    """Load all conversation JSON files from data/synthetic/<lang>/."""
    conversations = []
    for json_file in sorted(data_dir.rglob("*.json")):
        if json_file.name in ("manifest.json", "quality_report.json"):
            continue
        try:
            conv = json.loads(json_file.read_text())
            if "conversation_turns" in conv:
                conversations.append((json_file, conv))
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"Skipping {json_file}: {e}")
    return conversations


def _auto_checks(conv: dict) -> list[str]:
    """Run fast automated checks. Returns list of issues."""
    issues = []
    turns = conv.get("conversation_turns", [])

    if len(turns) < 3:
        issues.append(f"too few turns ({len(turns)})")

    # Check for empty turns
    empty = sum(1 for t in turns if not t.get("content", "").strip())
    if empty > 0:
        issues.append(f"{empty} empty turns")

    # Check for exact duplicates
    contents = [t.get("content", "") for t in turns]
    if len(contents) != len(set(contents)):
        issues.append("duplicate turns detected")

    # Check all turns have role=user
    non_user = [t for t in turns if t.get("role") != "user"]
    if non_user:
        issues.append(f"{len(non_user)} turns with role != 'user'")

    # Language detection (fast check on concatenated text)
    try:
        from langdetect import detect
        combined = " ".join(t.get("content", "") for t in turns[:3])
        if len(combined) > 30:
            detected = detect(combined)
            expected = conv.get("language", "")
            if detected.split("-")[0] != expected.split("-")[0]:
                issues.append(f"language mismatch: expected {expected}, detected {detected}")
    except Exception:
        pass

    return issues


def _llm_quality_review(conv: dict, provider: str, model: str, domain: str, persona: str) -> dict | None:
    """Use LLM-as-a-judge to score conversation quality."""
    lang_name = conv.get("language_name", conv.get("language", "unknown"))
    topic = conv.get("primary_topic", "general")
    difficulty = conv.get("difficulty_requested", "medium")
    turns_json = json.dumps(conv.get("conversation_turns", []), ensure_ascii=False)[:3000]

    prompt = f"""Review this synthetic conversation for quality. It should represent a {persona} asking about {topic} in {lang_name}.

Conversation turns (user messages only):
{turns_json}

Score each dimension 1-5:
- naturalness: Does this sound like a real person typing on a phone? Not overly formal or translated?
- topic_coverage: Does the conversation meaningfully explore the topic?
- difficulty_match: Does the actual difficulty match "{difficulty}"?
- language_quality: Is the {lang_name} natural and correct (not machine-translated English)?

Respond with ONLY this JSON, no markdown fences:
{{"naturalness": N, "topic_coverage": N, "difficulty_match": N, "language_quality": N, "overall": N, "issues": "description of any problems or empty string"}}"""

    try:
        provider = _normalize_provider(provider, model)
        if provider == "gemini":
            return _call_gemini_judge(model, prompt)
        elif provider == "openai":
            return _call_openai_judge(model, prompt)
        elif provider == "anthropic":
            return _call_anthropic_judge(model, prompt)
        else:
            log.warning(f"Unsupported judge provider: {provider}")
            return None
    except Exception as e:
        log.error(f"Quality review failed: {e}")
        return None


def _normalize_provider(provider: str | None, model: str) -> str:
    provider = (provider or _infer_provider(model)).strip().lower()
    aliases = {
        "google": "gemini",
        "google-gemini": "gemini",
        "claude": "anthropic",
        "anthropic": "anthropic",
        "openai": "openai",
        "gpt": "openai",
    }
    return aliases.get(provider, provider)


def _infer_provider(model: str) -> str:
    model = model.lower()
    if "gemini" in model:
        return "gemini"
    if "claude" in model:
        return "anthropic"
    if model.startswith(("gpt-", "o1", "o3", "o4")):
        return "openai"
    return "unknown"


def _call_gemini_judge(model: str, prompt: str) -> dict:
    try:
        from google import genai
        client = genai.Client()
        response = client.models.generate_content(model=model, contents=prompt)
    except ImportError:
        from google.generativeai import GenerativeModel
        gm = GenerativeModel(model)
        response = gm.generate_content(prompt)

    return _parse_judge_response(response.text)


def _call_openai_judge(model: str, prompt: str) -> dict:
    from openai import OpenAI

    client = OpenAI()
    response = client.responses.create(model=model, input=prompt)
    return _parse_judge_response(response.output_text)


def _call_anthropic_judge(model: str, prompt: str) -> dict:
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model, max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_judge_response(response.content[0].text)


def _parse_judge_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return json.loads(text.strip())
