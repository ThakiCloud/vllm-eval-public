#!/usr/bin/env python3

import json
import os
import logging
from datasets import load_dataset
from pathlib import Path

# Set environment flags for remote code loading
os.environ["DATASETS_TRUST_REMOTE_CODE"] = "1"
os.environ["HF_DATASETS_TRUST_REMOTE_CODE"] = "1"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# Constants
DATA_DIR = Path("data")
OUTPUT_FILENAME = "livecodebench_problems.jsonl"
OUTPUT_PATH = DATA_DIR / OUTPUT_FILENAME
DATASET_ID = "livecodebench/code_generation_lite"
DATASET_TAG = "release_v6"


def ensure_data_dir():
    """Create the data directory if it doesn't exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logging.debug(f"Ensured data directory exists at: {DATA_DIR}")


def save_jsonl(data, filepath):
    """Save a list of JSON objects to a JSONL file."""
    with open(filepath, "w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    logging.info(f"Saved {len(data)} records to {filepath}")


def format_problem(item):
    """Format a dataset item into a standardized problem dictionary."""
    return {
        "question_id": item.get("question_id"),
        "question_title": item.get("question_title"),
        "question_content": item.get("question_content"),
        "starter_code": item.get("starter_code", ""),
        "private_test_cases": item.get("private_test_cases", []),
        "public_test_cases": item.get("public_test_cases", []),
        "difficulty": item.get("difficulty", ""),
        "platform": item.get("platform", ""),
        "contest_date": item.get("contest_date", ""),
        "release_date": item.get("release_date", ""),
    }


def download_livecodebench():
    """
    Download the LiveCodeBench dataset from HuggingFace,
    format it, and save it as a JSONL file.
    """
    if OUTPUT_PATH.exists():
        logging.info(f"File already exists at {OUTPUT_PATH}. Skipping download.")
        return str(OUTPUT_PATH)

    logging.info("Downloading LiveCodeBench dataset...")
    try:
        dataset = load_dataset(DATASET_ID, version_tag=DATASET_TAG, trust_remote_code=True)
        test_data = dataset.get("test")
        if not test_data:
            raise ValueError("Test split not found in dataset")

        formatted_problems = [format_problem(item) for item in test_data]

        ensure_data_dir()
        save_jsonl(formatted_problems, OUTPUT_PATH)

        return str(OUTPUT_PATH)

    except Exception as e:
        logging.error(f"Failed to download or save dataset: {e}")
        return None


if __name__ == "__main__":
    download_livecodebench()