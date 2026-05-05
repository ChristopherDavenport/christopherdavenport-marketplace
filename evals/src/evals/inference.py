"""Inference backends for the eval harness.

Two backends, same interface:

- `sdk_run`  — direct Anthropic SDK call. Default model is Sonnet 4.6 with
  `temperature=0`; Haiku 4.5 also accepts `temperature=0`. Opus 4.7 *does
  not* accept the `temperature` parameter (the API rejects it as deprecated
  for that model), so opus runs are uncontrolled and noisier — flag them as
  indicators, not measurements. The plugin's SKILL.md content is stitched
  into the system prompt for the skill-loaded call.

- `cli_run` — subprocess wrapper around `claude --bare --print`. Exercises
  the actual `--plugin-dir` skill-discovery path end-to-end. Use via
  `--via-cli` for periodic integration checks. Ignores `model_alias`; the
  CLI picks its own model.

Both return the same `InferenceResult` shape so the runner is agnostic.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

INFERENCE_MAX_TOKENS = 8192

# Model alias → base name (matches what `claude --model X` accepts).
MODEL_BASE = {
    "haiku": "claude-haiku-4-5",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-7",
}

# Vertex publishes some models with a date stamp instead of @default.
# Empirical: opus-4-7 and sonnet-4-6 are at @default; haiku-4-5 is @20251001.
_VERTEX_SUFFIX = {
    "claude-haiku-4-5":  "@20251001",
    "claude-sonnet-4-6": "@default",
    "claude-opus-4-7":   "@default",
}

# Opus 4.7 rejects the `temperature` parameter as deprecated. Other models
# accept it. Maintaining this set is the cheapest way to keep the harness
# working as Anthropic adjusts which models support which sampling controls.
NO_TEMPERATURE = {"opus"}

# Approximate per-MTok pricing for cost reporting only. Public list prices.
_PRICING = {
    # base name → (input $/MTok, output $/MTok)
    "claude-haiku-4-5":  (1.00,  5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-7":  (15.00, 75.00),
}


class InferenceError(RuntimeError):
    pass


@dataclass
class InferenceResult:
    text: str
    cost_usd: float
    raw: dict[str, Any]


# ----- shared SDK client selection (mirrors judge._client) -----------------


def _sdk_client(model_base: str) -> tuple[object, str]:
    """Return (client, model_id) for the current provider env, formatted for `model_base`."""
    if os.environ.get("CLAUDE_CODE_USE_VERTEX") == "1":
        from anthropic import AnthropicVertex

        suffix = _VERTEX_SUFFIX.get(model_base, "@default")
        return AnthropicVertex(), f"{model_base}{suffix}"
    if os.environ.get("CLAUDE_CODE_USE_BEDROCK") == "1":
        from anthropic import AnthropicBedrock

        return AnthropicBedrock(), f"anthropic.{model_base}-v1:0"
    from anthropic import Anthropic

    if "ANTHROPIC_API_KEY" not in os.environ:
        raise InferenceError(
            "SDK backend needs auth: set CLAUDE_CODE_USE_VERTEX=1 (with "
            "ANTHROPIC_VERTEX_PROJECT_ID), CLAUDE_CODE_USE_BEDROCK=1, or "
            "ANTHROPIC_API_KEY."
        )
    return Anthropic(), model_base


# ----- SDK backend ---------------------------------------------------------


def find_skill_md(plugin_dir: Path) -> Path:
    """Locate the single SKILL.md inside a plugin directory.

    Convention across this marketplace: `<plugin_dir>/skills/<name>/SKILL.md`.
    Errors if zero or >1 are found — both indicate a non-conventional plugin
    that this harness can't safely auto-stitch.
    """
    matches = list(plugin_dir.glob("skills/*/SKILL.md"))
    if not matches:
        raise InferenceError(
            f"no SKILL.md found under {plugin_dir}/skills/*/SKILL.md"
        )
    if len(matches) > 1:
        raise InferenceError(
            f"multiple SKILL.md files under {plugin_dir}/skills/ "
            f"({len(matches)}); SDK backend needs exactly one"
        )
    return matches[0]


def sdk_run(
    prompt: str, plugin_dir: Path | None, model_alias: str = "sonnet"
) -> InferenceResult:
    """Call the model directly via the SDK.

    For the skill-loaded run, the SKILL.md content is injected as the system
    prompt. For the baseline run, system is left empty so the comparison
    isolates the SKILL.md effect. References under `references/` are NOT
    injected — that mirrors how skill auto-discovery surfaces SKILL.md into
    context without the model having explicitly fetched any reference.

    Temperature is pinned to 0 for models that accept it (sonnet, haiku);
    omitted for models that reject it (opus).
    """
    if model_alias not in MODEL_BASE:
        raise InferenceError(
            f"unknown model alias {model_alias!r}; "
            f"valid: {sorted(MODEL_BASE)}"
        )
    base = MODEL_BASE[model_alias]
    client, model = _sdk_client(base)

    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": INFERENCE_MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }
    if model_alias not in NO_TEMPERATURE:
        kwargs["temperature"] = 0.0
    if plugin_dir is not None:
        skill_path = find_skill_md(plugin_dir)
        # Pass as a content-block list — Vertex's Opus 4.7 endpoint rejects
        # the bare-string form even though the public Anthropic API accepts it.
        kwargs["system"] = [{"type": "text", "text": skill_path.read_text()}]

    msg = client.messages.create(**kwargs)
    text = "".join(b.text for b in msg.content if b.type == "text")
    if not text:
        raise InferenceError(f"empty response from SDK: {msg}")

    usage = msg.usage
    cost = _estimate_cost(base, usage.input_tokens, usage.output_tokens)
    raw = {
        "model": model,
        "model_alias": model_alias,
        "stop_reason": msg.stop_reason,
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
    }
    return InferenceResult(text=text, cost_usd=cost, raw=raw)


def _estimate_cost(model_base: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = _PRICING.get(model_base, (15.00, 75.00))  # opus rates as conservative fallback
    return input_tokens * in_rate / 1_000_000 + output_tokens * out_rate / 1_000_000


# ----- CLI backend ---------------------------------------------------------


def cli_run(
    prompt: str,
    plugin_dir: Path | None,
    model_alias: str | None = None,
    timeout: int = 300,
) -> InferenceResult:
    """Subprocess wrapper around `claude --bare --print`.

    Both the baseline and skill-loaded calls use `--bare` so they share the
    same auth path and skip hooks / auto-memory / CLAUDE.md auto-discovery —
    only `--plugin-dir` differs. Exercises the actual skill-discovery
    mechanism, at the cost of CLI-side variance (no `--temperature` flag).

    `model_alias` is honored if provided (passed via `--model`); the CLI
    accepts the same aliases (haiku/sonnet/opus). If omitted, the CLI picks
    its own default (currently Opus 4.7).
    """
    cmd = ["claude", "--bare", "--print", "--output-format", "json"]
    if model_alias is not None:
        cmd += ["--model", model_alias]
    if plugin_dir is not None:
        cmd += ["--plugin-dir", str(plugin_dir)]
    cmd.append(prompt)

    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as e:
        raise InferenceError(f"claude timed out after {timeout}s") from e

    if proc.returncode != 0:
        raise InferenceError(
            f"claude exited {proc.returncode}\n"
            f"stderr: {proc.stderr[:1000]}\n"
            f"stdout: {proc.stdout[:500]}"
        )

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise InferenceError(
            f"could not parse claude json output: {e}\nstdout: {proc.stdout[:1000]}"
        ) from e

    text = data.get("result") or ""
    if not text:
        raise InferenceError(f"claude returned empty result: {data}")

    cost = float(data.get("total_cost_usd") or 0.0)
    return InferenceResult(text=text, cost_usd=cost, raw=data)
