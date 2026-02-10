#!/bin/bash
# Gatekeeper: Production-grade quality & security pipeline. Exit 1 if any check fails.

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Use venv Python if present so ruff/mypy are found
if [ -x "$ROOT/.venv/bin/python" ]; then
    PYTHON="$ROOT/.venv/bin/python"
else
    PYTHON="python"
fi

FAILED=0

echo "🛡️  Security & Quality Gatekeeper (Production)"
echo "------------------------------------------------"

# 1. Formatter (auto-fix)
if "$PYTHON" -m ruff format . 2>/dev/null; then
    echo -e "${GREEN}✅ 1. Formatter (ruff format): SUCCESS${NC}"
else
    echo -e "${RED}❌ 1. Formatter (ruff format): FAILURE${NC}"
    FAILED=1
fi

# 2. Linter (auto-fix where possible)
if "$PYTHON" -m ruff check . --fix 2>/dev/null; then
    echo -e "${GREEN}✅ 2. Linter (ruff check): SUCCESS${NC}"
else
    echo -e "${RED}❌ 2. Linter (ruff check): FAILURE${NC}"
    FAILED=1
fi

# 3. Type check (strict)
if "$PYTHON" -m mypy . 2>/dev/null; then
    echo -e "${GREEN}✅ 3. Type check (mypy): SUCCESS${NC}"
else
    echo -e "${RED}❌ 3. Type check (mypy): FAILURE${NC}"
    FAILED=1
fi

# 4. Security — ban potential API keys; exclude .env and .git
KEY_PATTERN="sk-[a-zA-Z0-9]{20,}|az-[a-zA-Z0-9]{20,}"
if grep -rE "$KEY_PATTERN" \
    --include='*.py' --include='*.yaml' --include='*.yml' --include='*.json' --include='*.sh' \
    --exclude-dir=.git --exclude-dir=.venv --exclude='.env' --exclude='.env.*' . 2>/dev/null; then
    echo -e "${RED}❌ 4. Security (API keys): FAILURE — Potential key in source.${NC}"
    FAILED=1
else
    echo -e "${GREEN}✅ 4. Security (API keys): SUCCESS${NC}"
fi

# 5. Markers — block forbidden markers (exclude this script)
if grep -rE "TODO: REMOVE THIS|FIXME: URGENT" \
    --include='*.py' --include='*.yaml' --include='*.yml' --include='*.md' --include='*.sh' \
    --exclude-dir=.git --exclude-dir=.venv --exclude="verify_quality.sh" . 2>/dev/null; then
    echo -e "${RED}❌ 5. Markers: FAILURE — Forbidden markers found.${NC}"
    FAILED=1
else
    echo -e "${GREEN}✅ 5. Markers: SUCCESS${NC}"
fi

# 6. Documentation
if "$PYTHON" scripts/check_docs.py 2>/dev/null; then
    echo -e "${GREEN}✅ 6. Documentation: SUCCESS${NC}"
else
    echo -e "${RED}❌ 6. Documentation: FAILURE${NC}"
    FAILED=1
fi

echo "------------------------------------------------"
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}✅ SUCCESS — All checks passed.${NC}"
    exit 0
else
    echo -e "${RED}❌ FAILURE — One or more checks failed. Commit blocked.${NC}"
    exit 1
fi
