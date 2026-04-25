# ADR 001 — Core Architecture Decisions

**Status:** Accepted  
**Date:** 2026-04-25

## Context

We're building a distributed Test Orchestration Framework for coordinating physical and virtual test devices. The system must support concurrent device reservations, async job execution, and structured result storage, while being deployable to AWS and runnable fully offline for air-gapped environments.

## Decisions

### 1. DynamoDB for device reservation state (Asset Manager)

**Decision:** Asset Manager stores device state in DynamoDB, not PostgreSQL.

**Rationale:**
- Reservation lookups are always keyed by `deviceId` — no relational joins needed.
- DynamoDB's single-digit-millisecond reads are well suited to high-frequency reservation checks.
- On-demand billing eliminates capacity planning for bursty lab workloads.
- TTL attribute auto-expires stale reservations without a cleanup cron job.

**Trade-offs:**
- No ad-hoc queries without a GSI. Acceptable — we know our access patterns upfront.
- Limited transaction semantics compared to PostgreSQL (DynamoDB transactions exist but are
  coarser). Acceptable for reservation state where eventual consistency is tolerable.

---

### 2. gRPC + Protobuf for Asset Manager transport

**Decision:** Asset Manager exposes a gRPC API defined by a Protobuf IDL, not REST.

**Rationale:**
- Protobuf IDL is a language-neutral contract — Python clients and TypeScript clients generate
  stubs from the same `.proto` file, eliminating drift between producer and consumer.
- gRPC is binary and more efficient than JSON over REST for high-frequency internal calls.
- Strong typing at the transport layer catches contract violations at compile time.

**Trade-offs:**
- Harder to curl/debug than REST. Mitigated with grpcurl in the runbook.
- Requires stub generation in CI (see `make proto`).

---

### 3. PostgreSQL for Test Manager job store

**Decision:** Test Manager stores jobs and results in PostgreSQL.

**Rationale:**
- Job history queries are ad-hoc: filter by device, status, date range, user. SQL is the right
  tool for flexible relational queries.
- SQLAlchemy + Alembic gives us schema migrations with a clear audit trail — important for
  long-running testbed environments where the schema evolves.

---

### 4. SQS for job dispatch (Test Manager → Worker)

**Decision:** Test Manager enqueues jobs to SQS; an Orchestration Worker polls and executes.

**Rationale:**
- Decouples the API from execution — the REST endpoint returns immediately with a `QUEUED`
  status; the worker processes at its own rate.
- SQS visibility timeout provides at-least-once delivery and automatic retry on worker crash.
- Dead-letter queue captures jobs that repeatedly fail for manual inspection.

---

### 5. Amazon CDK (TypeScript) for infrastructure

**Decision:** All AWS resources are defined as CDK stacks, not raw CloudFormation YAML.

**Rationale:**
- CDK L2 constructs encode AWS best practices (encryption, IAM least-privilege) as defaults.
- TypeScript gives us type-safe resource references — mistyping a table name is a compile
  error, not a runtime failure.
- `cdk synth` generates CloudFormation for review without deploying, which satisfies change
  review requirements in classified environments.

---

## Consequences

- CI must run `make proto` before Python tests to ensure generated stubs are present.
- `cdk synth` output (in `infra/cdk.out/`) must be reviewed in every PR touching `infra/`.
- `RemovalPolicy.RETAIN` must be enforced on all data stores before any non-dev deployment.