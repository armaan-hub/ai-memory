#!/bin/bash
# Gemini CLI with Memory Context (Simple Version)
# Usage: gemini-memory.sh "your prompt"

PROMPT="${1:-}"
PROJECT="${PWD##*/}"

# Echo context prefix
echo "=== Memory Context for $PROJECT ==="
echo ""

# Run Gemini
if [ -n "$PROMPT" ]; then
    gemini "$PROMPT"
else
    gemini
fi
