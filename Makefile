.PHONY: help kind-deploy kind-clean helm-install helm-uninstall run-tests build-images push-images lint format clean

# Default target
help: ## Show this help message
	@echo "VLLM Evaluation System - Available Commands:"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# Variables
CLUSTER_NAME ?= vllm-eval-local
NAMESPACE ?= mlops
REGISTRY ?= ghcr.io/your-org
VERSION ?= $(shell git rev-parse --short HEAD)
RELEASE_TAG ?= release-$(VERSION)

# Kind cluster management
kind-deploy: ## Deploy Kind cluster with Argo and dependencies
	@echo "🚀 Creating Kind cluster: $(CLUSTER_NAME)"
	@if ! kind get clusters | grep -q $(CLUSTER_NAME); then \
		kind create cluster --name $(CLUSTER_NAME) --config scripts/kind-config.yaml; \
	else \
		echo "✅ Cluster $(CLUSTER_NAME) already exists"; \
	fi
	@echo "📦 Installing Argo Workflows..."
	kubectl create namespace argo --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -n argo -f https://github.com/argoproj/argo-workflows/releases/download/v3.5.2/install.yaml
	@echo "📦 Installing Argo Events..."
	kubectl create namespace argo-events --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -n argo-events -f https://raw.githubusercontent.com/argoproj/argo-events/stable/manifests/install.yaml
	@echo "📦 Installing NGINX Ingress..."
	kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.2/deploy/static/provider/kind/deploy.yaml
	kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=90s
	@echo "✅ Kind cluster ready!"

kind-clean: ## Delete Kind cluster
	@echo "🗑️  Deleting Kind cluster: $(CLUSTER_NAME)"
	kind delete cluster --name $(CLUSTER_NAME)

# Helm management
helm-install: ## Install all Helm charts
	@echo "📊 Installing ClickHouse..."
	helm repo add altinity https://docs.altinity.com/clickhouse-operator/
	helm repo update
	kubectl create namespace $(NAMESPACE) --dry-run=client -o yaml | kubectl apply -f -
	helm upgrade --install clickhouse-operator altinity/altinity-clickhouse-operator -n $(NAMESPACE)
	helm upgrade --install clickhouse charts/clickhouse -n $(NAMESPACE)
	@echo "📈 Installing Grafana..."
	helm repo add grafana https://grafana.github.io/helm-charts
	helm repo update
	helm upgrade --install grafana charts/grafana -n $(NAMESPACE)
	@echo "🔄 Installing Argo Workflows..."
	helm upgrade --install argo-workflows charts/argo-workflows -n $(NAMESPACE)
	@echo "✅ All charts installed!"

helm-uninstall: ## Uninstall all Helm charts
	@echo "🗑️  Uninstalling Helm charts..."
	-helm uninstall grafana -n $(NAMESPACE)
	-helm uninstall clickhouse -n $(NAMESPACE)
	-helm uninstall clickhouse-operator -n $(NAMESPACE)
	-helm uninstall argo-workflows -n $(NAMESPACE)

# Docker image management
build-images: ## Build all Docker images
	@echo "🔨 Building Docker images..."
	docker build -f docker/deepeval.Dockerfile -t $(REGISTRY)/vllm-eval-deepeval:$(VERSION) .
	docker build -f docker/evalchemy.Dockerfile -t $(REGISTRY)/vllm-eval-evalchemy:$(VERSION) .
	docker build -f docker/workflow-tools.Dockerfile -t $(REGISTRY)/vllm-eval-tools:$(VERSION) .

build-legacy-evalchemy: ## Build Legacy Evalchemy container (old lm-eval based)
	@echo "🔨 Building Legacy Evalchemy image..."
	docker build -f docker/legacy-evalchemy.Dockerfile -t $(REGISTRY)/vllm-eval-legacy-evalchemy:$(VERSION) .

push-images: build-images ## Push Docker images to registry
	@echo "📤 Pushing Docker images..."
	docker push $(REGISTRY)/vllm-eval-deepeval:$(VERSION)
	docker push $(REGISTRY)/vllm-eval-evalchemy:$(VERSION)
	docker push $(REGISTRY)/vllm-eval-tools:$(VERSION)
	@echo "🏷️  Tagging as release..."
	docker tag $(REGISTRY)/vllm-eval-deepeval:$(VERSION) $(REGISTRY)/vllm-eval-deepeval:$(RELEASE_TAG)
	docker tag $(REGISTRY)/vllm-eval-evalchemy:$(VERSION) $(REGISTRY)/vllm-eval-evalchemy:$(RELEASE_TAG)
	docker tag $(REGISTRY)/vllm-eval-tools:$(VERSION) $(REGISTRY)/vllm-eval-tools:$(RELEASE_TAG)
	docker push $(REGISTRY)/vllm-eval-deepeval:$(RELEASE_TAG)
	docker push $(REGISTRY)/vllm-eval-evalchemy:$(RELEASE_TAG)
	docker push $(REGISTRY)/vllm-eval-tools:$(RELEASE_TAG)

# Testing
run-tests: ## Run all tests locally
	@echo "🧪 Running Python tests..."
	python -m pytest eval/deepeval_tests/ -v
	@echo "🔍 Running linting..."
	ruff check . --fix
	@echo "🎨 Running formatting..."
	ruff format .
	@echo "📋 Running type checking..."
	mypy eval/ scripts/

lint: ## Run linting checks
	@echo "🔍 Running ruff check..."
	ruff check .
	@echo "📋 Running mypy..."
	mypy eval/ scripts/

format: ## Format code
	@echo "🎨 Formatting code..."
	ruff format .

# Dataset management
prepare-datasets: ## Prepare and deduplicate datasets
	@echo "📊 Preparing datasets..."
	python scripts/dedup_datasets.py
	@echo "✅ Datasets prepared!"

# Monitoring
port-forward-grafana: ## Port forward Grafana dashboard
	@echo "📈 Port forwarding Grafana (http://localhost:3000)..."
	kubectl port-forward -n $(NAMESPACE) svc/grafana 3000:80

port-forward-argo: ## Port forward Argo Workflows UI
	@echo "🔄 Port forwarding Argo Workflows (http://localhost:2746)..."
	kubectl port-forward -n argo svc/argo-server 2746:2746

# Development
dev-setup: ## Setup development environment
	@echo "🛠️  Setting up development environment..."
	pip install -r requirements-dev.txt
	pre-commit install
	@echo "✅ Development environment ready!"

# Workflow management
submit-workflow: ## Submit test workflow
	@echo "🚀 Submitting test workflow..."
	argo submit -n $(NAMESPACE) infra/argo-workflows/workflow-template.yaml \
		--parameter model_tag=test-$(VERSION) \
		--parameter dataset_version=latest

watch-workflow: ## Watch workflow execution
	@echo "👀 Watching workflows..."
	argo watch -n $(NAMESPACE) -w

# Database operations
clickhouse-client: ## Connect to ClickHouse client
	@echo "🗄️  Connecting to ClickHouse..."
	kubectl exec -it -n $(NAMESPACE) clickhouse-0 -- clickhouse-client

# Clean up
clean: ## Clean up temporary files and caches
	@echo "🧹 Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type f -name ".coverage" -delete
	docker system prune -f

# All-in-one commands
deploy-all: kind-deploy helm-install ## Deploy everything (Kind + Helm charts)
	@echo "🎉 Full deployment completed!"

destroy-all: helm-uninstall kind-clean ## Destroy everything
	@echo "💥 Everything destroyed!"

# Release management
release: build-images push-images ## Build and push release images
	@echo "🚀 Release $(RELEASE_TAG) completed!"
