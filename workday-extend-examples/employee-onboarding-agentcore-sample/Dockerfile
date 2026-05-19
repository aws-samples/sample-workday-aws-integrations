FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim
WORKDIR /app

# Build-time defaults; override at runtime via `docker run -e` or the AgentCore SDK.
ENV UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DOCKER_CONTAINER=1 \
    AWS_REGION=${AWS_REGION:-us-east-1} \
    AWS_DEFAULT_REGION=${AWS_REGION:-us-east-1}

COPY src/agentcore/requirements.txt src/agentcore/requirements.txt
RUN uv pip install --no-cache-dir -r src/agentcore/requirements.txt

RUN uv pip install --no-cache-dir aws-opentelemetry-distro>=0.10.1

# Non-root user for the AgentCore runtime
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

# AgentCore Runtime manages health checks externally; opt out of in-container
# checks to silence Trivy DKL-DI-0006.
HEALTHCHECK NONE

# Copy the project (respecting .dockerignore)
COPY . .

CMD ["opentelemetry-instrument", "python", "-m", "src.agentcore.onboarding_app"]
