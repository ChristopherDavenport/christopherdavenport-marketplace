#!/usr/bin/env python3
"""Import existing Claude Code transcripts into the telemetry store.

    python3 backfill.py                     # ~/.claude/projects
    python3 backfill.py --root DIR --since 2026-07-01
    python3 backfill.py --dry-run

Why bother when the sink exists
-------------------------------
The sink only sees sessions that happen after it is running. The transcripts are
already on disk and cover months, so importing them means the store answers
questions on day one instead of after a fortnight of accumulation.

They also see something OTel cannot. OTel redacts every third-party plugin and
skill to the literal string `third-party`; transcripts record the actual `Skill`
and `Agent` tool calls with real names. For attributing spend to *your own*
plugins, the transcripts are the un-redacted source.

What they lack
--------------
**No cost.** Transcripts carry exact token counts but no `cost_usd` -- that is
computed server-side and only OTel reports it. Rows imported here leave
`cost_usd` NULL rather than guessing from a price table that would silently rot.
Token counts are exact and are the honest basis for comparison; `store.py
--stats` breaks rows down by source so the gap is visible rather than assumed
away.

Where both sources describe the same request the row is merged, not duplicated:
whichever arrives second fills NULLs via COALESCE without clobbering what is
already there, and `source` becomes `otel+transcript`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import store

UPSERT_API = """
INSERT INTO api_requests (
    request_id, ts, session_id, model, cost_usd,
    input_tokens, output_tokens, cache_read, cache_creation,
    duration_ms, query_source, speed, effort,
    agent_name, skill_name, plugin_name, marketplace_name, plugin_resolved,
    mcp_server, mcp_tool, cwd, git_branch, source
) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
ON CONFLICT(request_id) DO UPDATE SET
    ts             = COALESCE(api_requests.ts, excluded.ts),
    session_id     = COALESCE(api_requests.session_id, excluded.session_id),
    model          = COALESCE(api_requests.model, excluded.model),
    cost_usd       = COALESCE(api_requests.cost_usd, excluded.cost_usd),
    input_tokens   = COALESCE(api_requests.input_tokens, excluded.input_tokens),
    output_tokens  = COALESCE(api_requests.output_tokens, excluded.output_tokens),
    cache_read     = COALESCE(api_requests.cache_read, excluded.cache_read),
    cache_creation = COALESCE(api_requests.cache_creation, excluded.cache_creation),
    cwd            = COALESCE(api_requests.cwd, excluded.cwd),
    git_branch     = COALESCE(api_requests.git_branch, excluded.git_branch),
    source         = CASE WHEN api_requests.source = excluded.source
                          THEN api_requests.source
                          ELSE 'otel+transcript' END
"""


def iter_records(path: Path):
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue  # a partially-flushed final line is normal on a live session


def blocks(message: dict) -> list:
    content = message.get("content")
    return content if isinstance(content, list) else []


def import_file(conn, path: Path, since: str | None, dry: bool) -> dict:
    counts = {"api": 0, "tools": 0, "sessions": 0, "skills": 0}
    session_seen: dict[str, dict] = {}
    pending_tools: dict[str, dict] = {}

    for rec in iter_records(path):
        ts = rec.get("timestamp")
        if not ts or (since and ts < since):
            continue
        sid = rec.get("sessionId")
        rtype = rec.get("type")

        if sid and sid not in session_seen:
            session_seen[sid] = {
                "started": ts, "ended": ts,
                "cwd": rec.get("cwd"), "branch": rec.get("gitBranch"),
                "entrypoint": rec.get("entrypoint"), "version": rec.get("version"),
            }
        elif sid:
            session_seen[sid]["ended"] = max(session_seen[sid]["ended"], ts)

        if rtype == "assistant":
            msg = rec.get("message") or {}
            usage = msg.get("usage") or {}
            # A requestId legitimately repeats across records — one API call can
            # produce several assistant records, and 3510 of 3511 repeats in the
            # local corpus carry byte-identical usage, so collapsing to one row
            # loses nothing. The exception is a real accounting followed by
            # all-zero rows; those zeros are not a measurement, and taking
            # whichever landed first would silently undercount that request.
            if usage and not any((usage.get(k) or 0) for k in (
                    "input_tokens", "output_tokens",
                    "cache_read_input_tokens", "cache_creation_input_tokens")):
                usage = {}
            # A handful of records carry usage but no requestId. Falling back to
            # the record uuid keeps them rather than dropping them on the floor.
            rid = rec.get("requestId") or (f"uuid:{rec['uuid']}" if rec.get("uuid") else None)
            if rid and usage:
                if not dry:
                    conn.execute(UPSERT_API, (
                        rid, ts, sid, msg.get("model"), None,
                        usage.get("input_tokens"), usage.get("output_tokens"),
                        usage.get("cache_read_input_tokens"),
                        usage.get("cache_creation_input_tokens"),
                        None, "subagent" if rec.get("isSidechain") else "main",
                        usage.get("speed"), None,
                        None, None, None, None, None, None, None,
                        rec.get("cwd"), rec.get("gitBranch"), "transcript",
                    ))
                counts["api"] += 1

            for b in blocks(msg):
                if not isinstance(b, dict) or b.get("type") != "tool_use":
                    continue
                inp = b.get("input") or {}
                pending_tools[b.get("id")] = {
                    "ts": ts, "sid": sid, "name": b.get("name"),
                    "bytes": len(json.dumps(inp)), "cwd": rec.get("cwd"),
                }
                # Skill/Agent invocations are the un-redacted attribution OTel
                # will not give us; keep them as events for the resolver.
                if b.get("name") in ("Skill", "Agent") and not dry:
                    conn.execute(
                        "INSERT OR IGNORE INTO events(ts, session_id, name, attrs, source) "
                        "VALUES (?,?,?,?,?)",
                        (ts, sid, f"transcript.{b['name'].lower()}_invoked",
                         json.dumps({
                             "skill": inp.get("skill"),
                             "subagent_type": inp.get("subagent_type"),
                             "cwd": rec.get("cwd"),
                         }), "transcript"),
                    )
                    counts["skills"] += 1

        elif rtype == "user":
            for b in blocks(rec.get("message") or {}):
                if not isinstance(b, dict) or b.get("type") != "tool_result":
                    continue
                tid = b.get("tool_use_id")
                info = pending_tools.pop(tid, None)
                if not info:
                    continue
                body = b.get("content")
                size = len(body if isinstance(body, str) else json.dumps(body or ""))
                if not dry:
                    conn.execute(
                        "INSERT OR IGNORE INTO tool_calls "
                        "(ts, session_id, tool_use_id, tool_name, success, duration_ms,"
                        " decision, decision_source, error_type, input_bytes, result_bytes,"
                        " mcp_scope, cwd, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (info["ts"], info["sid"], tid, info["name"],
                         0 if b.get("is_error") else 1, None, None, None,
                         "error" if b.get("is_error") else None,
                         info["bytes"], size, None, info["cwd"], "transcript"),
                    )
                counts["tools"] += 1

    # Tool calls with no matching result: the session ended mid-flight, or the
    # result was filtered. Record them rather than dropping — an unanswered tool
    # call is exactly the shape of an audit question.
    for tid, info in pending_tools.items():
        if not dry:
            conn.execute(
                "INSERT OR IGNORE INTO tool_calls "
                "(ts, session_id, tool_use_id, tool_name, success, duration_ms,"
                " decision, decision_source, error_type, input_bytes, result_bytes,"
                " mcp_scope, cwd, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (info["ts"], info["sid"], tid, info["name"], None, None, None, None,
                 "no_result", info["bytes"], None, None, info["cwd"], "transcript"),
            )
        counts["tools"] += 1

    for sid, s in session_seen.items():
        if not dry:
            conn.execute(
                "INSERT INTO sessions(session_id, started_at, ended_at, cwd, git_branch,"
                " entrypoint, app_version, source) VALUES (?,?,?,?,?,?,?,?) "
                "ON CONFLICT(session_id) DO UPDATE SET "
                " started_at = MIN(sessions.started_at, excluded.started_at),"
                " ended_at   = MAX(sessions.ended_at,   excluded.ended_at),"
                " cwd        = COALESCE(sessions.cwd, excluded.cwd),"
                " git_branch = COALESCE(sessions.git_branch, excluded.git_branch)",
                (sid, s["started"], s["ended"], s["cwd"], s["branch"],
                 s["entrypoint"], s["version"], "transcript"),
            )
        counts["sessions"] += 1

    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=Path.home() / ".claude" / "projects")
    ap.add_argument("--db", type=Path, default=None)
    ap.add_argument("--since", help="ISO date; skip records older than this")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    if not args.root.is_dir():
        print(f"no transcript root at {args.root}", file=sys.stderr)
        return 1

    conn = store.init(args.db)
    files = sorted(args.root.rglob("*.jsonl"))
    total = {"api": 0, "tools": 0, "sessions": 0, "skills": 0}

    for i, path in enumerate(files, 1):
        try:
            c = import_file(conn, path, args.since, args.dry_run)
        except Exception as exc:  # one bad transcript must not abort the import
            print(f"  skipped {path.name}: {exc}", file=sys.stderr)
            continue
        for k in total:
            total[k] += c[k]
        if not args.dry_run and i % 25 == 0:
            conn.commit()
        if not args.quiet and i % 100 == 0:
            print(f"  {i}/{len(files)} files…", file=sys.stderr)

    if not args.dry_run:
        conn.commit()

    print(f"{'would import' if args.dry_run else 'imported'} from {len(files)} transcripts:")
    print(f"  api_requests  {total['api']:>8,}")
    print(f"  tool_calls    {total['tools']:>8,}")
    print(f"  sessions      {total['sessions']:>8,}")
    print(f"  skill/agent   {total['skills']:>8,}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
