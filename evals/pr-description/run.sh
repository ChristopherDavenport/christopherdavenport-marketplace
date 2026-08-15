#!/bin/bash
# Assertion-based eval for the pr-description plugin.
#
#   ./evals/pr-description/run.sh              # run the suite
#   ./evals/pr-description/run.sh --mutate     # prove the suite can fail
#
# The plugin's load-bearing artifact is scripts/density.py, which turns a PR
# body into a decision: within budget, or not. That is assertable directly --
# bodies in, exit codes and failure sets out. No model, no tokens, no network,
# so this runs on every change rather than on a funded sweep.
#
# Cases assert the failure *set*, not just the exit code. A case that trips the
# wrong metric still exits non-zero, and would otherwise read as covered.
#
# --mutate replaces the scorer with one that always reports "within budget" and
# confirms every failure case goes red. A scoring suite that cannot fail is not
# testing anything, and the failure is invisible: a green run looks identical
# whether the scorer works or waves everything through.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN="$(cd "$HERE/../../workflow/pr-description" && pwd)"
SCORER="$PLUGIN/skills/pr-description/scripts/density.py"
CASES="$HERE/cases.json"

command -v jq >/dev/null || { echo "FATAL: jq required" >&2; exit 70; }
command -v python3 >/dev/null || { echo "FATAL: python3 required" >&2; exit 70; }
[[ -f "$SCORER" ]] || { echo "FATAL: scorer not found at $SCORER" >&2; exit 70; }

MUTATE=0
[[ "${1:-}" == "--mutate" ]] && MUTATE=1

BACKUP="$(mktemp "${TMPDIR:-/tmp}/prdesc-scorer.XXXXXX")" || BACKUP=""
# BSD-only spelling; GNU returns empty, and an empty BACKUP means --mutate
# cannot restore the scorer it stubs.
[[ -n "$BACKUP" ]] || { echo "FATAL: could not create a temp file" >&2; exit 70; }
trap '[[ $MUTATE -eq 1 ]] && cp "$BACKUP" "$SCORER" 2>/dev/null; rm -f "$BACKUP" 2>/dev/null' EXIT

if [[ $MUTATE -eq 1 ]]; then
  cp "$SCORER" "$BACKUP"
  # Still emits parseable JSON -- the interesting mutation is a scorer that
  # runs and approves, not one that crashes. A crash would be caught by any
  # case; a permissive scorer is caught only by this mode.
  cat > "$SCORER" <<'STUB'
#!/usr/bin/env python3
import json, sys
sys.stdin.read()
print(json.dumps({"tier": "normal", "metrics": {}, "failures": []}))
sys.exit(0)
STUB
  echo "MUTATION MODE: scorer replaced with an always-within-budget stub."
  echo "Every failure case must now FAIL. If they pass, the suite is vacuous."
  echo
fi

echo "  scorer: density.py"
echo

pass=0; fail=0; failed=()
n=$(jq '.cases | length' "$CASES")

for i in $(seq 0 $((n - 1))); do
  id=$(jq -r ".cases[$i].id" "$CASES")
  expect=$(jq -r ".cases[$i].expect" "$CASES")
  why=$(jq -r ".cases[$i].why" "$CASES")
  cl=$(jq -r ".cases[$i].changed_lines // empty" "$CASES")
  want=$(jq -r ".cases[$i].fails // [] | sort | join(\",\")" "$CASES")

  args=(--json)
  [[ -n "$cl" ]] && args+=(--changed-lines "$cl")

  out=$(jq -r ".cases[$i].body" "$CASES" | python3 "$SCORER" "${args[@]}" 2>&1)

  if ! got_json=$(printf '%s' "$out" | jq -e . 2>/dev/null); then
    fail=$((fail + 1)); failed+=("$id")
    printf '  \033[31mFAIL\033[0m  %-34s %s\n' "$id" "scorer emitted no JSON"
    echo "        ${out:0:160}" >&2
    continue
  fi

  # A metric name is the first token of each failure message.
  keys=$(printf '%s' "$got_json" | jq -r '[.failures[] | split(" ")[0]] | sort | join(",")')
  verdict=$([[ -z "$keys" ]] && echo pass || echo fail)

  ok=0
  if [[ "$verdict" == "$expect" ]]; then
    # On a failure case, the metric set must match exactly.
    if [[ "$expect" == "fail" && -n "$want" ]]; then
      [[ "$keys" == "$want" ]] && ok=1
    else
      ok=1
    fi
  fi

  if [[ $MUTATE -eq 1 && "$expect" == "fail" ]]; then
    # Under mutation a failure case SHOULD stop failing; that is the pass condition.
    [[ $ok -eq 0 ]] && ok=1 || ok=0
  fi

  if [[ $ok -eq 1 ]]; then
    pass=$((pass + 1)); printf '  \033[32mPASS\033[0m  %-34s %s\n' "$id" "$why"
  else
    fail=$((fail + 1)); failed+=("$id")
    printf '  \033[31mFAIL\033[0m  %-34s %s\n' "$id" "$why"
    printf '        expected %s[%s], got %s[%s]\n' "$expect" "$want" "$verdict" "$keys" >&2
  fi
done

echo
echo "  scorer: $pass passed, $fail failed (of $n)"
echo

if [[ $fail -gt 0 ]]; then
  echo "  failed: ${failed[*]}" >&2
  exit 1
fi
[[ $MUTATE -eq 1 ]] && echo "  Suite correctly detects a scorer that waves everything through." \
                    || echo "  Budget enforced at every cap and on both sides of each boundary."
