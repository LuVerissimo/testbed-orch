# Operational Runbook

## Start the local dev stack

```bash
make dev
# Services: LocalStack :4566, PostgreSQL :5432, linux-target :2222
#           asset-manager :50051, test-manager :8000
```

## Check service health

```bash
# LocalStack
curl -s http://localhost:4566/_localstack/health | jq .

# PostgreSQL
docker compose exec postgres pg_isready -U testorch

# gRPC (asset-manager)
grpcurl -plaintext localhost:50051 list
```

## Submit a test job

```bash
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"device_id": "device-001", "command": "uname -a", "timeout_seconds": 30}'
# → {"job_id": "abc123", "status": "QUEUED"}

curl http://localhost:8000/jobs/abc123
# → {"job_id": "abc123", "status": "COMPLETED", "exit_code": 0, "stdout": "Linux ..."}
```

## Run database migrations

```bash
make migrate
```

## Regenerate Protobuf stubs

```bash
make proto
# Stubs written to asset-manager/src/asset_manager/generated/
#                  test-manager/src/test_manager/generated/
```

## CDK operations

```bash
make infra-synth          # generate CloudFormation (no deploy)
make infra-diff           # diff local vs deployed
make infra-deploy         # deploy to AWS (requires credentials)
```

## Tear down local stack

```bash
make dev-down             # stops containers and removes volumes
```