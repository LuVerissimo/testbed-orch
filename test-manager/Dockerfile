# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY test-manager/src/ ./src/
COPY proto/ ./proto/

RUN pip install grpcio-tools && \
    mkdir -p src/test_manager/generated && \
    touch src/test_manager/generated/__init__.py && \
    python -m grpc_tools.protoc \
        -I proto \
        --python_out=src/test_manager/generated \
        --grpc_python_out=src/test_manager/generated \
        --pyi_out=src/test_manager/generated \
        proto/test_manager.proto && \
    sed -i 's/^import \(.*_pb2\) as/from . import \1 as/' \
        src/test_manager/generated/*_pb2_grpc.py

COPY test-manager/pyproject.toml ./

RUN python -m venv /venv && \
    /venv/bin/pip install --no-cache-dir .

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim

RUN useradd --no-create-home --shell /bin/false appuser

COPY --from=builder /venv /venv
COPY --from=builder /build/src /app/src/

ENV PATH="/venv/bin:$PATH"

WORKDIR /app
USER appuser
CMD ["uvicorn", "test_manager.app:app", "--host", "0.0.0.0", "--port", "8000"]