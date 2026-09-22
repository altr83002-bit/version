"""
/add — drop tokens into the keeper.

Usage:
  /add tokens:<newline-separated paste>
  /add file:<.txt attachment>
  Both accepted at once.
"""

import discord
from discord.ext import commands
from discord import app_commands
from utils.permissions import check_permission, channel_allowed


class AddCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="add", description="Add tokens to the keeper")
    @app_commands.describe(
        tokens="Paste tokens (newline separated)",
        file="Upload a .txt file full of tokens",
    )
    async def add(
        self,
        interaction: discord.Interaction,
        tokens: str | None = None,
        file: discord.Attachment | None = None,
    ):
        if not channel_allowed(interaction.channel_id):
            return await interaction.response.send_message(
                f"❌ Wrong channel.", ephemeral=True
            )
        if not check_permission(
            interaction.user.id,
            interaction.guild.owner_id if interaction.guild else None,
        ):
            return await interaction.response.send_message(
                "❌ No permission.", ephemeral=True
            )

        if not tokens and not file:
            return await interaction.response.send_message(
                "❌ Provide tokens text or attach a .txt file.", ephemeral=True
            )

        raw_lines: list[str] = []

        if tokens:
            raw_lines.extend(tokens.splitlines())

        if file:
            if not file.filename.endswith(".txt"):
                return await interaction.response.send_message(
                    "❌ File must be .txt", ephemeral=True
                )
            try:
                content = await file.read()
                raw_lines.extend(content.decode("utf-8").splitlines())
            except Exception as e:
                return await interaction.response.send_message(
                    f"❌ Couldn't read file: {e}", ephemeral=True
                )

        added = self.bot.token_manager.add(raw_lines)
        total = self.bot.token_manager.get_count()

        embed = discord.Embed(title="✅ Tokens Added", color=0x57F287)
        embed.add_field(name="New", value=str(added), inline=True)
        embed.add_field(name="Total", value=str(total), inline=True)
        embed.set_footer(text="Use /token start to launch keepalive on all tokens")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AddCommands(bot))
