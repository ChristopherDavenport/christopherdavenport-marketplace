#!/bin/bash
# Assertion-based eval for the guardrails plugin.
#
#   ./evals/guardrails/run.sh              # run the suite
#   ./evals/guardrails/run.sh --mutate     # prove the suite can fail
#
# Two parts, both deterministic and free -- crafted payloads in, exit codes
# out. No model, no tokens, no network, so this runs on every change rather
# than on a funded sweep.
#
#   1. escapes.py   the hook, fed PreToolUse payloads
#   2. templates    the policy templates the sandbox-policy skill ships,
#                   which are now the plugin's actual product
#
# --mutate is not a convenience. A guardrail suite that cannot fail is not
# testing anything, and that failure is invisible: a green run looks the same
# whether the hook works or is absent. This replaces the hook with one that
# always allows and confirms every deny case goes red.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN="$(cd "$HERE/../../safety/guardrails" && pwd)"
HOOK="$PLUGIN/scripts/escapes.py"
CASES="$HERE/cases.json"

command -v jq >/dev/null || { echo "FATAL: jq required" >&2; exit 70; }
command -v python3 >/dev/null || { echo "FATAL: python3 required" >&2; exit 70; }

MUTATE=0
[[ "${1:-}" == "--mutate" ]] && MUTATE=1

# Temp project root, and a sibling that is deliberately outside it.
SANDBOX="$(mktemp -d -t guardrails-eval)"
PROJECT="$SANDBOX/project"
OUTSIDE="$SANDBOX/outside"
mkdir -p "$PROJECT/src" "$OUTSIDE"
BACKUP="$(mktemp -t guardrails-hook)"
trap 'rm -rf "$SANDBOX"; [[ $MUTATE -eq 1 ]] && cp "$BACKUP" "$HOOK" 2>/dev/null; rm -f "$BACKUP" 2>/dev/null' EXIT

if [[ $MUTATE -eq 1 ]]; then
  cp "$HOOK" "$BACKUP"
  printf '#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n' > "$HOOK"
  echo "MUTATION MODE: hook replaced with an always-allow stub."
  echo "Every deny case must now FAIL. If they pass, the suite is vacuous."
  echo
fi

echo "  hook: escapes.py"
echo

pass=0; fail=0; failed=()
n=$(jq '.cases | length' "$CASES")

for i in $(seq 0 $((n - 1))); do
  id=$(jq -r ".cases[$i].id" "$CASES")
  expect=$(jq -r ".cases[$i].expect" "$CASES")
  why=$(jq -r ".cases[$i].why" "$CASES")
  payload=$(jq -c --arg c "$PROJECT" \
    ".cases[$i].payload // empty | if type==\"object\" then . + {cwd:\$c} else . end" \
    "$CASES" | sed "s|@PROJECT@|$PROJECT|g; s|@OUTSIDE@|$OUTSIDE|g")

  out=$(printf '%s' "$payload" | CLAUDE_PROJECT_DIR="$PROJECT" python3 "$HOOK" 2>&1)
  rc=$?

  ok=0
  if [[ "$expect" == "deny" ]]; then
    # Only exit 2 blocks. Any other non-zero is a "non-blocking error" per the
    # hooks contract, i.e. the call proceeds -- an escape wearing a crash.
    [[ $rc -eq 2 ]] && ok=1
  else
    [[ $rc -eq 0 ]] && ok=1
  fi

  if [[ $MUTATE -eq 1 && "$expect" == "deny" ]]; then
    # Under mutation a deny case SHOULD fail; that is the pass condition.
    [[ $ok -eq 0 ]] && ok=1 || ok=0
  fi

  if [[ $ok -eq 1 ]]; then
    pass=$((pass + 1)); printf '  \033[32mPASS\033[0m  %-32s %s\n' "$id" "$why"
  else
    fail=$((fail + 1)); failed+=("$id")
    printf '  \033[31mFAIL\033[0m  %-32s %s\n' "$id" "$why"
    [[ -n "$out" ]] && echo "        rc=$rc ${out:0:120}" >&2
  fi
done

echo
echo "  hook: $pass passed, $fail failed (of $n)"

# Template validation is skipped under mutation -- it does not exercise the
# hook, so its result would be identical either way and reporting it twice
# implies coverage the mutation run does not have.
tfail=0
if [[ $MUTATE -eq 0 ]]; then
  echo
  echo "  templates: sandbox-policy/references/templates.md"
  python3 "$HERE/validate_templates.py" || tfail=1
fi

echo
if [[ $fail -gt 0 || $tfail -ne 0 ]]; then
  [[ $fail -gt 0 ]] && echo "  failed: ${failed[*]}" >&2
  exit 1
fi
[[ $MUTATE -eq 1 ]] && echo "  Suite correctly detects a neutered hook." \
                    || echo "  Escape hatches guarded, templates sound."
