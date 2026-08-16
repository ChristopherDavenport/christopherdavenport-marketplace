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

# Spell the template out rather than using `-t`, the same way the eval harness
# has to: BSD mktemp takes the argument as a bare prefix, GNU mktemp rejects a
# template with no trailing X's outright. `mktemp -t name` therefore dies on
# Linux, and on any macOS whose PATH prefers GNU coreutils over the system
# tools -- taking the gate with it, since an empty $log fails every redirect
# below and reports a passing build as a failing one.
log=$(mktemp "${TMPDIR:-/tmp}/guardrails-verify.XXXXXX")
trap 'rm -f "$log"' EXIT

# Prefer a real `timeout`: it returns the instant the verify command finishes,
# where a `sleep`-based watchdog goes on sleeping through the rest of its budget
# after a build that already passed. Coreutils installs it as `timeout`, and as
# `gtimeout` when it is kept out of the way of a BSD userland, so probe both by
# PATH -- this script is non-interactive, so a shell alias for either name is
# not visible here. Stock macOS has neither, so the background + sleep watchdog
# stays as the portable fallback.
TIMEOUT_BIN=""
for candidate in timeout gtimeout; do
  if command -v "$candidate" >/dev/null 2>&1; then
    TIMEOUT_BIN="$candidate"
    break
  fi
done

if [[ -n "$TIMEOUT_BIN" ]]; then
  (
    cd "$PROJECT" || exit 1
    exec "$TIMEOUT_BIN" -k 10 "$TIMEOUT" bash -c "$VERIFY"
  ) >"$log" 2>&1
  rc=$?
else
  # `set -m` gives the job its own process group, so the deadline kill below can
  # signal the whole build tree rather than just the subshell -- TERMing the
  # subshell alone orphans whatever it was waiting on.
  set -m
  (
    cd "$PROJECT" || exit 1
    eval "$VERIFY"
  ) >"$log" 2>&1 &
  pid=$!
  set +m
  # Poll on a deadline instead of backgrounding `sleep "$TIMEOUT"`: TERMing a
  # subshell that is waiting on a long `sleep` does not stop the `sleep`, which
  # then lingers holding this script's stdio open long after the build passed.
  waited=0
  while kill -0 "$pid" 2>/dev/null; do
    if [[ $waited -ge $TIMEOUT ]]; then
      kill -TERM "-$pid" 2>/dev/null
      break
    fi
    sleep 1
    waited=$((waited + 1))
  done
  wait "$pid" 2>/dev/null; rc=$?
fi

[[ $rc -eq 0 ]] && exit 0

{
  # 124 = `timeout` fired; 137/143 = the child took KILL/TERM from either path.
  if [[ $rc -eq 124 || $rc -eq 137 || $rc -eq 143 ]]; then
    echo "verify-gate: '$VERIFY' timed out after ${TIMEOUT}s."
  else
    echo "verify-gate: '$VERIFY' is failing, so the work is not done."
  fi
  echo "Fix it before stopping. Last 40 lines:"
  echo "---"
  tail -40 "$log"
} >&2
exit 2
