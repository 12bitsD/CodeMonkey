"""One-shot LLM latency probe. Run from server: `python -m scripts.measure_llm_latency`."""
from __future__ import annotations

import asyncio
import statistics
import time

from services.llm.client import get_llm_client


async def probe(n: int = 20) -> None:
    client = get_llm_client()
    durations: list[float] = []
    failures = 0
    for i in range(n):
        start = time.monotonic()
        try:
            await client.chat_json(
                "You are a test assistant. Return JSON only.",
                'Please return {"ok": true}',
                max_tokens=32,
            )
            durations.append(time.monotonic() - start)
        except Exception as e:
            failures += 1
            print(f"[{i + 1}/{n}] FAIL: {e}")
            continue
        print(f"[{i + 1}/{n}] ok {durations[-1] * 1000:.0f} ms")

    if durations:
        p50 = statistics.median(durations) * 1000
        p95 = (
            statistics.quantiles(durations, n=20)[18] * 1000
            if len(durations) >= 20
            else max(durations) * 1000
        )
        print(
            f"\np50={p50:.0f}ms p95={p95:.0f}ms "
            f"max={max(durations) * 1000:.0f}ms fails={failures}/{n}"
        )
    else:
        print(f"\nAll {n} calls failed")


if __name__ == "__main__":
    asyncio.run(probe())
