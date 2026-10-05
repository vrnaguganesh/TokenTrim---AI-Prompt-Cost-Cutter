"""Download and inspect the datasets used by the TokenTrim training pipeline."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from datasets import load_dataset

SCRIPT_DIR = Path(__file__).resolve().parent
SERVICE_DIR = SCRIPT_DIR.parent
RAW_DIR = SERVICE_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
LOGGER = logging.getLogger(__name__)


def load_semantic_compression_dataset():
    print("Loading Semantic Compression SFT dataset...")
    try:
        dataset = load_dataset("Sudhendra/semantic-compression-sft")
    except Exception:
        LOGGER.exception("Unable to download Sudhendra/semantic-compression-sft")
        raise
    print("Dataset loaded successfully.")
    return dataset


def _load_bpo_dataset():
    try:
        return load_dataset("zai-org/BPO")
    except Exception:
        LOGGER.exception("Unable to download zai-org/BPO")
        raise


def _records(dataset: Any) -> Iterable[Dict[str, Any]]:
    for split_name, split in dataset.items():
        for index, record in enumerate(split):
            yield {"source_dataset": split_name, "source_index": index, **dict(record)}


def download_and_save_raw_data() -> Path:
    """Download both sources and persist a lossless JSONL staging file."""
    semantic = load_semantic_compression_dataset()
    print(semantic)
    train = semantic["train"] if "train" in semantic else next(iter(semantic.values()))
    print(train.column_names)
    print(train[0])
    print(f"Dataset splits: {list(semantic.keys())}")
    print(f"Number of records: {sum(len(split) for split in semantic.values())}")
    print(f"Column names: {train.column_names}")
    print(f"Sample record: {train[0]}")

    bpo = _load_bpo_dataset()
    all_records: List[Dict[str, Any]] = []
    for dataset_name, dataset in (
        ("BPO", bpo),
        ("semantic-compression-sft", semantic),
    ):
        for split_name, split in dataset.items():
            for index, record in enumerate(split):
                all_records.append({
                    "source_dataset": dataset_name,
                    "source_split": split_name,
                    "source_index": index,
                    "record": dict(record),
                })

    output_path = RAW_DIR / "raw_dataset.jsonl"
    try:
        with output_path.open("w", encoding="utf-8") as handle:
            for record in all_records:
                handle.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    except OSError:
        LOGGER.exception("Unable to write raw dataset to %s", output_path)
        raise
    print(f"Saved {len(all_records)} raw records to {output_path}")
    return output_path


if __name__ == "__main__":
    download_and_save_raw_data()
