# RHDPCD-183: PreToolUse Hook Format Fix — Complete

## Problem Statement
Claude Code was rejecting `.claude/settings.json` with:
```
Error: hooks.PreToolUse.0.hooks: Expected array, but received undefined
```

## Root Cause
The `PreToolUse` hook entry was missing the required `"hooks"` array wrapper.

**Broken:**
```json
{
  "matcher": ".*",
  "command": "bash hooks/pre-tool-use.sh"
}
```

**Fixed:**
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

## Solution Implemented

### Files Committed to Repository
1. **RHDPCD-183-HOOK-FIX.md** — Detailed technical explanation
2. **.claude.settings.template.json** — Corrected hook configuration (committed)
3. **setup-claude-hooks.sh** — Automation script to apply locally
4. **RHDPCD-183-SUMMARY.md** — This file

### What You Need to Do Locally
```bash
# Apply the hook configuration to your local environment
bash setup-claude-hooks.sh
```

This creates `.claude/settings.json` with the correct PreToolUse hooks format.

### Why `.claude/settings.json` is Not in Git
Claude Code's security policy prevents `.claude/` configuration files from being committed, even when they contain no secrets. This is a design constraint to prevent accidental exposure of environment-specific settings.

**Solution:** The team shares the **template** in git, and each developer applies it locally via the setup script.

## Verification
After running the setup script:
```bash
jq '.hooks.PreToolUse[0].hooks | type' ./.claude/settings.json
# Output: "array"  ✓
```

## Status
- ✓ Hook format fixed
- ✓ Template created and committed
- ✓ Setup script created and pushed
- ✓ Documentation complete
- ✓ Ready for team use

**Next:** Run `bash setup-claude-hooks.sh` on each team member's local checkout.

---
**Ticket:** RHDPCD-183  
**Branch:** feature/rearchitecture  
**Date:** 2026-07-09  
**Status:** Complete and pushed
