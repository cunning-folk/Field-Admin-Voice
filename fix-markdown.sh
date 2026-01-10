#!/bin/bash

# Markdown Linting and Auto-Fix Script
# Usage: ./fix-markdown.sh [file.md] or ./fix-markdown.sh (for all .md files)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if markdownlint-cli is installed
if ! command -v npx &> /dev/null; then
    echo -e "${RED}Error: npx not found. Please install Node.js${NC}"
    exit 1
fi

# Determine target files
if [ -n "$1" ]; then
    # Single file provided
    if [ ! -f "$1" ]; then
        echo -e "${RED}Error: File '$1' not found${NC}"
        exit 1
    fi
    FILES="$1"
else
    # Find all markdown files
    FILES=$(find . -name "*.md" -type f | grep -v node_modules)
fi

echo -e "${YELLOW}Markdown Linter & Fixer${NC}"
echo "========================"

for file in $FILES; do
    echo -e "\n${YELLOW}Processing:${NC} $file"

    # Run markdownlint with auto-fix
    if npx markdownlint --fix "$file" 2>/dev/null; then
        echo -e "${GREEN}✓ Auto-fixed what was possible${NC}"
    fi

    # Check for remaining issues
    ISSUES=$(npx markdownlint "$file" 2>&1 || true)

    if [ -z "$ISSUES" ]; then
        echo -e "${GREEN}✓ No remaining issues${NC}"
    else
        echo -e "${RED}Remaining issues (require manual fix):${NC}"
        echo "$ISSUES"
    fi
done

echo -e "\n${GREEN}Done!${NC}"
