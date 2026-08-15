#!/bin/bash
# Assertion-based eval for the claude-telemetry plugin.
#
#   ./evals/claude-telemetry/run.sh              # run the suite
#   ./evals/claude-telemetry/run.sh --mutate     # prove the suite can fail
#
# Builds a store from synthetic fixtures, then asserts on it. Deterministic and
# free: no model, no network, and no dependency on the operator's real
# ~/.claude/projects, which would make results differ per machine and leak
# private paths into CI logs.
#
# --mutate replaces the read-only SQL guard with one that permits everything and
# asserts the guard cases go red. An MCP tool that can write to the audit log is
# not an audit log, and a guard nobody tests is the same as no guard.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN="$(cd "$HERE/../../observability/claude-telemetry" && pwd)"
SCRIPTS="$PLUGIN/scripts"

command -v python3 >/dev/null || { echo "FATAL: python3 required" >&2; exit 70; }

MUTATE=0
[[ "${1:-}" == "--mutate" ]] && MUTATE=1

# `mktemp -t foo` is a BSD/macOS spelling; GNU coreutils rejects a template with
# no X's, returns empty, and the script then happily writes to /. Caught only in
# CI, because it works fine on the machine this was written on. Use the explicit
# XXXXXX form, which both accept, and refuse to continue if it still fails.
WORK="$(mktemp -d "${TMPDIR:-/tmp}/claude-telemetry-eval.XXXXXX")" || WORK=""
BACKUP="$(mktemp "${TMPDIR:-/tmp}/ct-mcp.XXXXXX")" || BACKUP=""
if [[ -z "$WORK" || ! -d "$WORK" || -z "$BACKUP" ]]; then
  echo "FATAL: could not create a temp workspace" >&2; exit 70
fi
DB="$WORK/t.db"
trap 'rm -rf "$WORK"; [[ $MUTATE -eq 1 ]] && cp "$BACKUP" "$SCRIPTS/mcp_server.py" 2>/dev/null; rm -f "$BACKUP" 2>/dev/null' EXIT

if [[ $MUTATE -eq 1 ]]; then
  cp "$SCRIPTS/mcp_server.py" "$BACKUP"
  python3 - "$SCRIPTS/mcp_server.py" <<'PY'
import re, sys
p = sys.argv[1]; t = open(p).read()
# Neuter the guard: every query is now accepted.
t = t.replace(
    'if not SELECT_ONLY.match(query or "") or FORBIDDEN.search(query or "") or ";" in query:',
    'if False:')
open(p, "w").write(t)
PY
  echo "MUTATION MODE: the read-only SQL guard now permits everything."
  echo "Every guard case must now FAIL. If they pass, the suite is vacuous."
  echo
fi

pass=0; fail=0; failed=()
check() { # check <name> <0|1 ok>
  if [[ "$2" -eq 1 ]]; then
    pass=$((pass+1)); printf '  \033[32mPASS\033[0m  %s\n' "$1"
  else
    fail=$((fail+1)); failed+=("$1"); printf '  \033[31mFAIL\033[0m  %s\n' "$1"
  fi
}

# --- build a synthetic corpus ------------------------------------------------
mkdir -p "$WORK/projects/-tmp-demo"
python3 "$HERE/make_fixture.py" "$WORK/projects/-tmp-demo/s1.jsonl" || {
  echo "FATAL: fixture generation failed" >&2; exit 70; }

export CLAUDE_TELEMETRY_DB="$DB"
# An exit code is 0-for-success; check() wants 1-for-ok. Converting rather than
# passing $? straight through, which reads fine and asserts the opposite.
if python3 "$SCRIPTS/backfill.py" --root "$WORK/projects" --db "$DB" --quiet >/dev/null 2>&1
then ok=1; else ok=0; fi
check "backfill imports a transcript" $ok

n1=$(python3 -c "import sqlite3;print(sqlite3.connect('$DB').execute('select count(*) from api_requests').fetchone()[0])")
[[ "$n1" -gt 0 ]] && check "api_requests populated ($n1)" 1 || check "api_requests populated" 0

# Idempotence is the property that makes re-running backfill safe, and it is
# easy to lose by adding a table without a natural key.
python3 "$SCRIPTS/backfill.py" --root "$WORK/projects" --db "$DB" --quiet >/dev/null 2>&1
n2=$(python3 -c "
import sqlite3
c=sqlite3.connect('$DB')
print('|'.join(str(c.execute(f'select count(*) from {t}').fetchone()[0]) for t in ('api_requests','tool_calls','events','sessions')))")
python3 "$SCRIPTS/backfill.py" --root "$WORK/projects" --db "$DB" --quiet >/dev/null 2>&1
n3=$(python3 -c "
import sqlite3
c=sqlite3.connect('$DB')
print('|'.join(str(c.execute(f'select count(*) from {t}').fetchone()[0]) for t in ('api_requests','tool_calls','events','sessions')))")
[[ "$n2" == "$n3" ]] && check "backfill is idempotent ($n3)" 1 || check "backfill is idempotent ($n2 -> $n3)" 0

# All-zero usage records are not accountings; importing them would undercount a
# request whose real numbers arrived on a sibling record.
zero=$(python3 -c "
import sqlite3
c=sqlite3.connect('$DB')
print(c.execute(\"select count(*) from api_requests where request_id='req_zero'\").fetchone()[0])")
[[ "$zero" -eq 0 ]] && check "all-zero usage records are skipped" 1 || check "all-zero usage records are skipped" 0

# A tool_use with no matching tool_result is an audit question, not noise.
orphan=$(python3 -c "
import sqlite3
c=sqlite3.connect('$DB')
print(c.execute(\"select count(*) from tool_calls where error_type='no_result'\").fetchone()[0])")
[[ "$orphan" -ge 1 ]] && check "unanswered tool calls are recorded" 1 || check "unanswered tool calls are recorded" 0

# Skill/Agent names survive from transcripts — the whole reason to read them.
skills=$(python3 -c "
import sqlite3
c=sqlite3.connect('$DB')
print(c.execute(\"select count(*) from events where name like 'transcript.%_invoked'\").fetchone()[0])")
[[ "$skills" -ge 1 ]] && check "un-redacted skill/agent invocations captured" 1 || check "un-redacted skill/agent invocations captured" 0

# --- OTel path ---------------------------------------------------------------
# Cost, permission decisions and hook outcomes exist only in OTel; a transcript
# never carries them, so the fixture above cannot reach this code at all.
python3 "$HERE/make_otlp_fixture.py" "$WORK/logs.json" || {
  echo "FATAL: OTLP fixture generation failed" >&2; exit 70; }
python3 - "$SCRIPTS" "$DB" "$WORK/logs.json" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[1])
import store, sink
conn = store.init(sys.argv[2])
sink.handle_logs(conn, json.load(open(sys.argv[3])))
conn.commit()
PY
ok=0; [[ $? -eq 0 ]] && ok=1
check "sink ingests an OTLP logs payload" $ok

cost=$(python3 -c "
import sqlite3
c=sqlite3.connect('$DB')
print(c.execute(\"select cost_usd from api_requests where request_id='req_otel_1'\").fetchone()[0])")
[[ "$cost" == "0.0421" ]] && check "cost_usd captured from OTel ($cost)" 1 || check "cost_usd captured from OTel (got $cost)" 0

dec=$(python3 -c "
import sqlite3
c=sqlite3.connect('$DB')
r=c.execute(\"select decision, decision_source from tool_calls where tool_use_id='toolu_otel_1'\").fetchone()
print('%s/%s' % r if r else 'none')")
[[ "$dec" == "accept/config" ]] && check "permission decision captured ($dec)" 1 || check "permission decision captured (got $dec)" 0

# The reason hook_runs exists: a hook erroring is invisible in a session,
# because the contract lets the guarded tool call proceed regardless.
errs=$(python3 -c "
import sqlite3
c=sqlite3.connect('$DB')
print(c.execute('select count(*) from hook_runs where num_errors > 0').fetchone()[0])")
[[ "$errs" -eq 2 ]] && check "failing hooks recorded ($errs)" 1 || check "failing hooks recorded (got $errs, want 2)" 0

verdict=$(python3 -c "
import sys; sys.path.insert(0,'$SCRIPTS')
import mcp_server, sqlite3
c=sqlite3.connect('file:$DB?mode=ro', uri=True); c.row_factory=sqlite3.Row
print('yes' if mcp_server.t_hook_health(c)['total_errors'] == 2 else 'no')")
[[ "$verdict" == "yes" ]] && check "hook_health surfaces the failures" 1 || check "hook_health surfaces the failures" 0

blinded=$(python3 -c "
import sqlite3
c=sqlite3.connect('$DB')
print(c.execute(\"select count(*) from plugin_loads where plugin_name='third-party'\").fetchone()[0])")
[[ "$blinded" -ge 1 ]] && check "third-party redaction recorded with its hash" 1 || check "third-party redaction recorded with its hash" 0

# --- MCP surface -------------------------------------------------------------
# Skipped under mutation: the server's own selftest asserts the guard too, so it
# would fail for the reason the mutation is deliberately creating, and reporting
# that as a suite failure would mask whether the guard cases inverted.
if [[ $MUTATE -eq 0 ]]; then
  out=$(python3 "$SCRIPTS/mcp_server.py" --db "$DB" --selftest 2>&1)
  echo "$out" | grep -q "PASS — 0 failure" && check "every MCP tool returns" 1 || {
    check "every MCP tool returns" 0; echo "$out" | grep FAIL | head -4 >&2; }
fi

# Protocol handshake: a server that cannot be initialised is not a server.
proto=$(printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | python3 "$SCRIPTS/mcp_server.py" --db "$DB" 2>/dev/null \
  | python3 -c "
import json,sys
ids=set(); tools=0
for line in sys.stdin:
    m=json.loads(line); ids.add(m.get('id'))
    if m.get('id')==2: tools=len(m['result']['tools'])
print('ok' if ids=={1,2} and tools>=8 else 'bad')")
[[ "$proto" == "ok" ]] && check "MCP handshake and tools/list" 1 || check "MCP handshake and tools/list" 0

# --- the read-only guard -----------------------------------------------------
for q in "DELETE FROM api_requests" \
         "SELECT 1; DROP TABLE events" \
         "INSERT INTO events VALUES(1,'a','b','c','d','e')" \
         "UPDATE api_requests SET cost_usd=0" \
         "PRAGMA table_info(events)" \
         "ATTACH DATABASE '/tmp/x' AS x"; do
  # Only a ValueError counts as the guard doing its job. sqlite raises on its
  # own for multi-statement input and for writes to a read-only handle, and
  # treating those as "rejected" would let a disabled guard still look green --
  # which is exactly what the first run of --mutate caught.
  rejected=$(python3 -c "
import sys; sys.path.insert(0,'$SCRIPTS')
import mcp_server, sqlite3
c=sqlite3.connect('file:$DB?mode=ro', uri=True); c.row_factory=sqlite3.Row
try:
    mcp_server.t_sql(c, query='''$q''')
    print('no')
except ValueError:
    print('yes')
except Exception as exc:
    print('no')  # sqlite stopped it, not the guard")
  ok=0; [[ "$rejected" == "yes" ]] && ok=1
  [[ $MUTATE -eq 1 ]] && { [[ $ok -eq 0 ]] && ok=1 || ok=0; }
  check "sql guard rejects: ${q:0:38}" $ok
done

echo
echo "  $pass passed, $fail failed"
echo
if [[ $fail -gt 0 ]]; then
  echo "  failed: ${failed[*]}" >&2
  exit 1
fi
[[ $MUTATE -eq 1 ]] && echo "  Suite correctly detects a disabled read-only guard." \
                    || echo "  Store, backfill, MCP surface and read-only guard all sound."
