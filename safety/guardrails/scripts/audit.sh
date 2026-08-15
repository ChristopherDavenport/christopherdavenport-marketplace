#!/bin/bash
# audit.sh -- record every tool call. A PreToolUse hook on all tools.
#
# CONTRACT: never blocks, never crashes the session. It is an observer, so
# every path exits 0 and errors are swallowed deliberately -- a broken audit
# log must not take down a working session.
#
# Output goes to ${CLAUDE_PLUGIN_DATA}, NOT beside the plugin:
# ${CLAUDE_PLUGIN_ROOT} changes on every plugin update, so anything written
# there is silently lost the next time the plugin upgrades. CLAUDE_PLUGIN_DATA
# is the documented directory that survives updates.
#
#   ${CLAUDE_PLUGIN_DATA}/audit/YYYY-MM-DD.jsonl
#
# Configuration:
#   CLAUDE_GUARDRAILS_AUDIT_OFF=1   disable audit logging
#   CLAUDE_GUARDRAILS_AUDIT_DIR     override the output directory

set +e

[[ "${CLAUDE_GUARDRAILS_AUDIT_OFF:-0}" == "1" ]] && exit 0

DATA_DIR="${CLAUDE_GUARDRAILS_AUDIT_DIR:-${CLAUDE_PLUGIN_DATA:-$HOME/.claude/guardrails}}"
OUT_DIR="$DATA_DIR/audit"
OUT="$OUT_DIR/$(date -u +%Y-%m-%d).jsonl"

input=$(cat 2>/dev/null)
mkdir -p "$OUT_DIR" 2>/dev/null

command -v jq >/dev/null 2>&1 || exit 0

# --arg / --argjson keep this injection-safe whatever tool_input contains.
printf '%s' "$input" | jq -c \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{
      ts: $ts,
      session: .session_id,
      cwd: .cwd,
      permission_mode: .permission_mode,
      agent_id: (.agent_id // null),
      agent_type: (.agent_type // null),
      tool: .tool_name,
      input: .tool_input
   }' >> "$OUT" 2>/dev/null

# A silent gap in the audit log is worse than a noisy one: leave a breadcrumb
# so a missing record is visible rather than indistinguishable from "no calls".
if [[ $? -ne 0 ]]; then
  printf '{"ts":"%s","audit_error":true}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$OUT" 2>/dev/null
fi

exit 0
