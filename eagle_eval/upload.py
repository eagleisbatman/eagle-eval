"""Send quality-gated conversations to the configured result destination."""

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def run_upload(config: dict, lang_codes: list[str], data_dir: Path,
               recreate: bool = False, dry_run: bool = False, verbose: bool = False) -> dict:
    """Send quality-gated conversations to the configured result destination."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    prefix = config.get("langfuse", {}).get("dataset_prefix", "evals")
    destination = str(config.get("results", {}).get("destination", "langfuse")).strip().lower()
    if destination == "local":
        from eagle_eval.local_datasets import local_results_dir, write_local_datasets

        if dry_run:
            project_dir = data_dir.expanduser().resolve().parent.parent
            datasets_dir = local_results_dir(config, project_dir) / "datasets"
            results = {"datasets": {}, "total_items": 0}
            for lang_code in lang_codes:
                count = len(_load_passed_conversations(data_dir / lang_code))
                dataset_path = datasets_dir / f"{lang_code}_conversations.json"
                results["datasets"][str(dataset_path)] = count
                results["total_items"] += count
            return results

        return write_local_datasets(config, lang_codes, data_dir, recreate=recreate)

    if destination != "langfuse" and not dry_run:
        raise RuntimeError(
            f"Live upload currently supports Langfuse. Configured result destination: {destination}. "
            "Run 'eagle-eval doctor --verbose' to inspect SDK readiness."
        )

    if not dry_run:
        try:
            from langfuse import get_client
        except ImportError as exc:
            raise RuntimeError(
                "The Langfuse result destination requires the Langfuse extra. "
                "Install it with: python -m pip install 'eagle-eval[langfuse]'"
            ) from exc
        lf = get_client()

    results = {"datasets": {}, "total_items": 0}

    for lang_code in lang_codes:
        lang_dir = data_dir / lang_code
        if not lang_dir.exists():
            log.warning(f"No data directory for {lang_code}, skipping")
            continue

        conversations = _load_passed_conversations(lang_dir)
        if not conversations:
            log.warning(f"No passed conversations for {lang_code}, skipping")
            continue

        dataset_name = f"{prefix}/{lang_code}/conversations"

        if dry_run:
            log.info(f"[dry-run] Would create dataset '{dataset_name}' with {len(conversations)} items")
            results["datasets"][dataset_name] = len(conversations)
            results["total_items"] += len(conversations)
            continue

        # Create or get dataset
        if recreate:
            try:
                lf.api.datasets.delete(dataset_name=dataset_name)
                log.info(f"Deleted existing dataset: {dataset_name}")
            except Exception:
                pass

        lf.create_dataset(name=dataset_name, description=f"Eval conversations for {lang_code}")

        item_count = 0
        for conv in conversations:
            from eagle_eval.local_datasets import conversation_to_dataset_item

            item = conversation_to_dataset_item(lang_code, conv)

            lf.create_dataset_item(
                dataset_name=dataset_name,
                input=item["input"],
                expected_output=item["expected_output"],
                metadata=item["metadata"],
            )
            item_count += 1
            log.debug(f"Uploaded {conv.get('conversation_id')} to {dataset_name}")

        results["datasets"][dataset_name] = item_count
        results["total_items"] += item_count
        log.info(f"{dataset_name}: {item_count} items uploaded")

    # Flush
    if not dry_run:
        lf.flush()

    return results


def _load_passed_conversations(lang_dir: Path) -> list[dict]:
    """Load conversations that passed quality gate."""
    conversations = []
    for json_file in sorted(lang_dir.glob("*.json")):
        try:
            conv = json.loads(json_file.read_text())
            status = conv.get("quality_status")
            if status in ("passed", "flagged"):  # include flagged — they're borderline, not bad
                conversations.append(conv)
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"Skipping {json_file}: {e}")
    return conversations
