FROM python:3.13-slim-bookworm@sha256:a1165e272e578941b84abc79e4ab38a0305cd12803a5c4247979ac7655f4d641 AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY backend/requirements.lock /app/backend/requirements.lock
RUN pip install --no-cache-dir -r backend/requirements.lock && useradd --create-home --uid 10001 app
COPY backend /app/backend
USER app
CMD ["python", "-m", "uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log", "--no-proxy-headers"]

FROM base AS tests
COPY tests /app/tests
COPY evaluation /app/evaluation
COPY contracts /app/contracts
CMD ["python", "-m", "pytest", "-q", "-o", "cache_dir=/tmp/pytest-cache", "tests"]
