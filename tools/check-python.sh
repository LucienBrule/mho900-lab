#!/bin/sh
# Run only the new typed workspace's gates, preserving pinned legacy sources.
set -eu
cd "$(dirname "$0")/.."
uv sync --locked --all-packages
uv run --locked ruff check packages
uv run --locked ruff format --check packages
uv run --locked mypy
uv run --locked mho-lab quality packages
uv run --locked pytest
