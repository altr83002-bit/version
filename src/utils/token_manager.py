"""
TokenManager — persistent token store with alive-session tracking.
Tokens live in data/tokens.txt across restarts.
Alive sessions are in-memory dict: token -> asyncio.Task
"""

import os
import asyncio
import aiohttp
from pathlib import Path


class TokenManager:
    def __init__(self):
        self.data_dir = os.getenv("DATA_DIR", "./data")
        self.tokens_file = os.path.join(self.data_dir, "tokens.txt")
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)

        # token string -> asyncio.Task (keepalive loop)
        self._alive_tasks: dict[str, asyncio.Task] = {}
        self.tokens: list[str] = self._load()

    # ── persistence ──────────────────────────────────────────────────────

    def _load(self) -> list[str]:
        try:
            if os.path.exists(self.tokens_file):
                with open(self.tokens_file, "r") as f:
                    return [l.strip() for l in f if l.strip()]
        except Exception as e:
            print(f"[TK] load error: {e}")
        return []

    def _save(self):
        try:
            with open(self.tokens_file, "w") as f:
                f.write("\n".join(self.tokens))
        except Exception as e:
            print(f"[TK] save error: {e}")

    # ── crud ─────────────────────────────────────────────────────────────

    def add(self, raw: list[str]) -> int:
        new = [t.strip() for t in raw if t.strip() and t.strip() not in self.tokens]
        self.tokens.extend(new)
        self._save()
        return len(new)

    def remove(self, token: str) -> bool:
        token = token.strip()
        if token in self.tokens:
            self._stop_alive(token)
            self.tokens.remove(token)
            self._save()
            return True
        return False

    def clear(self):
        for t in list(self._alive_tasks.keys()):
            self._stop_alive(t)
        self.tokens.clear()
        self._save()

    def get_all(self) -> list[str]:
        return self.tokens.copy()

    def get_count(self) -> int:
        return len(self.tokens)

    def export(self) -> bytes:
        return "\n".join(self.tokens).encode("utf-8")

    def preview(self, n: int = 10) -> list[str]:
        out = []
        for t in self.tokens[:n]:
            masked = t[:8] + "*" * max(0, len(t) - 8)
            alive = "🟢" if t in self._alive_tasks else "⚫"
            out.append(f"{alive} {masked}")
        return out

    # ── keepalive ────────────────────────────────────────────────────────

    def alive_count(self) -> int:
        return len(self._alive_tasks)

    def is_alive(self, token: str) -> bool:
        return token in self._alive_tasks

    def start_all(self, loop: asyncio.AbstractEventLoop | None = None):
        """Launch keepalive for every stored token. Called on bot ready."""
        for token in self.tokens:
            if token not in self._alive_tasks:
                self._launch(token)

    def start_token(self, token: str) -> bool:
        if token not in self.tokens:
            return False
        if token in self._alive_tasks:
            return True  # already running
        self._launch(token)
        return True

    def stop_token(self, token: str) -> bool:
        return self._stop_alive(token)

    def stop_all(self):
        for t in list(self._alive_tasks.keys()):
            self._stop_alive(t)

    def _launch(self, token: str):
        task = asyncio.create_task(self._keepalive_loop(token))
        self._alive_tasks[token] = task
        task.add_done_callback(lambda t: self._alive_tasks.pop(token, None))

    def _stop_alive(self, token: str) -> bool:
        task = self._alive_tasks.pop(token, None)
        if task and not task.done():
            task.cancel()
            return True
        return False

    async def _keepalive_loop(self, token: str):
        """
        Beats every 4 minutes.
        GET /api/v10/users/@me — lightweight, keeps the WS session considered
        active by Discord's side. On 401 the token is dead; drop it silently.
        """
        interval = int(os.getenv("KEEPALIVE_INTERVAL_S", "240"))  # 4 min default
        headers = {"Authorization": token}
        url = "https://discord.com/api/v10/users/@me"

        print(f"[TK] alive start: {token[:10]}...")
        while True:
            try:
                async with aiohttp.ClientSession() as sess:
                    async with sess.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
                        if r.status == 401:
                            print(f"[TK] token dead (401): {token[:10]}... — dropping")
                            self._alive_tasks.pop(token, None)
                            return
                        if r.status == 429:
                            retry = int((await r.json()).get("retry_after", 5))
                            await asyncio.sleep(retry + 1)
                            continue
            except asyncio.CancelledError:
                print(f"[TK] alive stop: {token[:10]}...")
                return
            except Exception as e:
                print(f"[TK] keepalive err {token[:10]}: {e}")
            await asyncio.sleep(interval)
