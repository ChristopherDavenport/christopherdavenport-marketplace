#!/usr/bin/env bash
# verify.sh -- the local mirror of .github/workflows/checks.yml.
#
# One command that means "this repo is green", so the same thing gates a push,
# a pull request, and an agent trying to declare itself done. The Stop hook in
# the guardrails plugin runs this via CLAUDE_GUARDRAILS_VERIFY (see
# .claude/settings.json) -- an agent may not stop on a red build.
#
# Everything here is deterministic and free: no model, no tokens, no network.
# The judge-based evals under evals/<plugin>/cases.yaml are deliberately NOT
# run -- they cost real money per case and are invoked by hand.
#
# Keep this in step with checks.yml. If the two drift, the gate is enforcing a
# different bar than CI and one of them is lying.

set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1

# Break the recursion before running anything. evals/guardrails/validate_hooks.py
# execs every hook script -- verify-gate.sh included -- with the ambient
# environment, to prove each one is runnable. When .claude/settings.json points
# CLAUDE_GUARDRAILS_VERIFY at this script, that exec re-enters here: verify.sh ->
# suite -> verify-gate.sh -> verify.sh, without bound.
#
# It does not look like a crash. It looks like a slow build, then a hung agent.
# Unsetting the variable restores exactly the behaviour the suite had before the
# gate was armed -- verify-gate.sh sees no command and exits 0 on its first line,
# which is the "is it runnable" answer the check is actually after.
unset CLAUDE_GUARDRAILS_VERIFY

fail=0
step() {
  local name="$1"; shift
  printf '\n=== %s ===\n' "$name"
  if "$@"; then
    return 0
  fi
  printf '!!! FAILED: %s\n' "$name"
  fail=1
}

# The generated-file gates regenerate in place and diff. CI runs on a throwaway
# checkout so it can leave the file dirty; here it would silently modify the
# working tree of whoever ran the gate -- including an agent that then commits
# it. Snapshot, compare, and always put the file back.
step_generated() {
  local name="$1" file="$2"; shift 2
  printf '\n=== %s ===\n' "$name"
  local before
  before=$(mktemp "${TMPDIR:-/tmp}/verify-gen.XXXXXX")
  cp "$file" "$before"
  if ! "$@" >/dev/null 2>&1; then
    printf '!!! FAILED: %s (generator errored)\n' "$name"
    cp "$before" "$file"; rm -f "$before"; fail=1; return
  fi
  if ! diff -q "$before" "$file" >/dev/null 2>&1; then
    printf '!!! FAILED: %s is stale. Run: %s\n' "$file" "$*"
    diff -u "$before" "$file" | head -40
    cp "$before" "$file"
    fail=1
  else
    printf '  %s up to date\n' "$file"
  fi
  rm -f "$before"
}

command -v jq      >/dev/null || { echo "jq missing";      exit 1; }
command -v python3 >/dev/null || { echo "python3 missing"; exit 1; }

# Flagged, not fatal. Adding eval cases is ordinary work and drift here is
# usually just an un-re-baselined manifest, so failing the Stop gate on it
# would punish normal development. CI enforces it; this line is so whoever --
# or whatever -- just edited a scorer finds out immediately rather than at
# review. See scripts/integrity.sh.
printf '\n=== integrity ===\n'
./scripts/integrity.sh || printf '  (not fatal here -- CI enforces it)\n'

step "guardrails — hooks, templates, manifests" ./evals/guardrails/run.sh
step "guardrails — mutation check"              ./evals/guardrails/run.sh --mutate
step "pr-description — scorer"                  ./evals/pr-description/run.sh
step "pr-description — mutation check"          ./evals/pr-description/run.sh --mutate
step "plugin context-cost budgets"              python3 scripts/plugin_costs.py --check

step_generated "COSTS.md is up to date"          COSTS.md \
  python3 scripts/plugin_costs.py --write
step_generated "marketplace.json cost stamps"    .claude-plugin/marketplace.json \
  python3 scripts/plugin_costs.py --sync

printf '\n'
if [[ $fail -ne 0 ]]; then
  echo "verify: RED"
  exit 1
fi
echo "verify: green"
