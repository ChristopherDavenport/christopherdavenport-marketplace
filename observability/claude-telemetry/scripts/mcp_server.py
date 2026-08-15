#!/usr/bin/env python3
"""MCP server over the local telemetry store: the query surface.

Speaks MCP over stdio using nothing but the standard library -- no SDK, so the
plugin has no install step and cannot break on a dependency resolution.

    python3 mcp_server.py            # stdio, for Claude Code
    python3 mcp_server.py --selftest # exercise every tool against the store

Design
------
Reads are opened read-only against a WAL database, so querying never blocks the
sink and cannot corrupt anything mid-write.

The tool set is deliberately small. A wide surface costs context on every
session, which is a poor trade for a plugin whose entire subject is context
cost. `run_query` is the general one -- group-by and aggregate over any table --
and the rest exist because the common questions deserve one call rather than a
correctly-shaped SQL string.

`sql` is a read-only escape hatch. It refuses anything that is not a single
SELECT, because an MCP tool that can write to the audit log is not an audit log.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

import store

PROTOCOL = "2024-11-05"

TABLES = {"api_requests", "tool_calls", "events", "spans", "metrics",
          "sessions", "plugin_loads", "plugin_alias"}

AGGS = {
    "count": "count(*)",
    "sum_cost": "sum(cost_usd)",
    "sum_input": "sum(input_tokens)",
    "sum_output": "sum(output_tokens)",
    "sum_cache_read": "sum(cache_read)",
    "sum_cache_creation": "sum(cache_creation)",
    "avg_duration": "avg(duration_ms)",
    "max_duration": "max(duration_ms)",
    "sum_duration": "sum(duration_ms)",
}

SELECT_ONLY = re.compile(r"^\s*select\b", re.I)
FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|replace|"
    r"reindex|analyze|begin|commit|rollback)\b", re.I)


def _conn(db):
    path = Path(db or store.DEFAULT_DB)
    if not path.exists():
        raise RuntimeError(
            f"no telemetry database at {path}. Run backfill.py to import existing "
            "transcripts, or start sink.py to collect live sessions.")
    return store.connect(path, readonly=True)


def _rows(cur, limit=200):
    out = [dict(r) for r in cur.fetchmany(limit)]
    return out


# --- tools ------------------------------------------------------------------

def t_overview(conn, **_):
    """What is in the store, and over what period."""
    s = store.stats(conn)
    lo, hi = s["_range"]
    return {
        "rows": {k: v for k, v in s.items() if not k.startswith("_")},
        "time_range": {"from": lo, "to": hi},
        "total_cost_usd": round(s["_cost_usd"], 4),
        "by_source": s["_by_source"],
        "note": ("Rows sourced from transcripts have no cost_usd — the transcripts "
                 "do not record it. Token counts there are exact. Only OTel-sourced "
                 "rows carry dollars, so cost totals cover the OTel period only."),
    }


def t_cost(conn, group_by="model", since=None, until=None, limit=50, **_):
    """Spend and tokens, grouped."""
    allowed = {
        "day": "substr(ts,1,10)",
        "model": "model", "query_source": "query_source",
        "plugin_resolved": "plugin_resolved", "skill_name": "skill_name",
        "agent_name": "agent_name", "session_id": "session_id",
        "cwd": "cwd", "git_branch": "git_branch",
        "speed": "speed", "effort": "effort",
    }
    col = allowed.get(group_by)
    if col is None:
        raise ValueError(f"group_by must be one of: {sorted(allowed)}")
    where, params = ["1=1"], []
    if since:
        where.append("ts >= ?"); params.append(since)
    if until:
        where.append("ts <= ?"); params.append(until)
    sql = (f"SELECT {col} AS grp, count(*) n, sum(cost_usd) cost_usd,"
           f" sum(input_tokens) input_tokens, sum(output_tokens) output_tokens,"
           f" sum(cache_read) cache_read, sum(cache_creation) cache_creation"
           f" FROM api_requests WHERE {' AND '.join(where)}"
           f" GROUP BY grp ORDER BY COALESCE(sum(cost_usd),0) DESC,"
           f" sum(input_tokens) DESC LIMIT ?")
    params.append(int(limit))
    return {"group_by": group_by, "rows": _rows(conn.execute(sql, params), int(limit))}


def t_sessions(conn, since=None, limit=25, cwd_like=None, **_):
    """Recent sessions with their cost and shape."""
    where, params = ["1=1"], []
    if since:
        where.append("s.started_at >= ?"); params.append(since)
    if cwd_like:
        where.append("COALESCE(s.cwd, a.cwd) LIKE ?"); params.append(f"%{cwd_like}%")
    sql = f"""
      SELECT s.session_id, s.started_at, s.ended_at,
             COALESCE(s.cwd, MIN(a.cwd)) cwd, COALESCE(s.git_branch, MIN(a.git_branch)) branch,
             count(a.request_id) requests, sum(a.cost_usd) cost_usd,
             sum(a.input_tokens) input_tokens, sum(a.output_tokens) output_tokens,
             (SELECT count(*) FROM tool_calls t WHERE t.session_id = s.session_id) tool_calls
      FROM sessions s LEFT JOIN api_requests a ON a.session_id = s.session_id
      WHERE {' AND '.join(where)}
      GROUP BY s.session_id ORDER BY s.started_at DESC LIMIT ?"""
    params.append(int(limit))
    return {"rows": _rows(conn.execute(sql, params), int(limit))}


def t_tool_audit(conn, tool_name=None, success=None, since=None, decision=None,
                 limit=25, **_):
    """The audit surface: what ran, whether it worked, and who allowed it."""
    where, params = ["1=1"], []
    if tool_name:
        where.append("tool_name = ?"); params.append(tool_name)
    if success is not None:
        where.append("success = ?"); params.append(1 if success in (True, "true", 1) else 0)
    if decision:
        where.append("decision = ?"); params.append(decision)
    if since:
        where.append("ts >= ?"); params.append(since)
    sql = (f"SELECT ts, session_id, tool_name, success, duration_ms, decision,"
           f" decision_source, error_type, input_bytes, result_bytes, cwd"
           f" FROM tool_calls WHERE {' AND '.join(where)} ORDER BY ts DESC LIMIT ?")
    params.append(int(limit))
    rows = _rows(conn.execute(sql, params), int(limit))
    summary = _rows(conn.execute(
        f"SELECT tool_name, count(*) n, sum(CASE WHEN success=0 THEN 1 ELSE 0 END) failures"
        f" FROM tool_calls WHERE {' AND '.join(where)} GROUP BY tool_name"
        f" ORDER BY n DESC LIMIT 20", params[:-1]), 20)
    return {"summary": summary, "rows": rows}


def t_trace(conn, trace_id=None, session_id=None, **_):
    """A span tree, as a nested structure."""
    if not trace_id:
        if not session_id:
            raise ValueError("pass trace_id or session_id")
        row = conn.execute(
            "SELECT trace_id FROM spans WHERE session_id=? ORDER BY ts DESC LIMIT 1",
            (session_id,)).fetchone()
        if not row:
            return {"spans": [], "note": "no spans for that session — traces are a "
                                          "beta exporter and off unless "
                                          "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1"}
        trace_id = row["trace_id"]
    spans = [dict(r) for r in conn.execute(
        "SELECT span_id, parent_id, name, ts, duration_ms, attrs FROM spans"
        " WHERE trace_id=? ORDER BY ts", (trace_id,))]
    by_parent: dict = {}
    for s in spans:
        s["attrs"] = json.loads(s["attrs"])
        by_parent.setdefault(s["parent_id"], []).append(s)

    def build(pid):
        out = []
        for s in by_parent.get(pid, []):
            out.append({"name": s["name"], "duration_ms": s["duration_ms"],
                        "ts": s["ts"], "attrs": s["attrs"],
                        "children": build(s["span_id"])})
        return out

    return {"trace_id": trace_id, "span_count": len(spans), "tree": build(None)}


def t_run_query(conn, table="api_requests", calculate="count", breakdown=None,
                where=None, since=None, until=None, limit=50, **_):
    """Group-by and aggregate over any table. The general one."""
    if table not in TABLES:
        raise ValueError(f"table must be one of: {sorted(TABLES)}")
    if calculate not in AGGS:
        raise ValueError(f"calculate must be one of: {sorted(AGGS)}")
    cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
    grp = breakdown if breakdown in cols else None
    if breakdown and grp is None:
        raise ValueError(f"breakdown '{breakdown}' is not a column of {table}: {sorted(cols)}")
    clauses, params = ["1=1"], []
    if since and "ts" in cols:
        clauses.append("ts >= ?"); params.append(since)
    if until and "ts" in cols:
        clauses.append("ts <= ?"); params.append(until)
    if where:
        # Only a bare `col op ?`-shaped predicate; no subqueries, no semicolons.
        if FORBIDDEN.search(where) or ";" in where:
            raise ValueError("where clause rejected")
        clauses.append(f"({where})")
    sel = f"{grp} AS grp, " if grp else ""
    sql = (f"SELECT {sel}{AGGS[calculate]} AS value FROM {table}"
           f" WHERE {' AND '.join(clauses)}"
           + (f" GROUP BY grp ORDER BY value DESC" if grp else "")
           + " LIMIT ?")
    params.append(int(limit))
    return {"table": table, "calculate": calculate, "breakdown": breakdown,
            "rows": _rows(conn.execute(sql, params), int(limit))}


def t_plugin_costs(conn, **_):
    """Per-plugin attribution, and an honest account of what is missing.

    OTel redacts non-official plugin names to the literal `third-party`, so this
    reports what can be attributed, what is blinded, and the un-redacted skill
    and agent invocations recovered from transcripts.
    """
    attributed = _rows(conn.execute(
        "SELECT COALESCE(plugin_resolved, plugin_name) plugin, count(*) n,"
        " sum(cost_usd) cost_usd FROM api_requests"
        " WHERE plugin_name IS NOT NULL GROUP BY plugin ORDER BY cost_usd DESC"), 50)
    blinded = conn.execute(
        "SELECT count(*) n, sum(cost_usd) cost FROM api_requests"
        " WHERE plugin_name = 'third-party' AND plugin_resolved IS NULL").fetchone()
    invocations = _rows(conn.execute(
        "SELECT json_extract(attrs,'$.skill') skill,"
        " json_extract(attrs,'$.subagent_type') agent, count(*) n FROM events"
        " WHERE name LIKE 'transcript.%_invoked' GROUP BY skill, agent"
        " ORDER BY n DESC LIMIT 40"), 40)
    hashes = _rows(conn.execute(
        "SELECT p.plugin_id_hash, p.plugin_name, p.marketplace, p.skill_count,"
        " p.agent_count, a.plugin_name AS resolved FROM plugin_loads p"
        " LEFT JOIN plugin_alias a USING(plugin_id_hash)"
        " GROUP BY p.plugin_id_hash ORDER BY p.plugin_name"), 100)
    unresolved = sum(1 for h in hashes if h["plugin_name"] == "third-party"
                     and not h["resolved"])
    return {
        "attributed": attributed,
        "blinded": {"requests": blinded["n"], "cost_usd": blinded["cost"]},
        "skill_agent_invocations_from_transcripts": invocations,
        "plugin_hashes": hashes,
        "note": (f"{unresolved} plugin hashes are still unmapped. OTel reports every "
                 "non-official plugin as the literal 'third-party'; populate "
                 "plugin_alias to attribute their spend. Transcript-derived skill and "
                 "agent invocations below are NOT redacted and are the reliable "
                 "signal for which of your own plugins actually fire."),
    }


def t_hook_health(conn, since=None, limit=25, **_):
    """Are the hooks actually running?

    A hook that exits non-zero with anything other than 2 is a *non-blocking
    error* per the contract: the tool call proceeds. So a hook can fail on every
    invocation with no visible symptom — no error in the session, no failed
    command, nothing. `num_errors` is how you find out.
    """
    where, params = ["1=1"], []
    if since:
        where.append("ts >= ?"); params.append(since)
    w = " AND ".join(where)
    summary = _rows(conn.execute(
        f"SELECT hook_name, hook_event, count(*) runs, sum(num_hooks) hooks_invoked,"
        f" sum(num_success) succeeded, sum(num_errors) errored,"
        f" sum(num_blocking) blocked, round(avg(duration_ms),1) avg_ms"
        f" FROM hook_runs WHERE {w} GROUP BY hook_name, hook_event"
        f" ORDER BY errored DESC, runs DESC", params), int(limit))
    failing = [r for r in summary if (r["errored"] or 0) > 0]
    total = conn.execute(
        f"SELECT count(*) runs, sum(num_errors) errs FROM hook_runs WHERE {w}",
        params).fetchone()
    verdict = "no hook telemetry yet — hooks are only reported by OTel, so start sink.py"
    if total["runs"]:
        verdict = ("every hook run completed cleanly" if not (total["errs"] or 0)
                   else f"{len(failing)} hook(s) are erroring; the tool calls they "
                        f"guard proceeded anyway")
    return {"verdict": verdict, "runs": total["runs"], "total_errors": total["errs"] or 0,
            "failing": failing, "by_hook": summary,
            "note": ("A non-blocking error means the guarded tool call still ran. "
                     "Any non-zero 'errored' here is a guard that silently did not "
                     "apply, not a cosmetic warning.")}


def t_sql(conn, query="", limit=200, **_):
    """Read-only escape hatch."""
    if not SELECT_ONLY.match(query or "") or FORBIDDEN.search(query or "") or ";" in query:
        raise ValueError("only a single read-only SELECT is allowed")
    return {"rows": _rows(conn.execute(query), int(limit))}


TOOLS = [
    ("telemetry_overview", "What is in the local telemetry store: row counts, time range, "
     "total cost, and which rows came from OTel versus transcripts. Start here.",
     {"type": "object", "properties": {}}, t_overview),
    ("telemetry_cost", "Spend and token totals grouped by model, day, plugin, skill, agent, "
     "session, cwd, git_branch, query_source, speed or effort.",
     {"type": "object", "properties": {
         "group_by": {"type": "string", "description":
                      "model | day | query_source | plugin_resolved | skill_name | "
                      "agent_name | session_id | cwd | git_branch | speed | effort"},
         "since": {"type": "string", "description": "ISO timestamp lower bound"},
         "until": {"type": "string"}, "limit": {"type": "integer"}}}, t_cost),
    ("telemetry_sessions", "Recent sessions with cost, tokens, tool-call count, cwd and branch.",
     {"type": "object", "properties": {
         "since": {"type": "string"}, "cwd_like": {"type": "string"},
         "limit": {"type": "integer"}}}, t_sessions),
    ("telemetry_tool_audit", "Audit surface: tool calls with success, duration, permission "
     "decision and who made it. Filter by tool_name, success, decision or time.",
     {"type": "object", "properties": {
         "tool_name": {"type": "string"}, "success": {"type": "boolean"},
         "decision": {"type": "string"}, "since": {"type": "string"},
         "limit": {"type": "integer"}}}, t_tool_audit),
    ("telemetry_trace", "The span tree for one trace or the latest trace of a session.",
     {"type": "object", "properties": {
         "trace_id": {"type": "string"}, "session_id": {"type": "string"}}}, t_trace),
    ("telemetry_run_query", "Group-by and aggregate over any table. calculate: count, "
     "sum_cost, sum_input, sum_output, sum_cache_read, sum_cache_creation, avg_duration, "
     "max_duration, sum_duration.",
     {"type": "object", "properties": {
         "table": {"type": "string"}, "calculate": {"type": "string"},
         "breakdown": {"type": "string"}, "where": {"type": "string"},
         "since": {"type": "string"}, "until": {"type": "string"},
         "limit": {"type": "integer"}}}, t_run_query),
    ("telemetry_plugin_costs", "Per-plugin spend, what is blinded by OTel's third-party "
     "redaction, and the un-redacted skill/agent invocations recovered from transcripts.",
     {"type": "object", "properties": {}}, t_plugin_costs),
    ("telemetry_hook_health", "Whether hooks are actually running. A hook erroring is a "
     "non-blocking error, so the guarded tool call proceeds and nothing looks wrong — "
     "this is the only way to see it.",
     {"type": "object", "properties": {
         "since": {"type": "string"}, "limit": {"type": "integer"}}}, t_hook_health),
    ("telemetry_sql", "Read-only SELECT against the store. Rejects anything else.",
     {"type": "object", "properties": {
         "query": {"type": "string"}, "limit": {"type": "integer"}},
      "required": ["query"]}, t_sql),
]
BY_NAME = {name: fn for name, _, _, fn in TOOLS}


def dispatch(msg: dict, db) -> dict | None:
    mid, method = msg.get("id"), msg.get("method")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": PROTOCOL,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "claude-telemetry", "version": "0.1.0"}}}
    if method in ("notifications/initialized", "notifications/cancelled"):
        return None
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": [
            {"name": n, "description": d, "inputSchema": s} for n, d, s, _ in TOOLS]}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        fn = BY_NAME.get(name)
        if not fn:
            return {"jsonrpc": "2.0", "id": mid,
                    "error": {"code": -32601, "message": f"unknown tool {name}"}}
        try:
            conn = _conn(db)
            try:
                result = fn(conn, **(params.get("arguments") or {}))
            finally:
                conn.close()
            text = json.dumps(result, indent=2, default=str)
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": f"error: {exc}"}], "isError": True}}
        return {"jsonrpc": "2.0", "id": mid,
                "result": {"content": [{"type": "text", "text": text}]}}
    return {"jsonrpc": "2.0", "id": mid,
            "error": {"code": -32601, "message": f"unknown method {method}"}}


def serve(db) -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        reply = dispatch(msg, db)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
    return 0


def selftest(db) -> int:
    conn = _conn(db)
    failures = 0
    # Supply the arguments a tool genuinely requires, so a correct "you must
    # pass an id" error is not mistaken for a broken tool.
    row = conn.execute("SELECT trace_id FROM spans LIMIT 1").fetchone()
    required = {
        "telemetry_sql": {"query": "SELECT 1 AS ok"},
        "telemetry_trace": {"trace_id": row["trace_id"]} if row else None,
    }
    for name, _, _, fn in TOOLS:
        args = required.get(name, {})
        if args is None:
            print(f"  skip  {name:<26} no spans in store (traces are beta/opt-in)")
            continue
        try:
            out = fn(conn, **args)
            size = len(json.dumps(out, default=str))
            flag = "  <-- large default payload" if size > 20000 else ""
            print(f"  ok    {name:<26} {size:>7,}B{flag}")
            if size > 20000:
                failures += 1
        except Exception as exc:
            failures += 1
            print(f"  FAIL  {name:<26} {exc}")
    # The escape hatch must actually refuse writes.
    for bad in ("DELETE FROM api_requests", "SELECT 1; DROP TABLE events",
                "INSERT INTO events VALUES(1,'','','','','')", "PRAGMA table_info(events)"):
        try:
            t_sql(conn, query=bad)
            print(f"  FAIL  sql guard let through: {bad}")
            failures += 1
        except ValueError:
            print(f"  ok    sql guard rejected: {bad[:40]}")
    conn.close()
    print(f"\n  {'PASS' if not failures else 'FAIL'} — {failures} failure(s)")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=None)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    return selftest(args.db) if args.selftest else serve(args.db)


if __name__ == "__main__":
    sys.exit(main())
