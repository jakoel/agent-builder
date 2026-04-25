"""Per-million-token pricing for cost tracking. Local providers are free."""

from __future__ import annotations

# USD per 1M tokens (input, output). Update as providers change pricing.
PRICING: dict[str, dict[str, tuple[float, float]]] = {
    "openai": {
        "gpt-4o":         (2.50, 10.00),
        "gpt-4o-mini":    (0.15, 0.60),
        "gpt-4-turbo":    (10.00, 30.00),
        "o1":             (15.00, 60.00),
        "o1-mini":        (3.00, 12.00),
        "o3-mini":        (1.10, 4.40),
    },
    "anthropic": {
        "claude-opus-4-7":           (15.00, 75.00),
        "claude-sonnet-4-6":         (3.00, 15.00),
        "claude-haiku-4-5-20251001": (0.80, 4.00),
        "claude-haiku-4-5":          (0.80, 4.00),
    },
    "ollama": {},
}


def compute_cost(provider: str, model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Return USD cost for a single LLM call. Falls back to 0 if model is unknown."""
    table = PRICING.get(provider, {})
    rates = table.get(model)
    if rates is None:
        # Try a prefix match for versioned models like "claude-sonnet-4-6-20250101"
        for known, r in table.items():
            if model.startswith(known):
                rates = r
                break
    if rates is None:
        return 0.0
    inp_per_m, out_per_m = rates
    return (prompt_tokens * inp_per_m + completion_tokens * out_per_m) / 1_000_000
