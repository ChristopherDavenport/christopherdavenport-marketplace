#!/bin/bash
# verify-gate.sh -- an agent may not declare done on a red build.
#
# A Stop hook. Exit 2 prevents Claude from stopping and feeds stderr back as
# the reason to keep working, turning "the agent says it works" into "the
# build says it works".
#
# OPT-IN BY DESIGN. This is the one hook that must not have a default.
# A Stop gate that guesses a verify command would block every turn in every
# repository that does not have one -- for a plugin other people install,
# that is hostile. It stays inert until you name the command:
#
#   export CLAUDE_GUARDRAILS_VERIFY="make verify"
#   export CLAUDE_GUARDRAILS_VERIFY="npm test && npm run lint"
#
# Put it in the project's .envrc, your shell profile, or a project settings
# file -- wherever it is scoped to repos that genuinely have a verify target.
#
# Also honours:
#   CLAUDE_GUARDRAILS_VERIFY_TIMEOUT   seconds (default 300)

set -uo pipefail

VERIFY="${CLAUDE_GUARDRAILS_VERIFY:-}"
[[ -z "$VERIFY" ]] && exit 0

input=$(cat 2>/dev/null)

# Guard against a Stop-hook loop: if we already blocked once and Claude is
# stopping again, let it go. Otherwise a permanently-red build becomes an
# infinite conversation.
if command -v jq >/dev/null 2>&1; then
  if [[ "$(printf '%s' "$input" | jq -r '.stop_hook_active // false' 2>/dev/null)" == "true" ]]; then
    exit 0
  fi
fi

PROJECT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
TIMEOUT="${CLAUDE_GUARDRAILS_VERIFY_TIMEOUT:-300}"

log=$(mktemp -t guardrails-verify)
trap 'rm -f "$log"' EXIT

# macOS ships neither `timeout` nor `gtimeout`, so a naive wrapper silently
# no-ops there and the gate never actually runs. Background + watchdog works
# everywhere.
(
  cd "$PROJECT" || exit 1
  eval "$VERIFY"
) >"$log" 2>&1 &
pid=$!
( sleep "$TIMEOUT"; kill -TERM "$pid" 2>/dev/null ) &
watcher=$!
wait "$pid" 2>/dev/null; rc=$?
kill -TERM "$watcher" 2>/dev/null; wait "$watcher" 2>/dev/null

[[ $rc -eq 0 ]] && exit 0

{
  if [[ $rc -eq 143 ]]; then
    echo "verify-gate: '$VERIFY' timed out after ${TIMEOUT}s."
  else
    echo "verify-gate: '$VERIFY' is failing, so the work is not done."
  fi
  echo "Fix it before stopping. Last 40 lines:"
  echo "---"
  tail -40 "$log"
} >&2
exit 2
