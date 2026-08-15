#!/usr/bin/env python3
"""Local OTLP/HTTP-JSON receiver: Claude Code telemetry straight into SQLite.

    python3 sink.py                      # listen on 127.0.0.1:4318
    python3 sink.py --port 4318 --verbose

Point Claude Code at it:

    CLAUDE_CODE_ENABLE_TELEMETRY=1
    CLAUDE_CODE_ENHANCED_TELEMETRY_BETA=1      # traces; beta, off by default
    OTEL_METRICS_EXPORTER=otlp
    OTEL_LOGS_EXPORTER=otlp
    OTEL_TRACES_EXPORTER=otlp
    OTEL_EXPORTER_OTLP_PROTOCOL=http/json      # no default — must be set
    OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318

No collector, no protobuf, no Docker. `http/json` means the payloads arrive as
plain JSON, so the whole receiver is stdlib. Verified end to end: metrics, logs
and traces all land.

Two things about the data that shape what is stored
---------------------------------------------------
**Cost only exists here.** `claude_code.api_request` carries `cost_usd` and the
full cache split. Transcripts carry exact tokens but no cost, so this is the
only source that can answer a dollar question.

**Attribution is redacted.** `plugin.name`, `skill.name` and `marketplace.name`
report the literal string `third-party` for every non-official plugin. The
`plugin_id_hash` on `plugin_loaded` is stable and distinct per plugin, so it is
kept as the join key; `plugin_alias` turns it back into a name. Do not trust
`api_requests.plugin_name` for private plugins — use `plugin_resolved`.

Binds to loopback only. Telemetry contains prompts and tool inputs when the
content flags are on, and this process does no authentication whatsoever.
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import store

_LOCK = threading.Lock()


def attr_value(v: dict):
    """Unwrap an OTLP AnyValue."""
    if not isinstance(v, dict):
        return v
    for k in ("stringValue", "boolValue"):
        if k in v:
            return v[k]
    for k in ("intValue", "doubleValue"):
        if k in v:
            try:
                return int(v[k]) if k == "intValue" else float(v[k])
            except (TypeError, ValueError):
                return v[k]
    if "arrayValue" in v:
        return [attr_value(x) for x in v["arrayValue"].get("values", [])]
    if "kvlistValue" in v:
        return {x["key"]: attr_value(x["value"]) for x in v["kvlistValue"].get("values", [])}
    return None


def attrs_of(obj: dict) -> dict:
    return {a["key"]: attr_value(a.get("value", {})) for a in obj.get("attributes", [])}


def iso(nano) -> str:
    try:
        return datetime.fromtimestamp(int(nano) / 1e9, timezone.utc).isoformat(
            timespec="milliseconds").replace("+00:00", "Z")
    except (TypeError, ValueError):
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def as_int(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def as_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


UPSERT_API = """
INSERT INTO api_requests (
    request_id, ts, session_id, model, cost_usd,
    input_tokens, output_tokens, cache_read, cache_creation,
    duration_ms, query_source, speed, effort,
    agent_name, skill_name, plugin_name, marketplace_name, plugin_resolved,
    mcp_server, mcp_tool, cwd, git_branch, source
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(request_id) DO UPDATE SET
    cost_usd       = COALESCE(excluded.cost_usd, api_requests.cost_usd),
    duration_ms    = COALESCE(excluded.duration_ms, api_requests.duration_ms),
    query_source   = COALESCE(excluded.query_source, api_requests.query_source),
    speed          = COALESCE(excluded.speed, api_requests.speed),
    effort         = COALESCE(excluded.effort, api_requests.effort),
    agent_name     = COALESCE(excluded.agent_name, api_requests.agent_name),
    skill_name     = COALESCE(excluded.skill_name, api_requests.skill_name),
    plugin_name    = COALESCE(excluded.plugin_name, api_requests.plugin_name),
    input_tokens   = COALESCE(api_requests.input_tokens, excluded.input_tokens),
    output_tokens  = COALESCE(api_requests.output_tokens, excluded.output_tokens),
    cache_read     = COALESCE(api_requests.cache_read, excluded.cache_read),
    cache_creation = COALESCE(api_requests.cache_creation, excluded.cache_creation),
    source         = CASE WHEN api_requests.source = excluded.source
                          THEN api_requests.source ELSE 'otel+transcript' END
"""

UPSERT_TOOL = """
INSERT INTO tool_calls
 (ts, session_id, tool_use_id, tool_name, success, duration_ms, decision,
  decision_source, error_type, input_bytes, result_bytes, mcp_scope, cwd, source)
VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(tool_use_id, source) DO UPDATE SET
    success         = COALESCE(excluded.success, tool_calls.success),
    duration_ms     = COALESCE(excluded.duration_ms, tool_calls.duration_ms),
    decision        = COALESCE(excluded.decision, tool_calls.decision),
    decision_source = COALESCE(excluded.decision_source, tool_calls.decision_source),
    error_type      = COALESCE(excluded.error_type, tool_calls.error_type),
    input_bytes     = COALESCE(excluded.input_bytes, tool_calls.input_bytes),
    result_bytes    = COALESCE(excluded.result_bytes, tool_calls.result_bytes)
"""


def resolve_plugin(conn, a: dict) -> str | None:
    """Real plugin name, if we can get one.

    OTel gives `third-party` for anything not in the official marketplace, so a
    literal match on that string is worthless. Fall back to the alias table
    keyed on plugin_id_hash when one is present.
    """
    name = a.get("plugin.name")
    if name and name != "third-party":
        return name
    h = a.get("plugin_id_hash")
    if h:
        row = conn.execute(
            "SELECT plugin_name FROM plugin_alias WHERE plugin_id_hash=?", (h,)
        ).fetchone()
        if row:
            return row["plugin_name"]
    return None


def handle_logs(conn, payload: dict) -> int:
    n = 0
    for rl in payload.get("resourceLogs", []):
        for sl in rl.get("scopeLogs", []):
            for rec in sl.get("logRecords", []):
                a = attrs_of(rec)
                name = a.get("event.name") or "unknown"
                ts = a.get("event.timestamp") or iso(rec.get("timeUnixNano"))
                sid = a.get("session.id")
                n += 1

                if name == "api_request":
                    conn.execute(UPSERT_API, (
                        a.get("request_id") or f"otel:{ts}:{a.get('event.sequence')}",
                        ts, sid, a.get("model"), as_float(a.get("cost_usd")),
                        as_int(a.get("input_tokens")), as_int(a.get("output_tokens")),
                        as_int(a.get("cache_read_tokens")), as_int(a.get("cache_creation_tokens")),
                        as_int(a.get("duration_ms")), a.get("query_source"),
                        a.get("speed"), a.get("effort"),
                        a.get("agent.name"), a.get("skill.name"), a.get("plugin.name"),
                        a.get("marketplace.name"), resolve_plugin(conn, a),
                        a.get("mcp_server.name"), a.get("mcp_tool.name"),
                        None, None, "otel",
                    ))
                elif name in ("tool_result", "tool_decision"):
                    tid = a.get("tool_use_id")
                    if tid:
                        conn.execute(UPSERT_TOOL, (
                            ts, sid, tid, a.get("tool_name"),
                            1 if str(a.get("success")).lower() == "true"
                            else (0 if a.get("success") is not None else None),
                            as_int(a.get("duration_ms")),
                            a.get("decision"), a.get("source") or a.get("decision_source"),
                            a.get("error_type"),
                            as_int(a.get("tool_input_size_bytes")),
                            as_int(a.get("tool_result_size_bytes")),
                            a.get("mcp_server_scope"), None, "otel",
                        ))
                elif name == "hook_execution_complete":
                    # num_non_blocking_error is the reason this gets a table.
                    # A hook erroring on every call is invisible in a session:
                    # the contract says the tool proceeds anyway.
                    conn.execute(
                        "INSERT OR IGNORE INTO hook_runs (ts, session_id, prompt_id,"
                        " hook_event, hook_name, hook_source, num_hooks, num_success,"
                        " num_blocking, num_errors, num_cancelled, duration_ms)"
                        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (ts, sid, a.get("prompt.id"), a.get("hook_event"),
                         a.get("hook_name"), a.get("hook_source"),
                         as_int(a.get("num_hooks")), as_int(a.get("num_success")),
                         as_int(a.get("num_blocking")),
                         as_int(a.get("num_non_blocking_error")),
                         as_int(a.get("num_cancelled")),
                         as_int(a.get("total_duration_ms"))),
                    )
                elif name == "plugin_loaded":
                    conn.execute(
                        "INSERT OR IGNORE INTO plugin_loads (ts, session_id, plugin_id_hash,"
                        " plugin_name, marketplace, scope, version, skill_count, agent_count,"
                        " command_count, has_hooks, has_mcp) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (ts, sid, a.get("plugin_id_hash"), a.get("plugin.name"),
                         a.get("marketplace.name"), a.get("plugin.scope"), a.get("plugin.version"),
                         as_int(a.get("skill_path_count")), as_int(a.get("agent_path_count")),
                         as_int(a.get("command_path_count")),
                         1 if a.get("has_hooks") in (True, "true") else 0,
                         1 if a.get("has_mcp") in (True, "true") else 0),
                    )

                # Everything lands in events too, including the three above:
                # the typed tables are projections, and a future CLI release
                # adding an attribute should not lose it.
                conn.execute(
                    "INSERT OR IGNORE INTO events (ts, session_id, name, attrs, source)"
                    " VALUES (?,?,?,?,?)",
                    (ts, sid, name, json.dumps(a, sort_keys=True, default=str), "otel"),
                )

                if sid:
                    conn.execute(
                        "INSERT INTO sessions (session_id, started_at, ended_at, cwd,"
                        " git_branch, entrypoint, app_version, source) VALUES (?,?,?,?,?,?,?,?)"
                        " ON CONFLICT(session_id) DO UPDATE SET"
                        "  started_at = MIN(sessions.started_at, excluded.started_at),"
                        "  ended_at   = MAX(sessions.ended_at, excluded.ended_at)",
                        (sid, ts, ts, None, None, a.get("app.entrypoint"),
                         a.get("app.version"), "otel"),
                    )
    return n


def handle_metrics(conn, payload: dict) -> int:
    n = 0
    for rm in payload.get("resourceMetrics", []):
        for sm in rm.get("scopeMetrics", []):
            for m in sm.get("metrics", []):
                body = m.get("sum") or m.get("gauge") or m.get("histogram") or {}
                for p in body.get("dataPoints", []):
                    a = attrs_of(p)
                    val = p.get("asDouble", p.get("asInt", p.get("sum")))
                    conn.execute(
                        "INSERT INTO metrics (ts, name, value, attrs) VALUES (?,?,?,?)",
                        (iso(p.get("timeUnixNano") or p.get("startTimeUnixNano")),
                         m.get("name", "unknown"), as_float(val),
                         json.dumps(a, sort_keys=True, default=str)),
                    )
                    n += 1
    return n


def handle_traces(conn, payload: dict) -> int:
    n = 0
    for rs in payload.get("resourceSpans", []):
        for ss in rs.get("scopeSpans", []):
            for sp in ss.get("spans", []):
                a = attrs_of(sp)
                start, end = sp.get("startTimeUnixNano"), sp.get("endTimeUnixNano")
                dur = None
                try:
                    dur = (int(end) - int(start)) / 1e6
                except (TypeError, ValueError):
                    pass
                conn.execute(
                    "INSERT OR IGNORE INTO spans (span_id, trace_id, parent_id, name, ts,"
                    " duration_ms, session_id, attrs) VALUES (?,?,?,?,?,?,?,?)",
                    (sp.get("spanId"), sp.get("traceId"), sp.get("parentSpanId") or None,
                     sp.get("name", "unknown"), iso(start), dur, a.get("session.id"),
                     json.dumps(a, sort_keys=True, default=str)),
                )
                n += 1
    return n


HANDLERS = {"metrics": handle_metrics, "logs": handle_logs, "traces": handle_traces}


def make_handler(conn, verbose: bool):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_POST(self):
            signal = self.path.rsplit("/", 1)[-1]
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            if self.headers.get("Content-Encoding") == "gzip":
                try:
                    raw = gzip.decompress(raw)
                except OSError:
                    pass

            written = 0
            try:
                # Claude Code opens with a 2-byte probe sent as
                # x-www-form-urlencoded; treat anything unparseable as a no-op
                # rather than a failure, or the exporter backs off.
                payload = json.loads(raw) if raw.strip() else {}
                fn = HANDLERS.get(signal)
                if fn and payload:
                    with _LOCK:
                        written = fn(conn, payload)
                        conn.commit()
            except Exception as exc:
                if verbose:
                    print(f"  ! {signal}: {exc}", file=sys.stderr, flush=True)

            if verbose and written:
                print(f"  {signal:<8} {written:>4} rows  ({len(raw)}B)", flush=True)

            body = b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):  # silence the default access log
            pass

    return Handler


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=4318)
    ap.add_argument("--db", default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    store.init(args.db).close()
    # ThreadingHTTPServer hands each request to a new thread, so the connection
    # has to allow it; _LOCK is what actually serialises the writes.
    conn = store.connect(args.db, multithread=True)

    srv = ThreadingHTTPServer((args.host, args.port), make_handler(conn, args.verbose))
    print(f"listening on http://{args.host}:{args.port}  ->  {store.DEFAULT_DB if not args.db else args.db}")
    print("  POST /v1/metrics  /v1/logs  /v1/traces")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        conn.commit()
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
