#!/usr/bin/env python3
"""Emit a synthetic Claude Code transcript covering the cases the suite asserts.

Synthetic rather than a copy of a real transcript for three reasons: real ones
carry prompts and absolute paths that should not land in a repo, they differ per
machine so the suite would not be reproducible, and they do not reliably contain
the edge cases worth pinning (an all-zero usage record, a tool call with no
result, a repeated requestId).
"""

import json
import sys

TS = "2026-08-15T12:00:0{}.000Z"
SID = "11111111-2222-3333-4444-555555555555"


def rec(**kw):
    base = {"sessionId": SID, "cwd": "/tmp/demo", "gitBranch": "main",
            "version": "2.1.233", "userType": "external", "isSidechain": False}
    base.update(kw)
    return base


def assistant(i, rid, usage, content=None):
    return rec(type="assistant", uuid=f"a{i}", timestamp=TS.format(i), requestId=rid,
               message={"id": f"msg_{i}", "model": "claude-opus-5", "role": "assistant",
                        "usage": usage, "content": content or []})


def usage(inp=10, out=20, cr=0, cc=0):
    return {"input_tokens": inp, "output_tokens": out,
            "cache_read_input_tokens": cr, "cache_creation_input_tokens": cc}


def main() -> int:
    out = []

    # A plain request.
    out.append(assistant(0, "req_a", usage(100, 50, 0, 200)))

    # The same requestId twice with identical usage: must collapse to one row.
    out.append(assistant(1, "req_dup", usage(5, 5)))
    out.append(assistant(2, "req_dup", usage(5, 5)))

    # An all-zero usage record: not an accounting, must be skipped entirely.
    out.append(assistant(3, "req_zero", usage(0, 0, 0, 0)))

    # A tool call that completes.
    out.append(assistant(4, "req_tool", usage(7, 7), [
        {"type": "tool_use", "id": "toolu_ok", "name": "Bash",
         "input": {"command": "echo hi"}}]))
    out.append(rec(type="user", uuid="u4", timestamp=TS.format(5),
                   message={"role": "user", "content": [
                       {"type": "tool_result", "tool_use_id": "toolu_ok",
                        "content": "hi", "is_error": False}]}))

    # A tool call that errors.
    out.append(assistant(6, "req_err", usage(3, 3), [
        {"type": "tool_use", "id": "toolu_err", "name": "Read",
         "input": {"file_path": "/nope"}}]))
    out.append(rec(type="user", uuid="u6", timestamp=TS.format(7),
                   message={"role": "user", "content": [
                       {"type": "tool_result", "tool_use_id": "toolu_err",
                        "content": "ENOENT", "is_error": True}]}))

    # A tool call with no result: the session ended mid-flight.
    out.append(assistant(8, "req_orphan", usage(2, 2), [
        {"type": "tool_use", "id": "toolu_orphan", "name": "Bash",
         "input": {"command": "sleep 999"}}]))

    # Skill and Agent invocations: the un-redacted attribution OTel will not give.
    out.append(assistant(9, "req_skill", usage(4, 4), [
        {"type": "tool_use", "id": "toolu_skill", "name": "Skill",
         "input": {"skill": "demo-skill"}},
        {"type": "tool_use", "id": "toolu_agent", "name": "Agent",
         "input": {"subagent_type": "demo-agent", "prompt": "x"}}]))

    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        for r in out:
            fh.write(json.dumps(r) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
