# RHDPCD-183: PreToolUse Hook Format Fix

## Issue
Claude Code was rejecting `.claude/settings.json` with the error:
```
hooks.PreToolUse.0.hooks: Expected array, but received undefined
```

## Root Cause
The `PreToolUse` hook entry was missing a `"hooks"` array wrapper. The schema requires:
```json
{
  "matcher": "PATTERN",
  "hooks": [
    { "type": "command", "command": "..." }
  ]
}
```

But the broken version had:
```json
{
  "matcher": ".*",
  "command": "bash hooks/pre-tool-use.sh"
}
```

## Fix Applied
Wrapped the command in a `"hooks"` array with `"type": "command"`:

```json
{
  "matcher": ".*",
  "hooks": [
    {
      "type": "command",
      "command": "bash hooks/pre-tool-use.sh"
    }
  ]
}
```

This now matches the schema used by `PostToolUse` entries.

## File Changes
- `.claude/settings.json` — restructured PreToolUse to have hooks array

## Note on Committing
The file cannot be pushed directly due to Claude Code's security restrictions on `.claude/` contents.
This is a team-level issue that requires either:
1. Manual merge approval from a human reviewer
2. Updating project `.claude/` settings permissions
3. Moving hook config to a non-`.claude/` location

## Verification
The fixed JSON passes:
```bash
jq empty ./.claude/settings.json
✓ JSON is valid
```

---
**RHDPCD-183** | Date: 2026-07-09 | Status: Ready for team review
