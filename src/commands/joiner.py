"""
/joiner — fire all stored tokens at a Discord invite.

Usage:
  /joiner invite:discord.gg/abc123
  /joiner invite:abc123 limit:50 delay:1200
"""

import re
import discord
from discord.ext import commands
from discord import app_commands
from utils.joiner import mass_join
from utils.permissions import check_permission, channel_allowed


def parse_invite(raw: str) -> str | None:
    raw = raw.strip()
    m = re.search(
        r"(?:discord\.gg/|discordapp\.com/invite/|discord\.com/invite/)([a-zA-Z0-9\-]+)",
        raw,
    )
    if m:
        return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9\-]+", raw):
        return raw
    return None


class JoinerCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="joiner", description="Mass-join a server with all stored tokens")
    @app_commands.describe(
        invite="Invite URL or code",
        limit="Max tokens to use (default: all)",
        delay="Delay between batch rounds in ms (default: 800)",
    )
    async def joiner(
        self,
        interaction: discord.Interaction,
        invite: str,
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

        code = parse_invite(invite)
        if not code:
            return await interaction.response.send_message("❌ Invalid invite.", ephemeral=True)

        tokens = self.bot.token_manager.get_all()
        if not tokens:
            return await interaction.response.send_message("❌ No tokens stored. Use /add first.", ephemeral=True)

        using = tokens[:limit] if limit else tokens
        delay_ms = delay if delay is not None else 800

        await interaction.response.defer(ephemeral=False)

        start_embed = discord.Embed(title="🔄 Joiner Running", color=0x9B59B6)
        start_embed.add_field(name="Target", value=f"discord.gg/{code}", inline=False)
        start_embed.add_field(name="Tokens", value=str(len(using)), inline=True)
        start_embed.add_field(name="Delay", value=f"{delay_ms}ms", inline=True)
        msg = await interaction.followup.send(embed=start_embed)

        result = await mass_join(using, code, delay_ms=delay_ms)

        color = 0x57F287 if result["failed"] == 0 else (0xED4245 if result["joined"] == 0 else 0xFEE75C)
        rate = round(result["joined"] / result["total"] * 100) if result["total"] else 0

        done_embed = discord.Embed(title="✅ Joiner Complete", color=color)
        done_embed.add_field(name="Joined", value=str(result["joined"]), inline=True)
        done_embed.add_field(name="Failed", value=str(result["failed"]), inline=True)
        done_embed.add_field(name="Success", value=f"{rate}%", inline=True)

        if result["errors"]:
            done_embed.add_field(
                name="Last Errors",
                value="\n".join(result["errors"][-5:]),
                inline=False,
            )

        await msg.edit(embed=done_embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(JoinerCommands(bot))
