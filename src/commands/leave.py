"""
/leave guild_id:<id> — make all (or N) tokens leave a guild.

Each token fires DELETE /users/@me/guilds/{guild_id} under its auth.
Results shown in an embed: left / failed / total.
"""

import asyncio
import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
from utils.permissions import check_permission, channel_allowed


async def _leave_one(session: aiohttp.ClientSession, token: str, guild_id: str) -> dict:
    try:
        async with session.delete(
            f"https://discord.com/api/v10/users/@me/guilds/{guild_id}",
            headers={"Authorization": token},
            timeout=aiohttp.ClientTimeout(total=8),
        ) as r:
            return {"ok": r.status == 204, "status": r.status, "token": token[:10]}
    except asyncio.TimeoutError:
        return {"ok": False, "status": 0, "msg": "timeout", "token": token[:10]}
    except Exception as e:
        return {"ok": False, "status": 0, "msg": str(e), "token": token[:10]}


class LeaveCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="leave", description="Make tokens leave a guild")
    @app_commands.describe(
        guild_id="Target guild ID",
        limit="Max tokens to use (default: all)",
        delay="Delay between batches in ms (default: 600)",
    )
    async def leave(
        self,
        interaction: discord.Interaction,
        guild_id: str,
        limit: int | None = None,
        delay: int | None = None,
    ):
        if not channel_allowed(interaction.channel_id):
            return await interaction.response.send_message("❌ Wrong channel.", ephemeral=True)
        if not check_permission(
            interaction.user.id,
            interaction.guild.owner_id if interaction.guild else None,
        ):
            return await interaction.response.send_message("❌ No permission.", ephemeral=True)

        if not guild_id.isdigit():
            return await interaction.response.send_message("❌ Guild ID must be numeric.", ephemeral=True)

        tokens = self.bot.token_manager.get_all()
        if not tokens:
            return await interaction.response.send_message("❌ No tokens stored.", ephemeral=True)

        using = tokens[:limit] if limit else tokens
        delay_ms = delay if delay is not None else 600
        batch_size = 5

        await interaction.response.defer(ephemeral=False)

        start_embed = discord.Embed(title="🚪 Leave Running", color=0xEB459E)
        start_embed.add_field(name="Guild ID", value=guild_id, inline=True)
        start_embed.add_field(name="Tokens", value=str(len(using)), inline=True)
        msg = await interaction.followup.send(embed=start_embed)

        left = 0
        failed = 0
        errors: list[str] = []

        async with aiohttp.ClientSession() as session:
            for i in range(0, len(using), batch_size):
                batch = using[i : i + batch_size]
                results = await asyncio.gather(*[_leave_one(session, t, guild_id) for t in batch])
                for r in results:
                    if r["ok"]:
                        left += 1
                    else:
                        failed += 1
                        errors.append(f"{r['token']}... → {r['status']}")
                if i + batch_size < len(using):
                    await asyncio.sleep(delay_ms / 1000)

        rate = round(left / len(using) * 100) if using else 0
        color = 0x57F287 if failed == 0 else (0xED4245 if left == 0 else 0xFEE75C)
        done = discord.Embed(title="✅ Leave Complete", color=color)
        done.add_field(name="Left", value=str(left), inline=True)
        done.add_field(name="Failed", value=str(failed), inline=True)
        done.add_field(name="Rate", value=f"{rate}%", inline=True)
        if errors:
            done.add_field(name="Last Errors", value="\n".join(errors[-5:]), inline=False)

        await msg.edit(embed=done)


async def setup(bot: commands.Bot):
    await bot.add_cog(LeaveCommands(bot))
