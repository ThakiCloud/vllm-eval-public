# Copyright 2024 PRIME team and/or its affiliates
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Borrowed from: https://huggingface.co/spaces/codeparrot/apps_metric/blob/main/utils.py

import multiprocessing
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import Dict, Optional
from datasets import load_dataset
from tools.code_verifier import run_test
import traceback
import os, sys, re, argparse
import concurrent.futures
import copy
import json, math
import warnings
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
from typing import Dict, Tuple

import numpy as np
from tqdm import tqdm
import re
import zlib
import pickle
import base64
import glob

os.environ["TOKENIZERS_PARALLELISM"] = "false"

def has_code(response):
    pattern = r"```python(?:[a-zA-Z0-9]*)\n(.*?)```"
    # Use re.DOTALL to match multiline content inside backticks
    matches = re.findall(pattern, response, re.DOTALL)
    return matches

def check_correctness(problem_to_check: Optional[dict], timeout, debug=False):
    """Check correctness of code generation."""
    try:
        # 간단하게 직접 실행 (multiprocessing 문제 회피)
        res, metadata = run_test(problem_to_check, debug=debug, timeout=timeout)
        judge_value = bool(res and np.all(np.array(res) > 0))
        
        if judge_value == False:
            print(f"Test failed: {res}, {metadata}")
            
        return judge_value
    except Exception as e:
        print(f"Error in check_correctness: {e}")
        traceback.print_exc(10)
        return False

def get_starter_code(header_str):
    if "def " in header_str:
        starter_code = header_str.split("def")[1].split("(")[0].strip()
    else:
        starter_code = header_str

    return starter_code

def combine(question_path, generation_paths, identifier='task_id'):
    # JSONL 파일 읽기 (각 줄이 하나의 JSON 객체)
    questions = []
    with open(question_path, "r") as f:
        for line in f:
            line = line.strip()
            if line:  # 빈 줄 무시
                questions.append(json.loads(line))

    total_questions = len(questions)
    print(f"Loaded {total_questions} questions from {question_path}")

    combined_results = {}
    for problem in questions:
        testcases = []
        for k, v in problem.items():
            if 'private_test_cases' == k:
                testcases.extend(json.loads(
                    pickle.loads(
                        zlib.decompress(
                            base64.b64decode(v.encode("utf-8"))
                        )
                    )
                ))
        starter_code = get_starter_code(problem['starter_code'])
        combined_results[problem['question_id']] = {
            'input_output': testcases,
            'starter_code': starter_code,
            'question_id': problem['question_id'],
        }  
    
    generations = []
    
    for generation_path in generation_paths:
        print(f"Loading generation file: {generation_path}")
        # JSONL 파일 읽기 (각 줄이 하나의 JSON 객체)
        tmp = []
        with open(generation_path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    try:
                        tmp.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error at line {line_num}: {e}")
                        print(f"Line content: {repr(line)}")
        print(f"Loaded {len(tmp)} generations from {generation_path}")
        generations.extend(tmp)

    count = 0
    all_collected = []
    for line in generations:
        # 문자열인 경우 JSON으로 파싱
        if isinstance(line, str):
            try:
                generation = json.loads(line)
            except json.JSONDecodeError:
                print(f"Skipping invalid JSON line: {repr(line)}")
                continue
        else:
            generation = line
            
        generation_out = generation['generation'] if 'generation' in generation.keys() else generation['output']
        
        # task_id로 매칭 시도
        gen_id = generation[identifier]
        
        # combined_results에서 question_id로 저장되어 있으므로, 
        # generation의 task_id와 question의 question_id를 매칭
        matched = False
        for q_id, q_data in combined_results.items():
            if q_id == gen_id:  # question_id와 task_id가 같은 경우
                combined_results[q_id]['generation'] = generation_out
                all_collected.append(copy.deepcopy(combined_results[q_id]))
                count += 1
                matched = True
                break
        
        if not matched:
            print(f"Warning: No matching question found for generation ID: {gen_id}")
            print(f"Available question IDs: {list(combined_results.keys())}")
    
    filtered = []
    for k, v in combined_results.items():
        if 'generation' not in combined_results[k]:
            filtered.append(k)
    for k in filtered:
        del combined_results[k]

    print(f"Matched {count} question-generation pairs.")
    return all_collected, len(all_collected)

def update_results(result, timeout):
    response_entry = {
        "qid": result['question_id'],
    } 
    problem_to_check = copy.deepcopy(result)
    curr_res = check_correctness(problem_to_check, timeout=timeout)
            
    if curr_res:
        response_entry["correctness"] = True
    else:
        response_entry["correctness"] = False
    
    return response_entry

def compute_accuracy(question_path, generation_path, timeout=5):

    results, total_questions = combine(question_path, generation_path)
    print(f"Loaded {total_questions} questions for evaluation.")
   
    correct = 0
    total = 0
    records = []
    
    # 단순하게 순차 실행 (multiprocessing 문제 회피)
    for idx, result in enumerate(tqdm(results, desc="Processing Generations")):
        response_entry = update_results(result, timeout)
        correct += response_entry['correctness']
        records.append(response_entry)
        total += 1


    months = json.load(open("data/livecodebench_split.json", "r"))

    mp = {}
    for item in records:
        if item['correctness'] == False: continue
        if item['qid'] not in mp: mp[item['qid']] = 1
        else: mp[item['qid']] += 1

    # 전체 결과 요약
    print(f"\n=== LiveCodeBench Evaluation Results ===")
    print(f"Total Questions: {total}")
    print(f"Correct Answers: {correct}")
    if total > 0:
        print(f"Overall Accuracy: {100.0 * correct / total:.2f}%")
    else:
        print("Overall Accuracy: No questions to evaluate")
    
    # 월별 분석 (데이터가 있는 경우에만)
    results_json = {
        "overall": {
            "total_questions": total,
            "correct_answers": correct,
            "accuracy": 100.0 * correct / total if total > 0 else 0.0
        },
        "monthly_results": {},
        "period_results": {},
        "version_results": {}
    }
    
    try:
        months = json.load(open("data/livecodebench_split.json", "r"))
        
        # 실제 문제 수에 따른 동적 계산
        total_expected_problems = sum(len(p) for p in months.values())
        N = max(1, len(records) // total_expected_problems) if total_expected_problems > 0 else 1
        
        print(f"\nLiveCodeBench Evaluation (Avg@{N})")
        print('='*65)
        print("Months\t\tCorrects\tTotal\t\tAccuracy")
        
        A = 0
        B = 0
        for m, p in sorted(months.items()):
            corrects = 0
            for i in p: 
                if i not in mp: continue
                corrects += mp[i]
            
            month_total = len(p) * N
            accuracy = 100.0 * corrects / month_total if month_total > 0 else 0.0
            print(f"{m}\t\t{corrects}\t\t{month_total}\t\t{accuracy:.2f}")
            
            # JSON 결과에 추가
            results_json["monthly_results"][m] = {
                "corrects": corrects,
                "total": month_total,
                "accuracy": accuracy
            }
            
            A += corrects
            B += month_total
            
            if m == '2024-05' or m == '2025-01':
                period_accuracy = 100.0 * A / B if B > 0 else 0.0
                if m == '2024-05':
                    period_name = '05/23-05/24'
                    print(f'{period_name}\t{A}\t\t{B}\t\t{period_accuracy:.2f}')
                    results_json["period_results"][period_name] = {
                        "corrects": A,
                        "total": B,
                        "accuracy": period_accuracy
                    }
                else:
                    period_name = '06/24-01/25'
                    print(f'{period_name}\t{A}\t\t{B}\t\t{period_accuracy:.2f}')
                    results_json["period_results"][period_name] = {
                        "corrects": A,
                        "total": B,
                        "accuracy": period_accuracy
                    }
                A = 0
                B = 0
        
        # v5, v6 버전별 결과 계산
        v5_corrects = 0
        v5_total = 0
        v6_corrects = 0
        v6_total = 0
        
        # v5: 2023-05 ~ 2024-05
        for m in ['2023-05', '2023-06', '2023-07', '2023-08', '2023-09', '2023-10', 
                  '2023-11', '2023-12', '2024-01', '2024-02', '2024-03', '2024-04', '2024-05']:
            if m in results_json["monthly_results"]:
                v5_corrects += results_json["monthly_results"][m]["corrects"]
                v5_total += results_json["monthly_results"][m]["total"]
        
        # v6: 2024-06 ~ 2025-04
        for m in ['2024-06', '2024-07', '2024-08', '2024-09', '2024-10', '2024-11', 
                  '2024-12', '2025-01', '2025-02', '2025-03', '2025-04']:
            if m in results_json["monthly_results"]:
                v6_corrects += results_json["monthly_results"][m]["corrects"]
                v6_total += results_json["monthly_results"][m]["total"]
        
        v5_accuracy = 100.0 * v5_corrects / v5_total if v5_total > 0 else 0.0
        v6_accuracy = 100.0 * v6_corrects / v6_total if v6_total > 0 else 0.0
        
        results_json["version_results"]["v5"] = {
            "corrects": v5_corrects,
            "total": v5_total,
            "accuracy": v5_accuracy
        }
        results_json["version_results"]["v6"] = {
            "corrects": v6_corrects,
            "total": v6_total,
            "accuracy": v6_accuracy
        }
        
    except FileNotFoundError:
        print("Note: livecodebench_split.json not found. Skipping monthly analysis.")
    
    return results_json

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Unified verifier for different datasets/tasks."
    )
    parser.add_argument(
        "-q", "--question-path",
        type=str,
        default="./data/livecodebench_problems.json",
    )
    parser.add_argument(
        "-g", "--generation-path",
        type=str,
        required=True
    )

    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=10,
    )
    parser.add_argument(
        "-s", "--seed",
        type=int,
        default=-1,
    )

    args = parser.parse_args()

    # 직접 파일 경로가 주어진 경우와 디렉토리 경로가 주어진 경우를 구분
    if os.path.isfile(args.generation_path):
        # 직접 파일 경로가 주어진 경우
        json_files = [args.generation_path]
    else:
        # 디렉토리 경로가 주어진 경우
        if args.seed != -1:
            json_files = glob.glob(f"./{args.generation_path}/*seed{args.seed}.jsonl")
        else:
            json_files = glob.glob(f"./{args.generation_path}/*.jsonl")
    
    results_json = compute_accuracy(args.question_path, json_files, timeout=args.timeout)
    
    # JSON 결과를 파일로 저장
    output_filename = "livecodebench_evaluation_results.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(results_json, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Results saved to: {output_filename}")

