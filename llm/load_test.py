#!/usr/bin/env python3
import argparse
import asyncio
import collections
import statistics
import time

import httpx


async def send_one(client, url, index):
    started = time.perf_counter()
    payload = {
        "model": "ray-l4-poc",
        "messages": [
            {
                "role": "user",
                "content": f"Reply only with the number {index}.",
            }
        ],
        "temperature": 0.0,
        "max_tokens": 16,
    }
    response = await client.post(url, json=payload)
    latency = time.perf_counter() - started
    response.raise_for_status()
    body = response.json()
    return latency, body.get("x_ray", {}), body["choices"][0]["message"]["content"]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080")
    parser.add_argument("--requests", type=int, default=12)
    parser.add_argument("--concurrency", type=int, default=4)
    args = parser.parse_args()

    semaphore = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient(timeout=300) as client:
        async def bounded(index):
            async with semaphore:
                return await send_one(
                    client,
                    f"{args.base_url.rstrip('/')}/v1/chat/completions",
                    index,
                )

        results = await asyncio.gather(
            *(bounded(index) for index in range(args.requests)),
            return_exceptions=True,
        )

    successes = [item for item in results if not isinstance(item, Exception)]
    failures = [item for item in results if isinstance(item, Exception)]
    replicas = collections.Counter(item[1].get("replica_id", "unknown") for item in successes)
    latencies = [item[0] for item in successes]

    print(f"Success: {len(successes)}/{args.requests}")
    print(f"Failure: {len(failures)}")
    print("Replica distribution:")
    for replica, count in replicas.items():
        print(f"  {replica}: {count}")
    if latencies:
        ordered = sorted(latencies)
        p95_index = max(0, round(0.95 * len(ordered)) - 1)
        print(f"Latency p50: {statistics.median(latencies):.2f}s")
        print(f"Latency p95: {ordered[p95_index]:.2f}s")
    for failure in failures[:3]:
        print("Error:", repr(failure))


if __name__ == "__main__":
    asyncio.run(main())
