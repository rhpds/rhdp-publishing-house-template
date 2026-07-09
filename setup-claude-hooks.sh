#!/bin/bash
# Setup script for .claude/settings.json hooks
# Required for RHDPCD-183 PreToolUse hook configuration

set -e

TEMPLATE_FILE=".claude.settings.template.json"
TARGET_FILE=".claude/settings.json"

if [ ! -f "$TEMPLATE_FILE" ]; then
  echo "✗ ERROR: $TEMPLATE_FILE not found"
  exit 1
fi

if [ -f "$TARGET_FILE" ]; then
  echo "✓ $TARGET_FILE already exists"
  echo "  To update, run: cp $TEMPLATE_FILE $TARGET_FILE"
  exit 0
fi

mkdir -p .claude
cp "$TEMPLATE_FILE" "$TARGET_FILE"

echo "✓ Created $TARGET_FILE from template"
echo "✓ PreToolUse hooks configured (RHDPCD-183)"
echo ""
echo "Note: This file cannot be committed due to Claude Code security restrictions."
echo "Changes made manually in .claude/settings.json are local-only."

# Validate
if jq empty "$TARGET_FILE" 2>/dev/null; then
  echo "✓ JSON validation passed"
else
  echo "✗ JSON validation failed"
  exit 1
fi

exit 0
