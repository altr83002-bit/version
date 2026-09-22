"""
/token <action> — full token lifecycle management.

Actions:
  start   — launch keepalive for all tokens (or one by index)
  stop    — stop keepalive for all (or one by index)
  list    — show stored tokens (masked) with alive status
  remove  — delete token by index from storage
  clear   — wipe everything, cancel all keepalives
  export  — DM a tokens.txt with the raw list
  count   — quick count + alive count
"""

import io
import discord
from discord.ext import commands
from discord import app_commands
from utils.permissions import check_permission, channel_allowed


class TokenCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="token", description="Token keeper management")
    @app_commands.describe(
        action="start | stop | list | remove | clear | export | count",
        index="Token index (1-based) for start/stop/remove — omit for all",
    )
    async def token(
        self,
        interaction: discord.Interaction,
        action: str,
        index: int | None = None,
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

        # ── start ──────────────────────────────────────────────────────
        if action == "start":
            if index is not None:
                tokens = tm.get_all()
                if index < 1 or index > len(tokens):
                    return await interaction.response.send_message(
                        f"❌ Index out of range (1–{len(tokens)})", ephemeral=True
                    )
                t = tokens[index - 1]
                ok = tm.start_token(t)
                return await interaction.response.send_message(
                    f"{'✅ Keepalive started' if ok else '⚠️ Already alive'} for token #{index}",
                    ephemeral=True,
                )
            # start all
            before = tm.alive_count()
            tm.start_all()
            after = tm.alive_count()
            embed = discord.Embed(title="🟢 Keepalive Started", color=0x57F287)
            embed.add_field(name="Tokens", value=str(tm.get_count()), inline=True)
            embed.add_field(name="Now Alive", value=str(after), inline=True)
            embed.add_field(name="Newly Launched", value=str(after - before), inline=True)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # ── stop ───────────────────────────────────────────────────────
        elif action == "stop":
            if index is not None:
                tokens = tm.get_all()
                if index < 1 or index > len(tokens):
                    return await interaction.response.send_message(
                        f"❌ Index out of range (1–{len(tokens)})", ephemeral=True
                    )
                t = tokens[index - 1]
                ok = tm.stop_token(t)
                return await interaction.response.send_message(
                    f"{'⛔ Keepalive stopped' if ok else '⚠️ Was not running'} for token #{index}",
                    ephemeral=True,
                )
            before = tm.alive_count()
            tm.stop_all()
            return await interaction.response.send_message(
                f"⛔ Stopped all keepalives ({before} cancelled)", ephemeral=True
            )

        # ── list ───────────────────────────────────────────────────────
        elif action == "list":
            tokens = tm.get_all()
            if not tokens:
                return await interaction.response.send_message("📭 No tokens stored.", ephemeral=True)

            lines: list[str] = []
            for i, t in enumerate(tokens, 1):
                alive = "🟢" if tm.is_alive(t) else "⚫"
                masked = t[:8] + "*" * max(0, len(t) - 8)
                lines.append(f"`{i:>3}.` {alive} `{masked}`")

            # chunk into pages of 20
            pages = [lines[i : i + 20] for i in range(0, len(lines), 20)]
            embed = discord.Embed(
                title=f"📋 Tokens ({len(tokens)} total, {tm.alive_count()} alive)",
                description="\n".join(pages[0]),
                color=0x5865F2,
            )
            if len(pages) > 1:
                embed.set_footer(text=f"Showing 1–20 of {len(tokens)}. Use index range to narrow.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        # ── remove ─────────────────────────────────────────────────────
        elif action == "remove":
            if index is None:
                return await interaction.response.send_message(
                    "❌ Provide index. Example: /token remove index:3", ephemeral=True
                )
            tokens = tm.get_all()
            if index < 1 or index > len(tokens):
                return await interaction.response.send_message(
                    f"❌ Index out of range (1–{len(tokens)})", ephemeral=True
                )
            t = tokens[index - 1]
            tm.remove(t)
            return await interaction.response.send_message(
                f"🗑️ Token #{index} removed. Total now: {tm.get_count()}", ephemeral=True
            )

        # ── clear ──────────────────────────────────────────────────────
        elif action == "clear":
            count = tm.get_count()
            alive = tm.alive_count()
            tm.clear()
            return await interaction.response.send_message(
                f"🗑️ Cleared {count} tokens, cancelled {alive} keepalives.", ephemeral=True
            )

        # ── export ─────────────────────────────────────────────────────
        elif action == "export":
            data = tm.export()
            if not data:
                return await interaction.response.send_message("📭 Nothing to export.", ephemeral=True)
            f = discord.File(io.BytesIO(data), filename="tokens.txt")
            await interaction.response.send_message(
                f"📤 {tm.get_count()} tokens exported:", file=f, ephemeral=True
            )

        # ── count ──────────────────────────────────────────────────────
        elif action == "count":
            embed = discord.Embed(title="📊 Token Count", color=0xFEE75C)
            embed.add_field(name="Stored", value=str(tm.get_count()), inline=True)
            embed.add_field(name="Alive", value=str(tm.alive_count()), inline=True)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            return await interaction.response.send_message(
                "❌ Unknown action. Use: `start | stop | list | remove | clear | export | count`",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(TokenCommands(bot))
