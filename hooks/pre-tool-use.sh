#!/usr/bin/env bash
# PreToolUse hook — enforces stage-based tool allow-list.
# Reads stage from .ph-stage (written by the /rhdp-publishing-house skill).
# If no stage file exists, all tools are allowed.

STAGE_FILE=".ph-stage"
TOOL="${CLAUDE_TOOL_NAME:-${TOOL_NAME:-}}"

[[ -z "$TOOL" ]] && exit 0
[[ ! -f "$STAGE_FILE" ]] && exit 0

STAGE=$(tr -d '[:space:]' < "$STAGE_FILE")

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

BLOCKED="reporting.db.prod|mcp__reporting|ph_rcars_query"
if echo "$TOOL" | grep -qiE "$BLOCKED"; then
  echo "[PH Hook] BLOCKED: '$TOOL' is not permitted in stage='$STAGE'. Use only PH-approved tools." >&2
  exit 2
fi

exit 0
