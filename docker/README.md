### VLLM Eval Docker Images

Build instructions for the Docker images in this folder. Use the naming convention:

- For local macOS builds: tag ends with `-mac`
- For Linux/amd64 builds: tag ends with `-linux`

Prerequisites:
- Docker 24+ and Buildx enabled (for cross-platform builds)

---

## evalchemy

- **macOS (local arch)**
```bash
docker build -f docker/evalchemy.Dockerfile -t ghcr.io/thakicloud/evalchemy-mac:latest .
```
```bash
docker push ghcr.io/thakicloud/evalchemy-mac:latest
```

- **Linux/amd64**
```bash
docker buildx build --platform linux/amd64 \
  -f docker/evalchemy.Dockerfile \
  -t ghcr.io/thakicloud/evalchemy-linux:latest .
```
```bash
docker push ghcr.io/thakicloud/evalchemy-linux:latest
```

---

## standard-evalchemy

- **macOS (local arch)**
```bash
docker build -f docker/standard-evalchemy.Dockerfile \
  -t ghcr.io/thakicloud/standard-evalchemy-mac:latest .
```
```bash
docker push ghcr.io/thakicloud/standard-evalchemy-mac:latest
```

- **Linux/amd64**
```bash
docker buildx build --platform linux/amd64 \
  -f docker/standard-evalchemy.Dockerfile \
  -t ghcr.io/thakicloud/standard-evalchemy-linux:latest .
```
```bash
docker push ghcr.io/thakicloud/standard-evalchemy-linux:latest
```

---

## nvidia-eval

- **macOS (local arch)**
```bash
docker build -f docker/nvidia-eval.Dockerfile -t ghcr.io/thakicloud/nvidia-eval-mac:latest .
```
```bash
docker push ghcr.io/thakicloud/nvidia-eval-mac:latest
```

- **Linux/amd64**
```bash
docker buildx build --platform linux/amd64 \
  -f docker/nvidia-eval.Dockerfile \
  -t ghcr.io/thakicloud/nvidia-eval-linux:latest .
```
```bash
docker push ghcr.io/thakicloud/nvidia-eval-linux:latest
```

---

## vllm-benchmark

- **macOS (local arch)**
```bash
docker build -f docker/vllm-benchmark.Dockerfile -t ghcr.io/thakicloud/vllm-benchmark-mac:latest .
```
```bash
docker push ghcr.io/thakicloud/vllm-benchmark-mac:latest
```

- **Linux/amd64**
```bash
docker buildx build --platform linux/amd64 \
  -f docker/vllm-benchmark.Dockerfile \
  -t ghcr.io/thakicloud/vllm-benchmark-linux:latest .
```
```bash
docker push ghcr.io/thakicloud/vllm-benchmark-linux:latest
```

---

## vllm-benchmark-linux

- **macOS (local arch)**
```bash
docker build -f docker/vllm-benchmark-linux.Dockerfile -t ghcr.io/thakicloud/vllm-benchmark-linux-mac:latest .
```
```bash
docker push ghcr.io/thakicloud/vllm-benchmark-linux-mac:latest
```

- **Linux/amd64**
```bash
docker buildx build --platform linux/amd64 \
  -f docker/vllm-benchmark-linux.Dockerfile \
  -t ghcr.io/thakicloud/vllm-benchmark-linux:latest .
```
```bash
docker push ghcr.io/thakicloud/vllm-benchmark-linux:latest
```

---

## deepeval

- **macOS (local arch)**
```bash
docker build -f docker/deepeval.Dockerfile -t ghcr.io/thakicloud/deepeval-mac:latest .
```
```bash
docker push ghcr.io/thakicloud/deepeval-mac:latest
```

- **Linux/amd64**
```bash
docker buildx build --platform linux/amd64 \
  -f docker/deepeval.Dockerfile \
  -t ghcr.io/thakicloud/deepeval-linux:latest .
```
```bash
docker push ghcr.io/thakicloud/deepeval-linux:latest
```

---

### Notes
- All images use non-root user `evaluser` where applicable.
- Standard output directories: `/app/results` and `/app/parsed` (volumes typically mounted to these paths).
- Healthchecks are included in most images; see Dockerfiles for details.

---

## Troubleshooting

- **Exec format error**: Build for the correct platform using Buildx and `--platform linux/amd64` for Linux images.
- **Windows line endings**: Ensure scripts use LF; or run inside the image/container: `sed -i 's/\r$//' /app/*.sh`.
- **Permission denied**: Ensure scripts are executable; run container with root to diagnose and `chmod +x /app/*.sh` if needed.
- **Network issues**: Prefer `--network host` for local testing or verify connectivity with tools inside the container.

For a detailed guide with commands and examples, see `docker/TROUBLESHOOTING.md`.

