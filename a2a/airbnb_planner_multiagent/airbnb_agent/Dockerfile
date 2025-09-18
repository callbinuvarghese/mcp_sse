# Dockerfile_airbnb_agent
WORKDIR /app

# GOOD: paths from the context root (.)
COPY a2a/airbnb_planner_multiagent/airbnb_agent/pyproject.toml ./
COPY a2a/airbnb_planner_multiagent/airbnb_agent/uv.lock* ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Copy the source
COPY a2a/airbnb_planner_multiagent/airbnb_agent/ ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

ENV PATH="/app/.venv/bin:${PATH}"
CMD ["uv", "run", "python", "-m", "airbnb_agent"]
