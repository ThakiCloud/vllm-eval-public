# VLLM Eval CLI - Quick Start Guide

This guide helps you resolve common setup issues and get started with the VLLM Evaluation CLI.

## 🚨 Common Issues and Solutions

### Issue 1: Missing Configuration File
**Error**: `Config file not found: /Users/yakhyo/.config/vllm-eval/default.toml`

**Solution**: Run the setup wizard to create configuration
```bash
vllm-eval setup
```

### Issue 2: Missing Dependencies
**Error**: `Deepeval package not installed. Run: pip install deepeval`

**Solution**: Install required dependencies
```bash
# For specific frameworks
pip install deepeval
pip install "lm-eval[all]"
pip install vllm

# Or install all dependencies at once
pip install "vllm-eval[full]"
```

### Issue 3: Missing Evalchemy Configuration
**Error**: `Evalchemy config not found: configs/eval_config.json`

**Solution**: Create the missing configuration file
```bash
mkdir -p configs
```

### Issue 4: Missing Endpoint Configuration
**Error**: `Endpoint parameter is required for Standard Evalchemy`

**Solution**: Provide endpoint when running or set in config
```bash
vllm-eval run all my-model --endpoint http://localhost:8000
```

### Issue 5: GPU Requirements
**Error**: `GPU is required for NVIDIA Eval but not available`

**Solution**: Either provide GPU access or disable NVIDIA eval
```bash
# Disable NVIDIA eval if no GPU
vllm-eval run all my-model --frameworks evalchemy,deepeval,vllm-benchmark
```

## 🚀 Quick Setup Steps

### 1. Install Dependencies
```bash
# Basic installation
pip install -e .

# With all evaluation frameworks
pip install -e ".[full]"
```

### 2. Run Setup Wizard
```bash
vllm-eval setup
```

### 3. Create Required Configurations
```bash
# Create configs directory
mkdir -p configs

# Create basic evalchemy config
cat > configs/eval_config.json << 'EOF'
{
  "benchmarks": [
    {
      "name": "basic_eval",
      "tasks": ["hellaswag", "arc_easy"],
      "few_shot": 5,
      "limit": 100
    }
  ],
  "model_configs": {
    "default": {
      "batch_size": 8,
      "max_length": 2048
    }
  },
  "generation_kwargs": {
    "temperature": 0.0,
    "top_p": 1.0,
    "max_tokens": 512
  }
}
EOF
```

### 4. Start Your Model Server
```bash
# Example with VLLM
python -m vllm.entrypoints.openai.api_server \
  --model your-model-name \
  --host 0.0.0.0 \
  --port 8000
```

### 5. Validate Setup
```bash
vllm-eval system validate
```

### 6. Run Quick Test
```bash
vllm-eval run quick my-model --endpoint http://localhost:8000 --dry-run
```

## 🎯 Minimal Working Example

For a quick test with minimal setup:

### 1. Install Basic Dependencies
```bash
pip install -e .
pip install requests
```

### 2. Create Minimal Config
```bash
vllm-eval setup --no-interactive
```

### 3. Test with Single Framework
```bash
vllm-eval run quick my-model \
  --framework vllm-benchmark \
  --endpoint http://localhost:8000 \
  --dry-run
```

## 🔧 Framework-Specific Setup

### Evalchemy
```bash
pip install "lm-eval[all]"
# Create configs/eval_config.json (see above)
```

### Deepeval
```bash
pip install deepeval
# No additional config needed
```

### NVIDIA Eval
```bash
# Requires GPU access
# Install torch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### VLLM Benchmark
```bash
pip install vllm aiohttp tenacity
# Works without additional config
```

## 📊 Recommended Development Workflow

### 1. Initial Setup
```bash
# Clone and install
git clone <repo>
cd vllm-eval-public
pip install -e ".[dev]"

# Run setup
vllm-eval setup

# Validate
vllm-eval system validate
```

### 2. Start Model Server
```bash
# Terminal 1: Start your model server
python -m vllm.entrypoints.openai.api_server \
  --model microsoft/DialoGPT-medium \
  --host 0.0.0.0 \
  --port 8000
```

### 3. Test Evaluation
```bash
# Terminal 2: Test evaluation
vllm-eval run quick test-model \
  --endpoint http://localhost:8000 \
  --framework vllm-benchmark \
  --dry-run

# If successful, run actual evaluation
vllm-eval run quick test-model \
  --endpoint http://localhost:8000 \
  --framework vllm-benchmark
```

### 4. Comprehensive Evaluation
```bash
# Run all available frameworks
vllm-eval run all test-model \
  --endpoint http://localhost:8000 \
  --frameworks vllm-benchmark,deepeval \
  --continue-on-error
```

## 🐛 Troubleshooting

### Check System Status
```bash
vllm-eval system status --verbose
```

### Run Diagnostics
```bash
vllm-eval doctor
```

### View Detailed Logs
```bash
vllm-eval run quick my-model --verbose --dry-run
```

### Clean and Reset
```bash
# Clean temporary files
vllm-eval system clean

# Reset configuration
rm -rf ~/.config/vllm-eval/
vllm-eval setup
```

This should resolve most common setup issues. Run the commands step by step and use `--dry-run` to test before actual execution.