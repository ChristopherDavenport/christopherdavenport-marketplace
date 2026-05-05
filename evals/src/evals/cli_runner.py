"""Subprocess wrapper around `claude --bare --print`.

Both the baseline and skill-loaded runs use `--bare` so they share the same
auth path (ANTHROPIC_API_KEY only) and skip hooks / auto-memory / CLAUDE.md
auto-discovery. The only difference between the two is the presence of
`--plugin-dir`, which loads the skill under test for that one invocation.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any


class ClaudeCliError(RuntimeError):
    pass


@dataclass
class CliResult:
    text: str
    cost_usd: float
    raw: dict[str, Any]


def run(prompt: str, plugin_dir: str | None, timeout: int = 300) -> CliResult:
    cmd = ["claude", "--bare", "--print", "--output-format", "json"]
    if plugin_dir is not None:
        cmd += ["--plugin-dir", plugin_dir]
    cmd.append(prompt)

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as e:
        raise ClaudeCliError(f"claude timed out after {timeout}s") from e

    if proc.returncode != 0:
        raise ClaudeCliError(
            f"claude exited {proc.returncode}\n"
            f"stderr: {proc.stderr[:1000]}\n"
            f"stdout: {proc.stdout[:500]}"
        )

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ClaudeCliError(
            f"could not parse claude json output: {e}\nstdout: {proc.stdout[:1000]}"
        ) from e

    text = data.get("result") or ""
    if not text:
        raise ClaudeCliError(f"claude returned empty result: {data}")

    cost = float(data.get("total_cost_usd") or 0.0)
    return CliResult(text=text, cost_usd=cost, raw=data)
