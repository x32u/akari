from discord.ext import commands
import discord

OWNERS = [863914425445908490, 598125772754124823]
STAFF = [863914425445908490, 598125772754124823]


class Permissions:
    def has_permission(**perms: bool) -> commands.check:
        invalid = set(perms) - set(discord.Permissions.VALID_FLAGS)
        if invalid:
            raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

        def predicate(ctx: commands.Context) -> bool:
            permissions = ctx.permissions

            if discord.Permissions.administrator in permissions:
                return True

            missing = [
                perm
                for perm, value in perms.items()
                if getattr(permissions, perm) != value
            ]

            if ctx.author.id in ctx.bot.owner_ids or not missing:
                return True

            raise commands.MissingPermissions(missing)

        return commands.check(predicate)

    def check_hierarchy(
        bot: commands.Bot, author: discord.Member, target: discord.Member
    ):
        if target.id in OWNERS:
            raise commands.CommandInvokeError(
                "You cannot perform this action on a bot owner."
            )
        if target.id == author.id:
            raise commands.CommandInvokeError(
                "You cannot perform this action on yourself."
            )
        if target.id in bot.owner_ids:
            raise commands.CommandInvokeError(
                "You cannot perform this action on a bot owner."
            )
        if author.id == author.guild.owner.id:
            return True
        if author.id in bot.owner_ids:
            return True
        if target.id == author.guild.owner.id:
            raise commands.CommandInvokeError(
                "You cannot perform this action on the server owner."
            )
        if target.top_role >= author.top_role:
            raise commands.CommandInvokeError(
                "You cannot perform this action on a higher role than you."
            )
        return True

    def server_owner():
        async def server_owner(ctx: commands.Context):
            if ctx.author.id == ctx.guild.owner_id:
                return True
            if ctx.author.id in OWNERS:
                return True
            else:
                raise commands.CommandInvokeError(
                    "You need to be the server owner to run this command."
                )

        return commands.check(server_owner)

    def staff():
        async def staff(ctx: commands.Context):
            if ctx.author.id in STAFF:
                return True
            else:
                raise commands.CommandInvokeError(
                    "You **need** to have staff permissions to authorize servers."
                )

        return commands.check(staff)

class GoodRole(commands.Converter):
    async def convert(self, ctx: commands.Context, argument):
        try:
            role = await commands.RoleConverter().convert(ctx, argument)
        except commands.BadArgument:
            role = discord.utils.get(ctx.guild.roles, name=argument)
        if role is None:
            role = ctx.find_role(argument)
        if role is None:
            raise commands.BadArgument(f"No role called **{argument}** found")
        if role.position >= ctx.guild.me.top_role.position:
            raise commands.BadArgument("This role cannot be managed by the bot")
        if ctx.author.id == ctx.guild.owner_id:
            return role
        if ctx.author.id in OWNERS:
            return role
        if role.position >= ctx.author.top_role.position:
            raise commands.BadArgument(f"You cannot manage this role")
        return role

class PositionConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        try:
            position = int(argument)
        except ValueError:
            raise commands.BadArgument("The position must be an integer.")
        max_guild_text_channels_position = len(
            [c for c in ctx.guild.channels if isinstance(c, discord.TextChannel)]
        )
        if position <= 0 or position >= max_guild_text_channels_position + 1:
            raise commands.BadArgument(
                f"The indicated position must be between 1 and {max_guild_text_channels_position}."
            )
        position -= 1
        return position

class Perms:
    def server_owner():
        async def predicate(ctx: commands.Context):
            if ctx.author.id != ctx.guild.owner_id:
                await ctx.warning(
                    f"This command can be used only by **{ctx.guild.owner}**"
                )
                return False
            return True

        return commands.check(predicate)