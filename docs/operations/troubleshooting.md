# Operations Troubleshooting

Comprehensive troubleshooting guide for operating the VLLM Evaluation System in production environments. Covers both CLI-based local operations and Kubernetes-native deployments with systematic diagnostic approaches.

!!! info "Operational Scope"
    
    - 🔧 **CLI Operations**: Local and remote CLI execution issues
    - ☸️ **Kubernetes Operations**: Production cluster troubleshooting
    - 📊 **Performance Issues**: System performance and optimization
    - 🛑 **Integration Problems**: Cross-system connectivity and data flow

## 🚑 Emergency Procedures

### Critical System Failure

```bash
# 1. Immediate Assessment
vllm-eval doctor --verbose
kubectl get pods -A --field-selector=status.phase!=Running

# 2. Stop Problematic Processes
vllm-eval system clean --force
kubectl delete jobs --all -n vllm-eval

# 3. System Recovery
make system-reset
vllm-eval setup --force
```

### Service Degradation

```bash
# Check system health
vllm-eval system status
kubectl top nodes
kubectl top pods -n vllm-eval

# Scale down if needed
kubectl scale deployment --replicas=0 -n vllm-eval --all
```

---

## 🔍 Diagnostic Methodology

### Systematic Troubleshooting Approach

1. **Identify Scope**: CLI, Kubernetes, or integrated system issue
2. **Gather Information**: Logs, metrics, system state
3. **Isolate Problem**: Narrow down to specific component
4. **Test Hypothesis**: Validate root cause theory
5. **Implement Fix**: Apply solution with verification
6. **Document Resolution**: Record solution for future reference

### Diagnostic Commands

#### CLI Diagnostics

```bash
# System health check
vllm-eval doctor --verbose

# Configuration validation
vllm-eval config validate --test-endpoints

# System status
vllm-eval system status --verbose

# Recent logs
vllm-eval system logs --tail 100

# Performance metrics
vllm-eval system metrics --last 24h
```

#### Kubernetes Diagnostics

```bash
# Cluster overview
kubectl cluster-info
kubectl get nodes -o wide
kubectl get pods -A

# Resource usage
kubectl top nodes
kubectl top pods -A

# Event monitoring
kubectl get events --sort-by='.lastTimestamp' -A

# Workflow status
argo list -n argo
argo get <workflow-name> -n argo
```

---

## 💻 CLI Operations Issues

### Installation and Setup Problems

#### Issue: CLI Command Not Found

**Symptoms**:
```bash
$ vllm-eval --help
zsh: command not found: vllm-eval
```

**Diagnosis**:
```bash
# Check installation
pip list | grep vllm-eval
which vllm-eval
echo $PATH
```

**Solutions**:
```bash
# Reinstall CLI
cd /path/to/vllm-eval-public
pip uninstall vllm-eval -y
pip install -e .

# Verify installation
vllm-eval --version
vllm-eval doctor
```

#### Issue: Configuration Errors

**Symptoms**:
- `Configuration file not found`
- `Invalid TOML syntax`
- `Environment variable not resolved`

**Diagnosis**:
```bash
# Check configuration files
ls -la ~/.config/vllm-eval/
vllm-eval config show --format json
vllm-eval config validate --check-syntax
```

**Solutions**:
```bash
# Reset configuration
rm -rf ~/.config/vllm-eval/
vllm-eval setup --force

# Fix TOML syntax
vllm-eval config validate --check-syntax
vllm-eval config edit  # Opens editor for manual fix

# Set environment variables
export VLLM_ENDPOINT="http://localhost:8000/v1"
export MODEL_NAME="my-model"
```

### Execution and Performance Issues

#### Issue: Evaluation Timeouts

**Symptoms**:
- Evaluations hanging indefinitely
- Timeout errors after long waits
- Partial results with incomplete frameworks

**Diagnosis**:
```bash
# Check running processes
ps aux | grep vllm-eval
vllm-eval system status

# Monitor resource usage
top -p $(pgrep -f vllm-eval)

# Check endpoint connectivity
curl -I http://localhost:8000/health
vllm-eval config validate --test-endpoints
```

**Solutions**:
```bash
# Increase timeouts
vllm-eval --profile production run evalchemy my-model --timeout 7200

# Reduce batch size
vllm-eval run evalchemy my-model --batch-size 1

# Use dry run to test configuration
vllm-eval run evalchemy my-model --dry-run

# Kill hanging processes
pkill -f vllm-eval
vllm-eval system clean
```

#### Issue: Memory and Resource Issues

**Symptoms**:
- Out of memory errors
- System slowdown during evaluation
- Disk space warnings

**Diagnosis**:
```bash
# Check system resources
free -h
df -h
top

# Check evaluation logs
vllm-eval system logs --grep "memory\|disk\|resource"

# Monitor during execution
watch -n 5 'free -h && df -h'
```

**Solutions**:
```bash
# Reduce memory usage
vllm-eval run evalchemy my-model --batch-size 1 --limit 100

# Clean up results
vllm-eval system clean
rm -rf ~/.config/vllm-eval/cache/*

# Use streaming output
vllm-eval run evalchemy my-model --stream-results

# Configure resource limits
vllm-eval config edit  # Set memory_limit, disk_limit
```

### Framework-Specific Issues

#### Evalchemy Issues

**Common Problems**:
- Task not found errors
- API compatibility issues
- Slow evaluation speed

**Solutions**:
```bash
# Check available tasks
vllm-eval run evalchemy --help | grep -A 20 "Available tasks"

# Test with minimal tasks
vllm-eval run evalchemy my-model --tasks arc_easy --limit 10

# Update Evalchemy
pip install --upgrade evalchemy

# Check endpoint compatibility
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "test", "prompt": "Hello", "max_tokens": 5}'
```

#### NVIDIA Eval Issues

**Common Problems**:
- GPU not available
- CUDA compatibility issues
- Model loading failures

**Solutions**:
```bash
# Check GPU availability
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"

# Use CPU mode
vllm-eval run nvidia my-model --gpus 0

# Check CUDA version
nvcc --version
python -c "import torch; print(torch.version.cuda)"
```

---

## ☸️ Kubernetes Operations Issues

### Cluster and Node Issues

#### Issue: Node Resource Exhaustion

**Symptoms**:
- Pods stuck in Pending state
- Node pressure warnings
- Failed pod scheduling

**Diagnosis**:
```bash
# Check node status
kubectl describe nodes
kubectl top nodes

# Check resource requests and limits
kubectl describe pods -n vllm-eval

# Check node conditions
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.conditions[?(@.type=="Ready")].status}{"\n"}{end}'
```

**Solutions**:
```bash
# Scale down unnecessary pods
kubectl scale deployment --replicas=0 -n default --all

# Clean up completed jobs
kubectl delete jobs --field-selector status.successful=1 -n vllm-eval

# Add more nodes (cloud environments)
# kubectl scale --replicas=3 nodepool/evaluation-nodes

# Adjust resource requests
kubectl patch deployment evaluation-runner -n vllm-eval -p '{"spec":{"template":{"spec":{"containers":[{"name":"runner","resources":{"requests":{"memory":"1Gi","cpu":"0.5"}}}]}}}}'
```

#### Issue: Persistent Volume Problems

**Symptoms**:
- Pods failing to start due to volume issues
- Data persistence problems
- Storage capacity warnings

**Diagnosis**:
```bash
# Check PV and PVC status
kubectl get pv,pvc -A
kubectl describe pvc -n vllm-eval

# Check storage class
kubectl get storageclass
kubectl describe storageclass standard
```

**Solutions**:
```bash
# Clean up unused PVCs
kubectl delete pvc --all -n vllm-eval --force

# Increase PVC size
kubectl patch pvc data-pvc -n vllm-eval -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'

# Use different storage class
kubectl patch pvc data-pvc -n vllm-eval -p '{"spec":{"storageClassName":"fast-ssd"}}'
```

### Argo Workflows Issues

#### Issue: Workflow Failures

**Symptoms**:
- Workflows stuck in running state
- Step failures with unclear errors
- Resource timeout issues

**Diagnosis**:
```bash
# Check workflow status
argo list -n argo
argo get <workflow-name> -n argo
argo logs <workflow-name> -n argo

# Check workflow events
kubectl describe workflow <workflow-name> -n argo

# Check Argo controller
kubectl logs -n argo deployment/workflow-controller
```

**Solutions**:
```bash
# Restart failed workflow
argo resubmit <workflow-name> -n argo

# Stop running workflow
argo stop <workflow-name> -n argo

# Clean up old workflows
argo delete --older 7d -n argo

# Restart Argo controller
kubectl rollout restart deployment/workflow-controller -n argo
```

#### Issue: Argo Events Not Triggering

**Symptoms**:
- Workflows not starting automatically
- Event source connection issues
- Sensor not responding to events

**Diagnosis**:
```bash
# Check event sources
kubectl get eventsources -n argo-events
kubectl describe eventsource webhook-event-source -n argo-events

# Check sensors
kubectl get sensors -n argo-events
kubectl logs -l app=sensor-controller -n argo-events

# Test webhook manually
curl -X POST http://<webhook-url>/webhook \
  -H "Content-Type: application/json" \
  -d '{"ref": "refs/heads/main", "repository": {"name": "test"}}'
```

**Solutions**:
```bash
# Restart event source
kubectl delete eventsource webhook-event-source -n argo-events
kubectl apply -f k8s/argo-events/event-source.yaml

# Restart sensor
kubectl rollout restart deployment/webhook-sensor -n argo-events

# Check network connectivity
kubectl exec -it <sensor-pod> -n argo-events -- wget -O- http://github.com
```

### Database and Storage Issues

#### Issue: ClickHouse Connection Problems

**Symptoms**:
- Metrics not being stored
- Query timeouts
- Connection refused errors

**Diagnosis**:
```bash
# Check ClickHouse pod status
kubectl get pods -l app=clickhouse -n vllm-eval
kubectl logs -l app=clickhouse -n vllm-eval

# Test connection
kubectl exec -it clickhouse-0 -n vllm-eval -- clickhouse-client --query "SELECT 1"

# Check service
kubectl describe service clickhouse -n vllm-eval
```

**Solutions**:
```bash
# Restart ClickHouse
kubectl rollout restart statefulset/clickhouse -n vllm-eval

# Check disk space
kubectl exec -it clickhouse-0 -n vllm-eval -- df -h

# Optimize tables
kubectl exec -it clickhouse-0 -n vllm-eval -- clickhouse-client --query "OPTIMIZE TABLE evaluation_metrics"

# Scale ClickHouse
kubectl scale statefulset clickhouse --replicas=2 -n vllm-eval
```

---

## 📊 Performance Troubleshooting

### Evaluation Performance Issues

#### Issue: Slow Evaluation Speed

**Root Causes**:
- Low batch sizes
- Network latency
- Endpoint throttling
- Resource contention

**Optimization Strategies**:

```bash
# Increase batch size
vllm-eval run evalchemy my-model --batch-size 8

# Use parallel execution
vllm-eval run all my-model --parallel

# Optimize endpoint
vllm serve my-model --tensor-parallel-size 2 --max-num-seqs 32

# Use local caching
vllm-eval run evalchemy my-model --cache-responses
```

#### Issue: High Resource Usage

**Monitoring Commands**:
```bash
# Monitor CLI resource usage
top -p $(pgrep -f vllm-eval)

# Monitor Kubernetes resources
kubectl top pods -n vllm-eval
kubectl describe nodes

# Monitor network usage
iftop  # or nethogs
```

**Optimization**:
```bash
# Limit concurrent evaluations
vllm-eval config edit  # Set max_concurrent_jobs = 2

# Use resource limits in Kubernetes
kubectl patch deployment evaluation-runner -n vllm-eval -p '{
  "spec": {
    "template": {
      "spec": {
        "containers": [{
          "name": "runner",
          "resources": {
            "limits": {"memory": "4Gi", "cpu": "2"},
            "requests": {"memory": "2Gi", "cpu": "1"}
          }
        }]
      }
    }
  }
}'
```

### System Performance Monitoring

#### Key Metrics to Monitor

**CLI Performance**:
- Evaluation completion time
- Memory usage during execution
- Disk I/O for results storage
- Network latency to endpoints

**Kubernetes Performance**:
- Pod resource utilization
- Node resource allocation
- Network bandwidth usage
- Storage I/O patterns

#### Performance Monitoring Setup

```bash
# Enable performance monitoring
vllm-eval system enable-monitoring

# Install monitoring tools in Kubernetes
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring
helm install grafana grafana/grafana -n monitoring

# Setup custom dashboards
kubectl apply -f k8s/monitoring/dashboards/
```

---

## 🔗 Integration Troubleshooting

### CLI ↔ Kubernetes Integration Issues

#### Issue: Configuration Sync Problems

**Symptoms**:
- CLI and K8s using different configurations
- Results format inconsistencies
- Profile mismatch errors

**Solutions**:
```bash
# Sync CLI config to Kubernetes
vllm-eval config export --format kubernetes > k8s-config.yaml
kubectl apply -f k8s-config.yaml

# Validate configuration compatibility
vllm-eval config validate --target kubernetes

# Use shared configuration storage
kubectl create configmap vllm-eval-config --from-file=~/.config/vllm-eval/
```

#### Issue: Result Format Inconsistencies

**Symptoms**:
- Different result schemas from CLI vs K8s
- Aggregation failures
- Dashboard display issues

**Solutions**:
```bash
# Standardize result format
vllm-eval results standardize --input ./results/ --output ./standardized/

# Validate result schema
vllm-eval results validate --schema ./schemas/result-schema.json

# Convert legacy results
vllm-eval results migrate --from v1.0 --to v2.0
```

### External System Integration

#### Issue: Model Server Connectivity

**Common Problems**:
- Authentication failures
- Network timeouts
- API version mismatches

**Diagnosis and Solutions**:
```bash
# Test basic connectivity
curl -v http://model-server:8000/health

# Test API compatibility
curl -X POST http://model-server:8000/v1/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{"model": "test", "prompt": "Hello", "max_tokens": 5}'

# Check API version
curl http://model-server:8000/v1/models

# Update endpoint configuration
vllm-eval config edit  # Update endpoint URLs
```

---

## 📊 Monitoring and Alerting

### Production Monitoring Setup

#### Key Metrics Dashboard

```yaml
# Grafana dashboard configuration
apiVersion: v1
kind: ConfigMap
metadata:
  name: vllm-eval-dashboard
data:
  dashboard.json: |
    {
      "dashboard": {
        "title": "VLLM Evaluation System",
        "panels": [
          {
            "title": "Evaluation Success Rate",
            "type": "stat",
            "targets": [{
              "expr": "rate(vllm_eval_success_total[5m])"
            }]
          },
          {
            "title": "Average Evaluation Time",
            "type": "graph",
            "targets": [{
              "expr": "avg(vllm_eval_duration_seconds)"
            }]
          }
        ]
      }
    }
```

#### Alerting Rules

```yaml
# Prometheus alerting rules
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: vllm-eval-alerts
spec:
  groups:
  - name: vllm-eval
    rules:
    - alert: EvaluationFailureRate
      expr: rate(vllm_eval_failures_total[5m]) > 0.1
      for: 5m
      annotations:
        summary: High evaluation failure rate
        description: "Evaluation failure rate is {{ $value }} over 5 minutes"
    
    - alert: LongRunningEvaluation
      expr: vllm_eval_duration_seconds > 7200
      for: 0s
      annotations:
        summary: Evaluation taking too long
        description: "Evaluation {{ $labels.job }} has been running for {{ $value }} seconds"
```

### Log Analysis

#### Centralized Logging

```bash
# Setup log aggregation
kubectl apply -f k8s/logging/fluentd.yaml
kubectl apply -f k8s/logging/elasticsearch.yaml
kubectl apply -f k8s/logging/kibana.yaml

# Query logs
curl -X POST "elasticsearch:9200/vllm-eval-logs/_search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"range": {"@timestamp": {"gte": "now-1h"}}},
          {"match": {"level": "ERROR"}}
        ]
      }
    }
  }'
```

#### Log Analysis Patterns

```bash
# Common error patterns
grep -E "ERROR|FAIL|TIMEOUT" /var/log/vllm-eval/*.log

# Performance analysis
grep -E "duration|latency|throughput" /var/log/vllm-eval/*.log | awk '{print $NF}' | sort -n

# Resource usage patterns
grep -E "memory|cpu|disk" /var/log/vllm-eval/*.log
```

---

## 🔄 Recovery Procedures

### System Recovery Playbook

#### Level 1: Service Recovery

```bash
# 1. Stop all evaluations
vllm-eval system stop-all
kubectl delete jobs --all -n vllm-eval

# 2. Clear caches and temporary files
vllm-eval system clean --all
kubectl delete pods -l temp=true -n vllm-eval

# 3. Restart core services
vllm-eval system restart
kubectl rollout restart deployment -n vllm-eval

# 4. Validate system health
vllm-eval doctor --verbose
kubectl get pods -n vllm-eval
```

#### Level 2: Configuration Recovery

```bash
# 1. Backup current configuration
cp -r ~/.config/vllm-eval/ ~/.config/vllm-eval.backup/
kubectl get configmaps -n vllm-eval -o yaml > k8s-config-backup.yaml

# 2. Reset to defaults
vllm-eval setup --reset --force
kubectl delete configmaps --all -n vllm-eval

# 3. Restore from backup
vllm-eval config import ~/.config/vllm-eval.backup/production.toml
kubectl apply -f k8s-config-backup.yaml

# 4. Validate configuration
vllm-eval config validate --all-profiles
```

#### Level 3: Full System Recovery

```bash
# 1. Complete teardown
vllm-eval uninstall --purge
make kind-teardown

# 2. Fresh installation
make kind-deploy
make helm-install
pip install -e .

# 3. Restore data from backups
vllm-eval system restore --from-backup /path/to/backup/
kubectl apply -f backup/k8s-resources/

# 4. Comprehensive validation
make run-tests
vllm-eval system validate --comprehensive
```

---

## 📚 Documentation and Resources

### Troubleshooting Resources

- **[CLI Troubleshooting](../cli/troubleshooting.md)** - CLI-specific issues
- **[System Overview](../architecture/system-overview.md)** - Architecture reference
- **[Configuration Guide](../user/benchmark-configuration.md)** - Configuration troubleshooting
- **[API Documentation](../api/evalchemy-api.md)** - Framework-specific issues

### External Resources

- **Kubernetes Troubleshooting**: [k8s.io/docs/tasks/debug-application-cluster/](https://kubernetes.io/docs/tasks/debug-application-cluster/)
- **Argo Workflows**: [argoproj.github.io/argo-workflows/troubleshooting/](https://argoproj.github.io/argo-workflows/troubleshooting/)
- **Docker Issues**: [docs.docker.com/config/troubleshoot/](https://docs.docker.com/config/troubleshoot/)

### Support Escalation

```bash
# Generate support bundle
vllm-eval system support-bundle --include-logs --include-config

# System information for support
vllm-eval system info --verbose > system-info.txt
kubectl cluster-info dump > cluster-info.yaml
```

!!! warning "Production Safety"
    
    Always test troubleshooting procedures in staging environments first.
    
    **Create backups** before making significant changes to production systems.
    
    **Document incidents** for future reference and team knowledge sharing.

!!! success "Operational Excellence"
    
    You now have comprehensive troubleshooting capabilities for both CLI and Kubernetes operations.
    
    **Remember**: Systematic diagnosis leads to faster resolution and better system reliability.