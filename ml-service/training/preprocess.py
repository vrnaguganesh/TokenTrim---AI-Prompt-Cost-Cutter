"""Normalize, validate, measure, and split TokenTrim training examples."""

import csv
import json
import logging
import random
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from tiktoken import get_encoding

SCRIPT_DIR = Path(__file__).resolve().parent
SERVICE_DIR = SCRIPT_DIR.parent
if str(SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(SERVICE_DIR))

from app.services.semantic_service import SemanticService

RAW_PATH = SERVICE_DIR / "data" / "raw" / "raw_dataset.jsonl"
PROCESSED_DIR = SERVICE_DIR / "data" / "processed"
SPLITS_DIR = SERVICE_DIR / "data" / "splits"
CSV_COLUMNS = [
    "id", "source_dataset", "original_prompt", "optimized_prompt",
    "original_tokens", "optimized_tokens", "tokens_saved",
    "reduction_percentage", "semantic_score", "optimization_label",
]
ENCODING = get_encoding("cl100k_base")
LOGGER = logging.getLogger(__name__)

_ORIGINAL_NAMES = (
    "original_prompt", "original", "prompt", "input", "verbose_prompt",
    "question", "instruction", "text",
)
_OPTIMIZED_NAMES = (
    "optimized_prompt", "optimized", "compressed", "compression",
    "compressed_prompt", "output", "response", "completion", "chosen",
)


def count_tokens(text: Any) -> int:
    return len(ENCODING.encode(str(text)))


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("content", "text", "value"):
            if key in value:
                return _text(value[key])
        return " ".join(_text(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return "\n".join(_text(item) for item in value)
    return ""


def normalize_whitespace(value: Any) -> str:
    text = _text(value).replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(line for line in lines if line)).strip()


def _find_field(record: Dict[str, Any], names: Sequence[str]) -> str:
    lowered = {str(key).lower(): key for key in record}
    for name in names:
        if name in lowered:
            return _text(record[lowered[name]])
    return ""


def _message_pair(record: Dict[str, Any]) -> Tuple[str, str]:
    messages = record.get("messages")
    if not isinstance(messages, list):
        return "", ""
    user_parts = []
    assistant_parts = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).lower()
        content = normalize_whitespace(message.get("content", ""))
        if role == "user" and content:
            user_parts.append(content)
        elif role == "assistant" and content:
            assistant_parts.append(content)
    original = "\n".join(user_parts)
    original = re.sub(r"^\s*compress\s*:\s*", "", original, flags=re.IGNORECASE)
    return original, "\n".join(assistant_parts)


def _infer_pair(record: Dict[str, Any]) -> Tuple[str, str]:
    """Use field names first, then infer a pair from textual fields."""
    message_original, message_optimized = _message_pair(record)
    if message_original and message_optimized:
        return message_original, message_optimized
    original = _find_field(record, _ORIGINAL_NAMES)
    optimized = _find_field(record, _OPTIMIZED_NAMES)
    if original and optimized and original != optimized:
        return original, optimized
    candidates = [
        normalize_whitespace(value)
        for value in record.values()
        if normalize_whitespace(value)
    ]
    candidates = list(dict.fromkeys(candidates))
    if len(candidates) < 2:
        return original, optimized
    # The verbose input is generally the longer field; preserve source order
    # when both values are similarly sized.
    longest = max(candidates, key=len)
    shortest = min(candidates, key=len)
    return original or longest, optimized or shortest


def normalize_record(raw: Dict[str, Any], index: int) -> Optional[Dict[str, Any]]:
    record = raw.get("record", raw)
    if not isinstance(record, dict):
        return None
    original, optimized = _infer_pair(record)
    original = normalize_whitespace(original)
    optimized = normalize_whitespace(optimized)
    if not original or not optimized or len(original) < 3 or len(optimized) < 2:
        return None
    source = raw.get("source_dataset", record.get("source_dataset", "unknown"))
    if source not in ("BPO", "semantic-compression-sft"):
        source = "semantic-compression-sft" if "compression" in str(source).lower() else "BPO"
    return {
        "id": f"{str(source).lower().replace('-', '_')}_{index}",
        "source_dataset": source,
        "original_prompt": original,
        "optimized_prompt": optimized,
    }


def _label(original: str, optimized: str, tokens_saved: int) -> str:
    if original == optimized or tokens_saved <= 0:
        return "KEEP"
    original_words = set(re.findall(r"\b\w+\b", original.lower()))
    optimized_words = set(re.findall(r"\b\w+\b", optimized.lower()))
    removed_words = original_words - optimized_words
    filler_words = {
        "can", "could", "please", "kindly", "would", "you", "me", "with",
        "in", "order", "to", "very", "just", "really", "that", "if",
        "possible", "thank", "thanks", "advance", "hello",
    }
    # REMOVE describes redundant segments, not an entire verbose prompt.
    removed_sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", original)
        if sentence.strip() and sentence.lower() not in optimized.lower()
    ]
    if (
        removed_sentences
        and all(
            set(re.findall(r"\b\w+\b", sentence.lower())) <= filler_words
            for sentence in removed_sentences
        )
        and tokens_saved >= 2
    ):
        return "REMOVE"
    return "COMPRESS"


def _deduplicate(records: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: set[Tuple[str, str]] = set()
    near_buckets: Dict[Tuple[int, str], List[Tuple[str, str]]] = {}
    result = []
    for record in records:
        key = (
            re.sub(r"\W+", " ", record["original_prompt"].lower()).strip(),
            re.sub(r"\W+", " ", record["optimized_prompt"].lower()).strip(),
        )
        bucket_key = (len(key[0]) // 40, key[0][:32])
        near_duplicate = any(
            SequenceMatcher(None, key[0], existing[0]).ratio() >= 0.98
            and SequenceMatcher(None, key[1], existing[1]).ratio() >= 0.98
            for existing in near_buckets.get(bucket_key, [])
        )
        if key not in seen and not near_duplicate:
            seen.add(key)
            near_buckets.setdefault(bucket_key, []).append(key)
            result.append(record)
    return result


def preprocess_dataset(raw_path: Path = RAW_PATH, seed: int = 42) -> Tuple[Path, Path, Path, Path]:
    if not raw_path.exists():
        raise FileNotFoundError(f"Raw dataset not found: {raw_path}. Run download_dataset.py first.")
    records: List[Dict[str, Any]] = []
    with raw_path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            try:
                normalized = normalize_record(json.loads(line), index)
            except (json.JSONDecodeError, TypeError, ValueError):
                LOGGER.exception("Skipping malformed dataset record %s", index)
                continue
            if normalized:
                records.append(normalized)
    records = _deduplicate(records)
    try:
        pairs = [(item["original_prompt"], item["optimized_prompt"]) for item in records]
        scores = []
        batch_size = 64
        for start in range(0, len(pairs), batch_size):
            scores.extend(
                SemanticService.calculate_batch_similarities(
                    pairs[start:start + batch_size]
                )
            )
    except Exception:
        LOGGER.exception("Semantic embedding failed; no records were fabricated.")
        raise
    enriched = []
    for item, score in zip(records, scores):
        original_tokens = count_tokens(item["original_prompt"])
        optimized_tokens = count_tokens(item["optimized_prompt"])
        saved = original_tokens - optimized_tokens
        item.update({
            "original_tokens": original_tokens,
            "optimized_tokens": optimized_tokens,
            "tokens_saved": saved,
            "reduction_percentage": round(saved / original_tokens * 100, 2) if original_tokens else 0.0,
            "semantic_score": round(float(score), 4),
            "optimization_label": _label(item["original_prompt"], item["optimized_prompt"], saved),
        })
        if not (item["semantic_score"] < 0.65 and item["reduction_percentage"] > 85):
            enriched.append(item)
    if not enriched:
        raise ValueError("No valid records remained after normalization and validation.")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED_DIR / "tokentrim_semantic_compression.csv"
    _write_csv(output_path, enriched)
    rng = random.Random(seed)
    by_source: Dict[str, List[Dict[str, Any]]] = {}
    for record in enriched:
        by_source.setdefault(record["source_dataset"], []).append(record)
    split_records: Dict[str, List[Dict[str, Any]]] = {
        "train": [], "validation": [], "test": []
    }
    for source_records in by_source.values():
        rng.shuffle(source_records)
        n_train = int(len(source_records) * 0.8)
        n_val = int(len(source_records) * 0.1)
        split_records["train"].extend(source_records[:n_train])
        split_records["validation"].extend(source_records[n_train:n_train + n_val])
        split_records["test"].extend(source_records[n_train + n_val:])
    for records in split_records.values():
        rng.shuffle(records)
    splits = tuple(split_records.items())
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, split_records in splits:
        path = SPLITS_DIR / f"{name}.csv"
        _write_csv(path, split_records)
        paths.append(path)
        # Retain the old artifact format for existing consumers.
        with (SPLITS_DIR / f"{name}.jsonl").open("w", encoding="utf-8") as handle:
            for item in split_records:
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"Prepared {len(enriched)} records: {output_path}")
    return (output_path, *paths)


def _write_csv(path: Path, records: List[Dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows({key: record.get(key, "") for key in CSV_COLUMNS} for record in records)


if __name__ == "__main__":
    preprocess_dataset()
