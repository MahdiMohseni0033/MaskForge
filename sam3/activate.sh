#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
conda activate "$PROJECT_ROOT/.venv"
export PYTHONNOUSERSITE=1
