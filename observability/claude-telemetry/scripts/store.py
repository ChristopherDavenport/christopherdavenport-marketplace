#!/usr/bin/env python3
"""SQLite store for local Claude Code telemetry.

    python3 store.py --init          # create/migrate the database
    python3 store.py --stats         # what is in it

One file, two writers, one reader:

    sink.py       OTLP/HTTP-JSON from live sessions   (going forward)
    backfill.py   ~/.claude/projects/**/*.jsonl       (retroactive)
    mcp.py        the query surface

Design notes that are not obvious
---------------------------------
**Two sources, one schema.** OTel and the transcripts describe the same events
with different fidelity and different blind spots, so rows carry a `source`
column and are deduplicated on natural keys rather than kept apart. OTel knows
`cost_usd` and attribution; transcripts know the real skill and agent names that
OTel redacts. Neither alone answers "what did this plugin cost me".

**Attribution is redacted in OTel.** Every non-official plugin reports as the
literal string `third-party` on `plugin.name`, `skill.name` and
`marketplace.name`. `plugin_id_hash` is stable and distinct per plugin, so
`plugin_alias` maps hash to real name and `api_requests.plugin_resolved` is the
column worth trusting. See doctor.py for building that map.

**WAL and busy_timeout are not optional here.** The sink writes on every export
interval while an MCP query may be reading, and the default journal mode turns
that into `database is locked`.

**Timestamps are stored as ISO-8601 UTC text**, not epoch. SQLite compares them
lexicographically, which is what makes `WHERE ts > ?` work without a conversion
on every row, and it keeps the DB readable with a plain sqlite3 shell.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB = Path(
    os.environ.get("CLAUDE_TELEMETRY_DB")
    or Path.home() / ".claude" / "telemetry" / "telemetry.db"
)

SCHEMA_VERSION = 1

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
) STRICT;

-- One row per API call. The money table.
CREATE TABLE IF NOT EXISTS api_requests (
    request_id       TEXT PRIMARY KEY,
    ts               TEXT NOT NULL,
    session_id       TEXT,
    model            TEXT,
    cost_usd         REAL,
    input_tokens     INTEGER,
    output_tokens    INTEGER,
    cache_read       INTEGER,
    cache_creation   INTEGER,
    duration_ms      INTEGER,
    query_source     TEXT,
    speed            TEXT,
    effort           TEXT,
    agent_name       TEXT,
    skill_name       TEXT,
    plugin_name      TEXT,
    marketplace_name TEXT,
    plugin_resolved  TEXT,
    mcp_server       TEXT,
    mcp_tool         TEXT,
    cwd              TEXT,
    git_branch       TEXT,
    source           TEXT NOT NULL
) STRICT;
CREATE INDEX IF NOT EXISTS ix_api_ts      ON api_requests(ts);
CREATE INDEX IF NOT EXISTS ix_api_session ON api_requests(session_id);
CREATE INDEX IF NOT EXISTS ix_api_model   ON api_requests(model);
CREATE INDEX IF NOT EXISTS ix_api_plugin  ON api_requests(plugin_resolved);

-- Audit surface: what the agent did, and who let it.
CREATE TABLE IF NOT EXISTS tool_calls (
    id              INTEGER PRIMARY KEY,
    ts              TEXT NOT NULL,
    session_id      TEXT,
    tool_use_id     TEXT,
    tool_name       TEXT,
    success         INTEGER,
    duration_ms     INTEGER,
    decision        TEXT,
    decision_source TEXT,
    error_type      TEXT,
    input_bytes     INTEGER,
    result_bytes    INTEGER,
    mcp_scope       TEXT,
    cwd             TEXT,
    source          TEXT NOT NULL,
    UNIQUE(tool_use_id, source)
) STRICT;
CREATE INDEX IF NOT EXISTS ix_tool_ts   ON tool_calls(ts);
CREATE INDEX IF NOT EXISTS ix_tool_name ON tool_calls(tool_name);
CREATE INDEX IF NOT EXISTS ix_tool_sess ON tool_calls(session_id);

-- Everything else OTel emits, kept generically so a new event name in a future
-- CLI release lands intact rather than being dropped on the floor.
-- UNIQUE across the whole tuple because backfill is re-run routinely and events
-- have no natural id. Without it a second import silently doubles the table.
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY,
    ts         TEXT NOT NULL,
    session_id TEXT,
    name       TEXT NOT NULL,
    attrs      TEXT NOT NULL,
    source     TEXT NOT NULL,
    UNIQUE(ts, session_id, name, attrs, source)
) STRICT;
CREATE INDEX IF NOT EXISTS ix_ev_ts   ON events(ts);
CREATE INDEX IF NOT EXISTS ix_ev_name ON events(name);
CREATE INDEX IF NOT EXISTS ix_ev_sess ON events(session_id);

CREATE TABLE IF NOT EXISTS spans (
    span_id     TEXT PRIMARY KEY,
    trace_id    TEXT NOT NULL,
    parent_id   TEXT,
    name        TEXT NOT NULL,
    ts          TEXT NOT NULL,
    duration_ms REAL,
    session_id  TEXT,
    attrs       TEXT NOT NULL
) STRICT;
CREATE INDEX IF NOT EXISTS ix_span_trace ON spans(trace_id);
CREATE INDEX IF NOT EXISTS ix_span_name  ON spans(name);
CREATE INDEX IF NOT EXISTS ix_span_ts    ON spans(ts);

CREATE TABLE IF NOT EXISTS metrics (
    id    INTEGER PRIMARY KEY,
    ts    TEXT NOT NULL,
    name  TEXT NOT NULL,
    value REAL,
    attrs TEXT NOT NULL
) STRICT;
CREATE INDEX IF NOT EXISTS ix_metric_name_ts ON metrics(name, ts);

-- Sessions, assembled from whichever source saw them.
CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    started_at  TEXT,
    ended_at    TEXT,
    cwd         TEXT,
    git_branch  TEXT,
    entrypoint  TEXT,
    app_version TEXT,
    source      TEXT NOT NULL
) STRICT;
CREATE INDEX IF NOT EXISTS ix_sess_started ON sessions(started_at);

-- plugin_loaded, one row per (plugin, session). The raw material for the
-- hash -> real-name map, because OTel will not tell us the name directly.
CREATE TABLE IF NOT EXISTS plugin_loads (
    id             INTEGER PRIMARY KEY,
    ts             TEXT NOT NULL,
    session_id     TEXT,
    plugin_id_hash TEXT,
    plugin_name    TEXT,
    marketplace    TEXT,
    scope          TEXT,
    version        TEXT,
    skill_count    INTEGER,
    agent_count    INTEGER,
    command_count  INTEGER,
    has_hooks      INTEGER,
    has_mcp        INTEGER,
    UNIQUE(session_id, plugin_id_hash)
) STRICT;
CREATE INDEX IF NOT EXISTS ix_pl_hash ON plugin_loads(plugin_id_hash);

-- Hook executions. Promoted out of `events` to a table of its own because
-- `num_errors` is the single highest-value signal in the whole store and it
-- needs to be cheap to query.
--
-- Per the hooks contract, a hook exiting non-zero with anything other than 2 is
-- a *non-blocking error*: the tool call proceeds. So a hook can be failing on
-- every single invocation while the session looks completely normal. That is
-- how two of the three guardrails hooks ran for two merged PRs without ever
-- executing — found here, by `num_errors > 0`, not by any test.
CREATE TABLE IF NOT EXISTS hook_runs (
    id            INTEGER PRIMARY KEY,
    ts            TEXT NOT NULL,
    session_id    TEXT,
    prompt_id     TEXT,
    hook_event    TEXT,
    hook_name     TEXT,
    hook_source   TEXT,
    num_hooks     INTEGER,
    num_success   INTEGER,
    num_blocking  INTEGER,
    num_errors    INTEGER,
    num_cancelled INTEGER,
    duration_ms   INTEGER,
    UNIQUE(ts, session_id, hook_name)
) STRICT;
CREATE INDEX IF NOT EXISTS ix_hook_ts     ON hook_runs(ts);
CREATE INDEX IF NOT EXISTS ix_hook_errors ON hook_runs(num_errors);
CREATE INDEX IF NOT EXISTS ix_hook_name   ON hook_runs(hook_name);

-- The de-anonymisation map. Hand-built or inferred; see doctor.py.
CREATE TABLE IF NOT EXISTS plugin_alias (
    plugin_id_hash TEXT PRIMARY KEY,
    plugin_name    TEXT NOT NULL,
    marketplace    TEXT,
    confidence     TEXT NOT NULL,
    noted_at       TEXT
) STRICT;
"""


def connect(db_path: Path | None = None, *, readonly: bool = False,
            multithread: bool = False) -> sqlite3.Connection:
    """Open the store.

    multithread=True is for sink.py, whose ThreadingHTTPServer hands each request
    to a fresh thread. sqlite3 would otherwise refuse the connection outright;
    the sink serialises every write behind its own lock instead.
    """
    path = Path(db_path or DEFAULT_DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    if readonly and path.exists():
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=10,
                               check_same_thread=not multithread)
    else:
        conn = sqlite3.connect(path, timeout=10, check_same_thread=not multithread)
    conn.row_factory = sqlite3.Row
    # WAL lets the MCP reader work while the sink is mid-write; without
    # busy_timeout a concurrent export surfaces as "database is locked".
    if not readonly:
        conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def init(db_path: Path | None = None) -> sqlite3.Connection:
    conn = connect(db_path)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO meta(key, value) VALUES('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
    return conn


def stats(conn: sqlite3.Connection) -> dict:
    out = {}
    for table in ("api_requests", "tool_calls", "events", "spans", "metrics",
                  "sessions", "plugin_loads", "plugin_alias", "hook_runs"):
        out[table] = conn.execute(f"SELECT count(*) c FROM {table}").fetchone()["c"]
    row = conn.execute(
        "SELECT min(ts) lo, max(ts) hi, sum(cost_usd) cost FROM api_requests"
    ).fetchone()
    out["_range"] = (row["lo"], row["hi"])
    out["_cost_usd"] = row["cost"] or 0.0
    out["_by_source"] = {
        r["source"]: r["c"]
        for r in conn.execute(
            "SELECT source, count(*) c FROM api_requests GROUP BY source"
        )
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    if args.init:
        conn = init(args.db)
        print(f"initialised {args.db or DEFAULT_DB} (schema v{SCHEMA_VERSION})")
        conn.close()
        return 0

    if args.stats:
        path = Path(args.db or DEFAULT_DB)
        if not path.exists():
            print(f"no database at {path} — run --init", file=sys.stderr)
            return 1
        conn = connect(path, readonly=True)
        s = stats(conn)
        for k, v in s.items():
            if not k.startswith("_"):
                print(f"  {k:<16}{v:>10,}")
        lo, hi = s["_range"]
        print(f"\n  range     {lo or '—'}  ..  {hi or '—'}")
        print(f"  cost      ${s['_cost_usd']:.4f}")
        print(f"  by source {json.dumps(s['_by_source'])}")
        conn.close()
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
