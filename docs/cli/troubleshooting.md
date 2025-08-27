# Troubleshooting

This guide covers common issues and solutions for the VLLM Evaluation CLI.

## Quick Diagnostics

### System Health Check

Start with the built-in diagnostic tool:

```bash
# Run comprehensive system diagnostics
vllm-eval doctor

# Verbose diagnostic output
vllm-eval doctor --verbose

# Check system status
vllm-eval system status
```

### Configuration Validation

```bash
# Validate current configuration
vllm-eval config validate

# Test endpoint connectivity
vllm-eval config validate --test-endpoints
```

## Common Issues

### Installation Issues

#### Issue: `vllm-eval: command not found`

**Solutions:**

1. **Install in development mode**:
```bash
cd /path/to/vllm-eval-public
pip install -e .
```

2. **Check installation**:
```bash
pip list | grep vllm-eval
which vllm-eval
```

#### Issue: Configuration file not found

**Solutions:**

1. **Run setup wizard**:
```bash
vllm-eval setup
```

2. **Create minimal configuration**:
```bash
mkdir -p ~/.config/vllm-eval
cat > ~/.config/vllm-eval/config.toml << EOF
profile_name = "default"

[model]
name = "my-model"
endpoint = "http://localhost:8000/v1/completions"

[evaluation.evalchemy]
enabled = true
EOF
```

### Connectivity Issues

#### Issue: Connection refused to model endpoint

**Solutions:**

1. **Check if server is running**:
```bash
curl http://localhost:8000/health
```

2. **Start VLLM server**:
```bash
vllm serve my-model --port 8000
```

3. **Update endpoint in config**:
```toml
[model]
endpoint = "http://correct-host:8000/v1/completions"
```

### Performance Issues

#### Issue: Slow evaluation execution

**Solutions:**

1. **Increase batch size**:
```toml
[evaluation.evalchemy]
batch_size = 8
```

2. **Use parallel execution**:
```bash
vllm-eval run all my-model --parallel
```

#### Issue: Out of memory errors

**Solutions:**

1. **Reduce batch size**:
```toml
[evaluation.evalchemy]
batch_size = 1
```

2. **Limit sequence length**:
```toml
[model]
max_tokens = 1024
```

## Getting Help

### Built-in Help

```bash
# General help
vllm-eval --help

# Command-specific help
vllm-eval run --help
vllm-eval run evalchemy --help
```

### Debug Mode

```bash
# Enable debug output
vllm-eval --verbose run evalchemy my-model

# Full debug mode
vllm-eval --debug run evalchemy my-model
```

### Log Files

- **System logs**: `~/.config/vllm-eval/logs/`
- **Evaluation logs**: `./logs/` (or configured logs directory)

```bash
# View recent errors
tail -f ~/.config/vllm-eval/logs/evaluation.log
```

## Error Codes

| Code | Description | Solution |
|------|-------------|----------|
| `CONFIG_001` | Configuration file not found | Run `vllm-eval setup` |
| `CONN_001` | Connection refused | Start model server |
| `AUTH_001` | Authentication failed | Set correct API key |
| `GPU_001` | CUDA out of memory | Reduce batch size |

For more information, see:
- [Commands Reference](commands.md)
- [Configuration Guide](configuration.md)
