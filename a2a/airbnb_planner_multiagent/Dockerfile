# syntax=docker/dockerfile:1

ARG PYTHON_IMAGE=ghcr.io/astral-sh/uv:0.6.11-python3.12-bookworm-slim
FROM ${PYTHON_IMAGE} AS base

# Required args:
#  - AGENT_DIR: folder with the agent code (relative to repo root)
#  - MODULE:    python module to run (must have __main__.py)
ARG AGENT_DIR
ARG MODULE

WORKDIR /app

# Copy shared deps first for better caching
# (Paths are relative to the *build context*, which we'll set to repo root.)
COPY a2a/airbnb_planner_multiagent/pyproject.toml ./pyproject.toml
# If you have a lock file, uncomment the next line and keep --frozen below
# COPY a2a/airbnb_planner_multiagent/uv.lock ./uv.lock

# Install dependencies (no project install; project may not be a package)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project

# Copy just this agent's source
COPY ${AGENT_DIR}/ /app/${MODULE}/

ENV PATH="/app/.venv/bin:${PATH}"

# Run the module (requires __main__.py inside that module)
CMD uv run python -m ${MODULE}

