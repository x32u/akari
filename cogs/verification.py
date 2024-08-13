import discord
import random
import string
from discord.ext.commands import group, Cog, has_guild_permissions
from discord import (
    TextChannel,
    Role
)

from tools.persistent.verification import VerificationView
from tools.bot import Pretend
from tools.helpers import PretendContext


def generate_code():
  characters = string.hexdigits.upper()
  return ''.join(random.choice(characters) if i not in (3, 6) else '-' for i in range(11))

class Verification(Cog):
    def __init__(self, bot: Pretend):
        self.bot = bot
        self.description = "Verification commands"
        self.thresholds = {}

    @group(invoke_without_command=True)
    async def verification(self, ctx: PretendContext):
        await ctx.send_help(ctx.command)
    @has_guild_permissions(administrator=True)
    @verification.command(name="setup", brief="Administrator")
    async def verification_setup(self, ctx: PretendContext, channel: TextChannel, *, role: Role):
        """setup verification"""
        check = await self.bot.db.fetchrow("SELECT * FROM verify_guilds WHERE guild_id = $1", ctx.guild.id)
        if check:
            return await ctx.send("Verification is already setup in this server.")
        await self.bot.db.execute("INSERT INTO verify_guilds(guild_id, role_id) VALUES ($1, $2)", ctx.guild.id, role.id)
        await channel.send(
    embed=discord.Embed(
        title="Verify",
        description="Click on the button below this message to verify",
        color=discord.Color.blurple()
    ),
    view=VerificationView()
)
        await ctx.send_success("Verification setup successfully.")
    @has_guild_permissions(administrator=True)
    @verification.command(name="reset", brief="Administrator")    
    async def verification_reset(self, ctx: PretendContext):
        """reset verification"""
        check = await self.bot.db.fetchrow("SELECT * FROM verify_guilds WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send("Verification is not setup in this server.")
        await self.bot.db.execute("DELETE FROM verify_guilds WHERE guild_id = $1", ctx.guild.id)
        await ctx.send_success("Verification reset successfully.")


async def setup(bot: Pretend) -> None:
    return await bot.add_cog(Verification(bot))
