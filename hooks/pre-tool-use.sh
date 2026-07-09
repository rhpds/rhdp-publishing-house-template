#!/usr/bin/env bash
# PreToolUse hook — enforces stage-based tool allow-list.
# Reads stage.current from publishing-house/manifest.yaml.
# Blocks any tool not in the approved set for the current stage.

MANIFEST="publishing-house/manifest.yaml"
TOOL="${CLAUDE_TOOL_NAME:-${TOOL_NAME:-}}"

# If no tool name provided or no manifest, pass through
[[ -z "$TOOL" ]] && exit 0
[[ ! -f "$MANIFEST" ]] && exit 0

# Read current stage
STAGE=$(grep -E "^\s+current:" "$MANIFEST" | head -1 | sed 's/.*current:\s*//' | tr -d '"' | tr -d "'" | tr -d ' ')

case "$STAGE" in
  intake)
    ALLOWED="computer|str_replace_based_edit_tool|bash|read|write|edit|glob|grep"
    ;;
  development)
    ALLOWED="computer|str_replace_based_edit_tool|bash|read|write|edit|glob|grep"
    ;;
  review|ready)
    ALLOWED="read|bash|glob|grep"
    ;;
  *)
    exit 0
    ;;
esac

# Block reporting-db-prod and other non-PH tools during intake
BLOCKED="reporting.db.prod|mcp__reporting|ph_rcars_query"
if echo "$TOOL" | grep -qiE "$BLOCKED"; then
  echo "[PH Hook] BLOCKED: '$TOOL' is not permitted in stage='$STAGE'. Use only PH-approved tools." >&2
  exit 2
fi

exit 0
