from discord.ext import commands 
from ...helpers import AkariContext
from PretendAPI.errors import HTTPError
from PretendAPI.models import InstagramUser

class InstagramUser(commands.Converter): 
    async def convert(self, ctx: AkariContext, argument: str) -> InstagramUser: 
        try: 
            return await ctx.bot.api.get_instagram_user(argument)
        except HTTPError as err: 
            return await ctx.error(err.args[0])