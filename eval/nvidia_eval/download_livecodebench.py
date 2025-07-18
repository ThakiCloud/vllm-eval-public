#!/usr/bin/env python3

import json
import os
from datasets import load_dataset

os.environ['DATASETS_TRUST_REMOTE_CODE'] = '1'
os.environ['HF_DATASETS_TRUST_REMOTE_CODE'] = '1'

def download_livecodebench():
    """Download LiveCodeBench dataset and save as JSONL file"""

    output_path = "data/livecodebench_problems.jsonl"

    # Step 1: Check if file already exists
    if os.path.exists(output_path):
        print(f"File '{output_path}' already exists. Skipping download.")
        return output_path

    print("Downloading LiveCodeBench dataset...")
    try:
        # Load the dataset
        dataset = load_dataset("livecodebench/code_generation_lite", version_tag="release_v6", trust_remote_code=True)

        # Get the test split
        test_data = dataset['test']

        # Create data directory if it doesn't exist
        os.makedirs('data', exist_ok=True)

        # Save as JSONL file
        with open(output_path, 'w') as f:
            for item in test_data:
                problem = {
                    'question_id': item['question_id'],
                    'question_title': item['question_title'],
                    'question_content': item['question_content'],
                    'starter_code': item.get('starter_code', ''),
                    'private_test_cases': item['private_test_cases'],
                    'public_test_cases': item.get('public_test_cases', ''),
                    'difficulty': item.get('difficulty', ''),
                    'platform': item.get('platform', ''),
                    'contest_date': item.get('contest_date', ''),
                    'release_date': item.get('release_date', '')
                }
                f.write(json.dumps(problem) + '\n')

        print(f"Successfully downloaded {len(test_data)} problems to {output_path}")
        return output_path

    except Exception as e:
        print(f"Error downloading dataset: {e}")
        return None

if __name__ == "__main__":
    download_livecodebench()
