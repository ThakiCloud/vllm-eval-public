# Evalchemy API

## Standard Evalchemy Bencharking

Evalchemy supports two evaluation methods, and you can choose either of the following:

1. Using Docker – build a Docker image and run the benchmark inside a container.
2. Using a script – directly run the provided benchmark script without Docker.

### Docker Run

Build Docker Image:

```bash
docker build -f docker/standard_evalchemy.Dockerfile \
    -t standard-evalchemy:latest .
```

#### Run a container from built docker image:

```bash
docker run --rm \
    --network host \
    -e VLLM_MODEL_ENDPOINT="http://localhost:8080/v1/completions" \
    -e MODEL_NAME="Qwen/Qwen2-0.5B" \
    -e SERVED_MODEL_NAME="qwen2-0.5b" \
    -e TOKENIZER="Qwen/Qwen2-0.5B" \
    -e TOKENIZER_BACKEND="huggingface" \
    -e MODEL_CONFIG='{"model_type": "curator", "api_config": {"max_retries": 3, "retry_delay": 5.0}}' \
    -e EVALUATION_CONFIG='{"limit": 100, "output_format": "json", "log_samples": true, "max_tokens": 2000}' \
    standard-evalchemy:latest
```

!!! note

    `--network host` - solution to MODEL ID or MODEL NAME issue

#### `parsed` and `results` folders will be created:

```bash
├── eval/
│   └── standard_evalchemy/
│       ├── parsed/
│       └── results/
```

### Bash Run

#### Libraries needs to be installed in `vllm-eval-public` folder

Install `requirements-dev.txt`:

```bash
pip install -r requirements-dev.txt
```

Install `evalchemy` library:

```bash
git clone https://github.com/ThakiCloud/evalchemy.git
cd evalchemy
pip install . -e
cd ..
```

#### `run_evalchemy.sh` can be run now:

```bash
./run_evalchemy.sh \
  --endpoint http://localhost:8000/v1/completions \
  --model-name "facebook/opt-125m" \
  --tokenizer "facebook/opt-125m" \
  --tokenizer-backend "huggingface" \
  --batch-size 1 \
  --run-id test_01
```

#### `parsed` and `results` folders will be created:

```bash
├── eval/
│   └── standard_evalchemy/
│       ├── parsed/
│       └── results/
```
