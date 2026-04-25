FROM python:3.11-slim

WORKDIR /app

RUN useradd --no-create-home --shell /bin/false appuser

COPY pyproject.toml ./
COPY src/ ./src/
RUN pip install .

USER appuser
CMD ["python", "-c", "import time; time.sleep(9999)"]