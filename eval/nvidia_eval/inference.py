import requests
from tqdm import tqdm
import copy
import os
import json
import argparse
import time
from datasets import load_dataset

os.environ["TOKENIZERS_PARALLELISM"] = "false"

def get_args(add_evaluation=False):
    parser = argparse.ArgumentParser(description="llm_config")

    ## model & tokenizer
    parser.add_argument('--output-folder', type=str, default=None)
    parser.add_argument('--load', type=str, default=None,
                       help='Directory containing a model checkpoint.')
    parser.add_argument('--tokenizer-model', type=str, default=None)
    ## dataset path
    parser.add_argument('--datapath', type=str, default='')

    ## others
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--device-id', type=str, default=None)
    
    if add_evaluation:
        parser = _add_evaluation_argument(parser)

    args = parser.parse_args()

    return args


def _add_evaluation_argument(parser):
    group = parser.add_argument_group(title='evaluation')

    ## generation
    group.add_argument('--model-type', type=str, required=True)
    group.add_argument('--temperature', type=float, default=0)
    group.add_argument('--topk', type=int, default=1)
    group.add_argument('--topp', type=float, default=1)
    group.add_argument('--max-output-len', type=int, default=2048) # change it to smaller value for smaller model or local model testing due the limit of the output length
    group.add_argument('--start-idx', type=int, default=-1)
    group.add_argument('--end-idx', type=int, default=-1)
    group.add_argument('--tensor-parallel-size', type=int, default=1)

    ## inference api
    group.add_argument('--api-base', type=str, default='http://localhost:8000/v1')
    group.add_argument('--max-workers', type=int, default=16)
    group.add_argument('--eval-dataset-list', nargs='*', type=str)
    group.add_argument('--stop-token-ids', nargs='*', type=int)
    parser.add_argument('--batch-size', type=int, default=16)
    parser.add_argument('--fp16', default=False, action='store_true')
    parser.add_argument('--bf16', default=False, action='store_true')
    return parser
    

def get_starter_code(header_str):
    if "def " in header_str:
        starter_code = header_str.split("def")[1].split("(")[0].strip()
    else:
        starter_code = header_str

    return starter_code



def preprocess_livecodebench(data_file, model_type):
    data_list = []
    with open(data_file, "r") as f:
        for line in f:
            if line.strip():  # 빈 줄 방지
                data_list.append(json.loads(line))

    instruction = ""
    if model_type == "qwen":
        instruction = "<|im_start|>system\nYou are a helpful and harmless assistant. You should think step-by-step.<|im_end|>\n"
    
    prompt_list = []
    qid_list = []
    for item in data_list:
        question = item['question_content'].strip()

        code_instruction_nostartercode = """Write Python code to solve the problem. Please place the solution code in the following format:\n```python\n# Your solution code here\n```"""
        code_instruction_hasstartercode = """Please place the solution code in the following format:\n```python\n# Your solution code here\n```"""

        if item['starter_code'] != "":
            question += "\n\n" + "Solve the problem starting with the provided function header.\n\nFunction header:\n" + "```\n" + item['starter_code'] + "\n```"
            question += "\n\n" + code_instruction_hasstartercode
        else:
            question += "\n\n" + code_instruction_nostartercode

        if model_type == "qwen":
            final_prompt = instruction + "<|im_start|>user\n" + question + "<|im_end|>\n<|im_start|>assistant\n<think>\n"
        else:
            final_prompt = " " + question + " " + "<think>\n"
        
        prompt_list.append(final_prompt)
        qid_list.append(item['question_id'])
    
    return prompt_list, qid_list

def preprocess_aime(data_file, model_type):
    
    prompt_list = []
    qid_list = []
    with open(data_file, "r") as f:
        for i, line in enumerate(f):
            item = json.loads(line)
            final_question = item['problem'].strip()
            if model_type == "qwen":
                final_prompt = """<|im_start|>system\nYou are a helpful and harmless assistant. You should think step-by-step.<|im_end|>\n<|im_start|>user\n{question}\n\nPlease place your final answer inside \\boxed{{}}.<|im_end|>\n<|im_start|>assistant\n<think>\n""".format(question=final_question)
            else:
                final_prompt = """{question}\nPlease reason step by step, and put your final answer within \\boxed{{}}.

<think>
""".format(question=final_question)
            prompt_list.append(final_prompt)
            qid_list.append(i)
    return prompt_list, qid_list
    
def call_api_completion(prompt, args):
    """API 서버에 완성 요청을 보냅니다."""
    api_url = f"{args.api_base}/completions"
    
    data = {
        "model": args.load,  # 서버에 로드된 모델명 사용
        "prompt": prompt,
        "max_tokens": args.max_output_len,
        "temperature": args.temperature,
        "stream": False
    }
    
    # top_p는 1.0이 아닐 때만 추가
    if args.topp < 1.0:
        data["top_p"] = args.topp
    
    try:
        print(f"API 요청 URL: {api_url}")
        print(f"API 요청 데이터: {data}")
        print(f"프롬프트 길이: {len(prompt)} 문자")
        
        response = requests.post(api_url, json=data, timeout=600)
        
        print(f"HTTP 상태 코드: {response.status_code}")
        
        if response.status_code != 200:
            print(f"에러 응답 내용: {response.text}")
            return ""
            
        result = response.json()
        print("API 호출 성공!")
        return result['choices'][0]['text']
    except requests.exceptions.RequestException as e:
        print(f"API 호출 오류: {e}")
        print(f"요청 URL: {api_url}")
        print(f"요청 데이터: {data}")
        return ""
    except KeyError as e:
        print(f"응답 파싱 오류: {e}")
        print(f"응답 내용: {response.text}")
        return ""


def get_prompt_list(args):
    ## get input data
    input_datapath = args.datapath
    if "aime" in args.datapath:
        prompt_list, qid_list = preprocess_aime(input_datapath, args.model_type)
    elif "livecodebench" in args.datapath:
        print("input_datapath:", input_datapath)
        prompt_list, qid_list = preprocess_livecodebench(input_datapath, args.model_type)
    else:
        raise ValueError("Invalid dataset name")
        
    print("number of total prompt_list:", len(prompt_list))
    if args.start_idx != -1 and args.end_idx != -1:
        print("getting data from %d to %d" % (args.start_idx, args.end_idx))
        prompt_list = prompt_list[args.start_idx:args.end_idx]
        if qid_list:
            qid_list = qid_list[args.start_idx:args.end_idx]

    print("number of test samples in the dataset:", len(prompt_list))
    return prompt_list, qid_list


def main():
    args = get_args(add_evaluation=True)
    if args.device_id:
        os.environ["CUDA_VISIBLE_DEVICES"] = args.device_id

    for key, value in vars(args).items():
        print(f"{key}: {value}")

    print(f"API 서버 URL: {args.api_base}")

    ## load test data
    prompt_list, qid_list = get_prompt_list(args)

    ## run inference via API
    print("args.model_type:", args.model_type)
    print("args.max_output_len:", args.max_output_len)
    print("args.seed:", args.seed)
    print("args.topp:", args.topp)
    print("args.temperature:", args.temperature)

    output_list = []
    # API 호출은 batch 처리를 하지 않고 하나씩 처리 (더 안정적)
    for i in tqdm(range(len(prompt_list))):
        prompt = prompt_list[i]
        qid = qid_list[i] if qid_list else i
        
        generated_text = call_api_completion(prompt, args)
        
        if "<|im_end|>" in generated_text:
            idx = generated_text.index("<|im_end|>")
            generated_text = generated_text[:idx]
        if "<|end_of_text|>" in generated_text:
            idx = generated_text.index("<|end_of_text|>")
            generated_text = generated_text[:idx]
        if "<|eot_id|>" in generated_text:
            idx = generated_text.index("<|eot_id|>")
            generated_text = generated_text[:idx]
        
        if qid_list:
            output_dict = {"task_id": qid, "output": generated_text}
            output_list.append(output_dict)
        else:
            output_dict = {"output": generated_text}
            output_list.append(output_dict)
            
        # API 요청 간 잠시 대기 (서버 부하 방지)
        time.sleep(0.1)

    ## write to output_datapath

    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)

    output_name = "%dto%d_seed%d.jsonl" % (args.start_idx, args.end_idx, args.seed) \
                            if args.start_idx != -1 and args.end_idx != -1 else "seed%d.jsonl" % args.seed
    
    output_datapath = os.path.join(args.output_folder, output_name)

    print("writing to %s" % output_datapath)
    with open(output_datapath, "w", encoding='utf-8') as f:
        for output in output_list:
            if type(output) == dict:
                f.write(json.dumps(output) + "\n")
            else:
                f.write(output + "\n")

if __name__ == "__main__":
    main()

