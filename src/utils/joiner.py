"""
mass_join — batch invite acceptor.
Each token fires a POST /invites/{code} under its own Authorization header.
Results come back as {joined, failed, total, errors[]}.
"""

import asyncio
import aiohttp


async def _join_one(session: aiohttp.ClientSession, token: str, code: str) -> dict:
    try:
        async with session.post(
            f"https://discord.com/api/v10/invites/{code}",
            headers={"Authorization": token, "Content-Type": "application/json"},
            timeout=aiohttp.ClientTimeout(total=8),
        ) as r:
            if r.status in (200, 201):
                return {"ok": True, "status": r.status, "token": token[:10]}
            body = {}
            if "application/json" in r.headers.get("Content-Type", ""):
                body = await r.json()
            return {"ok": False, "status": r.status, "msg": body.get("message", "unknown"), "token": token[:10]}
    except asyncio.TimeoutError:
        return {"ok": False, "status": 0, "msg": "timeout", "token": token[:10]}
    except Exception as e:
        return {"ok": False, "status": 0, "msg": str(e), "token": token[:10]}


async def mass_join(
    tokens: list[str],
    invite_code: str,
    limit: int | None = None,
    delay_ms: int = 800,
    max_concurrent: int = 5,
) -> dict:
    if limit:
        tokens = tokens[:limit]

    joined = 0
    failed = 0
    errors: list[str] = []
    delay = delay_ms / 1000

    async with aiohttp.ClientSession() as session:
        for i in range(0, len(tokens), max_concurrent):
            batch = tokens[i : i + max_concurrent]
            results = await asyncio.gather(*[_join_one(session, t, invite_code) for t in batch])

            for r in results:
                if r["ok"]:
                    joined += 1
                else:
                    failed += 1
                    errors.append(f"{r['token']}... → {r['status']} {r['msg']}")

            if i + max_concurrent < len(tokens):
                await asyncio.sleep(delay)

    return {"joined": joined, "failed": failed, "total": len(tokens), "errors": errors[-10:]}
