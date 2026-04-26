.PHONY: dev dev-down proto migrate lint test test-unit test-integration build infra-synth infra-diff infra-deploy clean help

# ── Local dev ─────────────────────────────────────────────────────────────────

dev: ## Start the full local dev stack (LocalStack, Postgres, linux-target, services)
	cp -n .env.example .env 2>/dev/null || true
	docker compose up -d --build

dev-down: ## Stop and remove all local containers and volumes
	docker compose down -v

# ── Protobuf code generation ──────────────────────────────────────────────────
# Generates Python stubs into asset-manager/src/asset_manager/generated/
# and test-manager/src/test_manager/generated/ from .proto files.

proto: ## Generate Protobuf/gRPC Python stubs from proto/
	python3 -m grpc_tools.protoc \
		-I proto \
		--python_out=asset-manager/src/asset_manager/generated \
		--grpc_python_out=asset-manager/src/asset_manager/generated \
		--pyi_out=asset-manager/src/asset_manager/generated \
		proto/*.proto
	python3 -m grpc_tools.protoc \
		-I proto \
		--python_out=test-manager/src/test_manager/generated \
		--grpc_python_out=test-manager/src/test_manager/generated \
		--pyi_out=test-manager/src/test_manager/generated \
		proto/*.proto
	sed -i 's/^import \(.*_pb2\) as/from . import \1 as/' \
		asset-manager/src/asset_manager/generated/*_pb2_grpc.py	
	@echo "Stubs generated."

# ── Database migrations ───────────────────────────────────────────────────────

migrate: ## Run Alembic migrations against the local Postgres instance
	cd test-manager && alembic upgrade head

# ── Linting ───────────────────────────────────────────────────────────────────

lint: ## Lint all Python (ruff) and CDK TypeScript (tsc --noEmit)
	ruff check asset-manager/src asset-manager/tests
	ruff check test-manager/src test-manager/tests
	ruff check device-adapter/src device-adapter/tests
	cd infra && npx tsc --noEmit

# ── Tests ─────────────────────────────────────────────────────────────────────

test: ## Run all tests (requires make dev running for integration tests)
	$(MAKE) test-unit
	$(MAKE) test-integration

test-unit: ## Run unit tests only (no Docker required — uses moto for DynamoDB)
	pytest asset-manager/tests/unit -v
	pytest test-manager/tests/unit -v
	pytest device-adapter/tests/unit -v
	cd infra && npm test

test-integration: ## Run integration tests (requires make dev running)
	pytest asset-manager/tests/integration -v
	pytest test-manager/tests/integration -v
	pytest device-adapter/tests/integration -v

# ── Docker image build ────────────────────────────────────────────────────────

build: ## Build all Docker images (tagged with current git SHA)
	docker build -t asset-manager:$(shell git rev-parse --short HEAD) ./asset-manager
	docker build -t test-manager:$(shell git rev-parse --short HEAD) ./test-manager

# ── CDK / Infrastructure ──────────────────────────────────────────────────────

infra-synth: ## Synthesize CDK app → CloudFormation templates in infra/cdk.out/
	cd infra && npm run build && npx cdk synth

infra-diff: ## Show diff between deployed stack and local CDK app
	cd infra && npx cdk diff

infra-deploy: ## Deploy CDK stacks to AWS (requires valid AWS credentials)
	cd infra && npx cdk deploy --all --require-approval broadening

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean: ## Remove generated stubs, build artifacts, and pytest cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name generated -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf infra/dist infra/cdk.out

# ── Help ──────────────────────────────────────────────────────────────────────

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'