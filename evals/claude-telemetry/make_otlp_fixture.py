#!/usr/bin/env python3
"""Emit an OTLP/HTTP-JSON logs payload covering the events the sink projects.

Hook, cost and permission telemetry exist only in OTel — a transcript never
carries them — so the transcript fixture cannot reach that code. This is the
payload shape Claude Code actually sends, captured from a live session and
reduced to the cases worth asserting.

Includes one hook run that errors, because that is the case the whole hook_runs
table exists for and the one that shipped undetected in guardrails.
"""

import json
import sys


def kv(d):
    out = []
    for k, v in d.items():
        if isinstance(v, bool):
            out.append({"key": k, "value": {"boolValue": v}})
        elif isinstance(v, int):
            out.append({"key": k, "value": {"intValue": str(v)}})
        elif isinstance(v, float):
            out.append({"key": k, "value": {"doubleValue": v}})
        else:
            out.append({"key": k, "value": {"stringValue": str(v)}})
    return out


SID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
BASE = {"session.id": SID, "app.version": "2.1.233"}


def ev(name, ts, **attrs):
    return {"timeUnixNano": "1755280000000000000",
            "attributes": kv({**BASE, "event.name": name, "event.timestamp": ts, **attrs})}


def main() -> int:
    records = [
        # Cost — the field transcripts do not have.
        ev("api_request", "2026-08-15T12:00:00.000Z", model="claude-opus-5",
           cost_usd=0.0421, input_tokens=12, output_tokens=340,
           cache_read_tokens=51000, cache_creation_tokens=1200,
           duration_ms=2100, request_id="req_otel_1", query_source="main"),

        # A permission decision — also OTel-only.
        ev("tool_decision", "2026-08-15T12:00:01.000Z", tool_name="Bash",
           tool_use_id="toolu_otel_1", decision="accept", source="config",
           tool_source="builtin"),
        ev("tool_result", "2026-08-15T12:00:02.000Z", tool_name="Bash",
           tool_use_id="toolu_otel_1", success="true", duration_ms=1500,
           tool_input_size_bytes=40, tool_result_size_bytes=8),

        # A clean hook run.
        ev("hook_execution_complete", "2026-08-15T12:00:03.000Z",
           hook_event="PreToolUse", hook_name="PreToolUse:Read", hook_source="merged",
           num_hooks=1, num_success=1, num_blocking=0, num_non_blocking_error=0,
           num_cancelled=0, total_duration_ms=12),

        # THE case: a hook erroring. The guarded call proceeded anyway.
        ev("hook_execution_complete", "2026-08-15T12:00:04.000Z",
           hook_event="PreToolUse", hook_name="PreToolUse:Bash", hook_source="merged",
           num_hooks=2, num_success=1, num_blocking=0, num_non_blocking_error=1,
           num_cancelled=0, total_duration_ms=80),

        # A Stop hook that never succeeded at all.
        ev("hook_execution_complete", "2026-08-15T12:00:05.000Z",
           hook_event="Stop", hook_name="Stop", hook_source="merged",
           num_hooks=1, num_success=0, num_blocking=0, num_non_blocking_error=1,
           num_cancelled=0, total_duration_ms=25),

        # Redacted third-party plugin: the attribution blind spot.
        ev("plugin_loaded", "2026-08-15T12:00:06.000Z", **{
            "plugin.name": "third-party", "marketplace.name": "third-party",
            "plugin.scope": "user-local", "plugin_id_hash": "deadbeefcafe0001",
            "skill_path_count": 1, "agent_path_count": 0,
            "has_hooks": False, "has_mcp": False}),
    ]

    payload = {"resourceLogs": [{"scopeLogs": [{"logRecords": records}]}]}
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
