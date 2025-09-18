# syntax=docker/dockerfile:1

# uv + Python base (small, fast)
FROM ghcr.io/astral-sh/uv:0.6.11-python3.12-bookworm-slim

WORKDIR /app

# Copy project metadata first to leverage Docker layer caching
COPY pyproject.toml uv.lock* ./

# Install only dependencies first (faster rebuilds)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

# Now copy the rest of the source
COPY . .

# Install the project into the venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

# Drop privileges (optional but recommended)
RUN useradd -m -u 10001 appuser
USER appuser

# Ensure the venv is on PATH
ENV PATH="/app/.venv/bin:${PATH}"

# Run your package as a module (requires airbnb_agent/__main__.py)
CMD ["uv", "run", "python", "-m", "."]
