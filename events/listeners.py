import asyncio, aiohttp, datetime, discord, datetime, io, re, orjson, uwuify

from discord.ext.commands import Cog

from collections import defaultdict
from discord.ext.commands import Cog
from discord import User, Member, AllowedMentions, Message, MessageType

from collections import defaultdict

from tools.bot import Akari
from tools.validators import ValidAutoreact


class Listeners(Cog):
    def __init__(self, bot: Akari):
        self.bot = bot
        self.locks = defaultdict(asyncio.Lock)

    @Cog.listener("on_user_update")
    async def username_change(self, before: User, after: User):
        if before.name != after.name:
            await self.bot.db.execute(
                "INSERT INTO usernames VALUES ($1,$2,$3)",
                after.id,
                str(before),
                int(datetime.datetime.now().timestamp()),
            )

    @Cog.listener("on_member_update")
    async def on_boost_role_update(self, before: Member, after: Member):
        if (
            not before.guild.premium_subscriber_role in before.roles
            and after.guild.premium_subscriber_role in after.roles
        ):
            if before.guild.system_channel:
                return

            results = await self.bot.db.fetch(
                "SELECT * FROM boost WHERE guild_id = $1", after.guild.id
            )
            for result in results:
                channel = self.bot.get_channel(result["channel_id"])
                if channel:
                    perms = channel.permissions_for(after.guild.me)
                    if perms.send_messages and perms.embed_links:
                        x = await self.bot.embed_build.alt_convert(
                            after, result["message"]
                        )
                        await channel.send(**x)
                        await asyncio.sleep(0.4)

    @Cog.listener("on_member_join")
    async def on_new_member(self, member: Member):
        results = await self.bot.db.fetch(
            "SELECT * FROM welcome WHERE guild_id = $1", member.guild.id
        )
        for result in results:
            channel = self.bot.get_channel(result["channel_id"])
            if channel:
                perms = channel.permissions_for(member.guild.me)
                if perms.send_messages and perms.embed_links:
                    x = await self.bot.embed_build.alt_convert(
                        member, result["message"]
                    )
                    await channel.send(**x)
                    await asyncio.sleep(0.4)

    @Cog.listener("on_member_remove")
    async def on_leave_event(self, member: Member):
        results = await self.bot.db.fetch(
            "SELECT * FROM leave WHERE guild_id = $1", member.guild.id
        )
        for result in results:
            channel = self.bot.get_channel(result["channel_id"])
            if channel:
                perms = channel.permissions_for(member.guild.me)
                if perms.send_messages and perms.embed_links:
                    x = await self.bot.embed_build.alt_convert(
                        member, result["message"]
                    )
                    await channel.send(**x)
                    await asyncio.sleep(0.4)

    @Cog.listener("on_member_join")
    async def on_autorole(self, member: Member):
        if member.guild.me.guild_permissions.manage_roles:
            if member.guild.id == 1005150492382478377:
                check = await self.bot.db.fetchrow(
                    "SELECT * FROM authorize WHERE user_id = $1", member.id
                )
                if check:
                    await member.add_roles(
                        member.guild.get_role(1124447347783520318),
                        reason="Subscriber joined the server",
                    )

            results = await self.bot.db.fetch(
                "SELECT * FROM autorole WHERE guild_id = $1", member.guild.id
            )
            for result in results:
                role = member.guild.get_role(result["role_id"])
                if role:
                    if role.is_assignable():
                        await member.add_roles(role, reason="AutoRole")

    @Cog.listener("on_member_remove")
    async def on_boost_remove(self, before: Member):
        check = await self.bot.db.fetchrow(
            "SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
            before.guild.id,
            before.id,
        )
        if check:
            role = before.guild.get_role(int(check["role_id"]))
            await self.bot.db.execute(
                "DELETE FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
                before.guild.id,
                before.id,
            )
            await role.delete(reason="booster left the server")

    @Cog.listener("on_member_update")
    async def on_boost_transfered(self, before: Member, after: Member):
        if (
            before.guild.premium_subscriber_role in before.roles
            and not after.guild.premium_subscriber_role in after.roles
        ):
            check = await self.bot.db.fetchrow(
                "SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
                before.guild.id,
                before.id,
            )
            if check:
                role = before.guild.get_role(int(check["role_id"]))
                await self.bot.db.execute(
                    "DELETE FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
                    before.guild.id,
                    before.id,
                )
                await role.delete(reason="booster transfered all their boosts")

    @Cog.listener("on_user_update")
    async def on_username_tracking(self, before: User, after: User):
        if str(before) != str(after):
            results = await self.bot.db.fetch("SELECT webhook_url FROM username_track")
            headers = {"Content-Type": "application/json"}

            json = {
                "username": "Akari-usernames",
                "content": f"New username available: **{before}**",
                "avatar_url": self.bot.user.display_avatar.url,
            }

            for result in results:
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.post(result["webhook_url"], json=json) as r:
                        if not r.status in [204, 429]:
                            await self.bot.db.execute(
                                "DELETE FROM username_track WHERE webhook_url = $1",
                                result["webhook_url"],
                            )

    @Cog.listener("on_member_join")
    async def whitelist_check(self, member: Member):
        """
        Check for user IDs in the whitelist
        """
        if await self.bot.db.fetchrow(
            """
    SELECT * FROM whitelist_state
    WHERE guild_id = $1
    """,
            member.guild.id,
        ):
            if not await self.bot.db.fetchrow(
                """
      SELECT * FROM whitelist
      WHERE guild_id = $1
      AND user_id = $2
      """,
                member.guild.id,
                member.id,
            ):
                if check := await self.bot.db.fetchrow(
                    """
        SELECT embed FROM whitelist_state
        WHERE guild_id = $1
        """,
                    member.guild.id,
                ):
                    if check["embed"] == "default":
                        try:
                            await member.send(
                                f"You are not whitelisted to join **{member.guild.name}**"
                            )
                        except Exception as e:
                            self.bot.get_channel(1218519366610456629).send(e)
                            pass

                    elif check["embed"] == "none":
                        try:
                            return await member.guild.kick(
                                member, reason=f"Not in the whitelist"
                            )
                        except Exception as e:
                            self.bot.get_channel(1218519366610456629).send(e)

                    else:
                        x = await self.bot.embed_build.alt_convert(
                            member, check["embed"]
                        )
                        try:
                            await member.send(**x)
                        except Exception as e:
                            self.bot.get_channel(1218519366610456629).send(e)
                            pass
                try:
                    await member.guild.kick(member, reason=f"Not in the whitelist")
                except Exception as e:
                    self.bot.get_channel(1218519366610456629).send(e)


    @Cog.listener("on_raw_reaction_add")
    async def on_reactionrole_add(self, payload: discord.RawReactionActionEvent):
        m = self.bot.get_guild(payload.guild_id).get_member(payload.user_id)
        if not m:
            return
        if m.bot:
            return

        check = await self.bot.db.fetchrow(
            "SELECT role_id FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4",
            payload.guild_id,
            payload.channel_id,
            payload.message_id,
            str(payload.emoji),
        )
        if check:
            role = self.bot.get_guild(payload.guild_id).get_role(check[0])
            if role:
                if role.is_assignable():
                    if (
                        not role
                        in self.bot.get_guild(payload.guild_id)
                        .get_member(payload.user_id)
                        .roles
                    ):
                        await self.bot.get_guild(payload.guild_id).get_member(
                            payload.user_id
                        ).add_roles(role, reason="Reaction Role")

    @Cog.listener("on_raw_reaction_remove")
    async def on_reactionrole_remove(self, payload: discord.RawReactionActionEvent):
        m = self.bot.get_guild(payload.guild_id).get_member(payload.user_id)
        if not m:
            return
        if m.bot:
            return

        check = await self.bot.db.fetchrow(
            "SELECT role_id FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4",
            payload.guild_id,
            payload.channel_id,
            payload.message_id,
            str(payload.emoji),
        )
        if check:
            role = self.bot.get_guild(payload.guild_id).get_role(check[0])
            if role:
                if role.is_assignable():
                    if (
                        role
                        in self.bot.get_guild(payload.guild_id)
                        .get_member(payload.user_id)
                        .roles
                    ):
                        await self.bot.get_guild(payload.guild_id).get_member(
                            payload.user_id
                        ).remove_roles(role, reason="Reaction Role")

    # starboard

    @Cog.listener("on_raw_reaction_remove")
    async def on_starboard_remove(self, payload: discord.RawReactionActionEvent):
        res = await self.bot.db.fetchrow(
            "SELECT * FROM starboard WHERE guild_id = $1", payload.guild_id
        )
        if res:
            if not res["emoji"]:
                return
            if str(payload.emoji) == res["emoji"]:
                mes = await self.bot.get_channel(payload.channel_id).fetch_message(
                    payload.message_id
                )
                reactions = [
                    r.count for r in mes.reactions if str(r.emoji) == res["emoji"]
                ]
                if len(reactions) > 0:
                    reaction = reactions[0]
                    if not res["channel_id"]:
                        return
                    channel = self.bot.get_channel(res["channel_id"])
                    if channel:
                        check = await self.bot.db.fetchrow(
                            "SELECT * FROM starboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3",
                            payload.guild_id,
                            payload.channel_id,
                            payload.message_id,
                        )
                        if check:
                            try:
                                m = await channel.fetch_message(
                                    check["starboard_message_id"]
                                )
                                await m.edit(
                                    content=f"{payload.emoji} **#{reaction}** {mes.channel.mention}"
                                )
                            except:
                                await self.bot.db.execute(
                                    "DELETE FROM starboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3",
                                    payload.guild_id,
                                    payload.channel_id,
                                    payload.message_id,
                                )

    @Cog.listener("on_raw_reaction_add")
    async def on_starboard_add(self, payload: discord.RawReactionActionEvent):
        res = await self.bot.db.fetchrow(
            "SELECT * FROM starboard WHERE guild_id = $1", payload.guild_id
        )
        if res:
            if not res["emoji"]:
                return
            if str(payload.emoji) == res["emoji"]:
                mes = await self.bot.get_channel(payload.channel_id).fetch_message(
                    payload.message_id
                )
                reactions = [
                    r.count for r in mes.reactions if str(r.emoji) == res["emoji"]
                ]
                if len(reactions) > 0:
                    reaction = reactions[0]
                    if not res["channel_id"]:
                        return
                    channel = self.bot.get_channel(res["channel_id"])

                    if not channel:
                        return

                    if payload.channel_id == channel.id:
                        return

                    check = await self.bot.db.fetchrow(
                        "SELECT * FROM starboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3",
                        payload.guild_id,
                        payload.channel_id,
                        payload.message_id,
                    )
                    if not check:
                        if not res["count"]:
                            return
                        if reaction < res["count"]:
                            return
                        file = None
                        if not mes.embeds:
                            embed = discord.Embed(
                                color=self.bot.color,
                                description=mes.content,
                                timestamp=mes.created_at,
                            )
                            embed.set_author(
                                name=str(mes.author),
                                icon_url=mes.author.display_avatar.url,
                            )
                            if mes.attachments:
                                if mes.attachments[0].filename.endswith(
                                    ("png", "jpeg", "jpg")
                                ):
                                    embed.set_image(url=mes.attachments[0].proxy_url)
                                elif mes.attachments[0].filename.endswith(
                                    ("mp3", "mp4", "mov")
                                ):
                                    file = discord.File(
                                        fp=io.BytesIO(await mes.attachments[0].read()),
                                        filename=mes.attachments[0].filename,
                                    )
                        else:
                            em = mes.embeds[0]
                            embed = discord.Embed(
                                color=em.color,
                                description=em.description or mes.content,
                                title=em.title,
                                url=em.url,
                            )

                            if em.author:
                                embed.set_author(
                                    name=em.author.name,
                                    icon_url=em.author.proxy_icon_url,
                                    url=em.author.url,
                                )
                            else:
                                embed.set_author(
                                    name=mes.author,
                                    icon_url=mes.author.display_avatar.url,
                                )

                            if em.thumbnail:
                                embed.set_thumbnail(url=em.thumbnail.proxy_url)

                            if em.image:
                                embed.set_image(url=em.image.proxy_url)

                            if em.footer:
                                embed.set_footer(
                                    text=em.footer.text, icon_url=em.footer.icon_url
                                )

                            if mes.attachments:
                                file = discord.File(
                                    fp=io.BytesIO(await mes.attachments[0].read()),
                                    filename=mes.attachments[0].filename,
                                )

                        if mes.reference:
                            embed.description = f"{embed.description}\n<:right:1106622898489262170> [replying to {mes.reference.resolved.author}]({mes.reference.resolved.jump_url})"

                        view = discord.ui.View()
                        view.add_item(
                            discord.ui.Button(label="message", url=mes.jump_url)
                        )
                        perms = channel.permissions_for(channel.guild.me)
                        if (
                            perms.send_messages
                            and perms.embed_links
                            and perms.attach_files
                        ):
                            m = await channel.send(
                                content=f"{payload.emoji} **#{reaction}** {mes.channel.mention}",
                                embed=embed,
                                view=view,
                                file=file,
                            )
                            await self.bot.db.execute(
                                "INSERT INTO starboard_messages VALUES ($1,$2,$3,$4)",
                                payload.guild_id,
                                payload.channel_id,
                                payload.message_id,
                                m.id,
                            )
                    else:
                        try:
                            m = await channel.fetch_message(
                                check["starboard_message_id"]
                            )
                            await m.edit(
                                content=f"{payload.emoji} **#{reaction}** {mes.channel.mention}"
                            )
                        except:
                            await self.bot.db.execute(
                                "DELETE FROM starboard_messages WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3",
                                payload.guild_id,
                                payload.channel_id,
                                payload.message_id,
                            )

    @Cog.listener("on_reaction_remove")
    async def reaction_snipe_event(
        self, reaction: discord.Reaction, user: discord.Member
    ):
        if user.bot:
            return

        get_snipe = self.bot.cache.get("reaction_snipe")
        if get_snipe:
            lol = get_snipe
            lol.append(
                {
                    "channel": reaction.message.channel.id,
                    "message": reaction.message.id,
                    "reaction": str(reaction.emoji),
                    "user": str(user),
                    "created_at": datetime.datetime.now().timestamp(),
                }
            )
            await self.bot.cache.set("reaction_snipe", lol)
        else:
            payload = [
                {
                    "channel": reaction.message.channel.id,
                    "message": reaction.message.id,
                    "reaction": str(reaction.emoji),
                    "user": str(user),
                    "created_at": datetime.datetime.now().timestamp(),
                }
            ]
            await self.bot.cache.set("reaction_snipe", payload)


    @Cog.listener("on_message")
    async def bump_event(self, message: Message):
        if message.type == MessageType.chat_input_command:
            if (
                message.interaction.name == "bump"
                and message.author.id == 302050872383242240
            ):
                if (
                    "Bump done!" in message.embeds[0].description
                    or "Bump done!" in message.content
                ):
                    check = await self.bot.db.fetchrow(
                        "SELECT thankyou FROM bumpreminder WHERE guild_id = $1",
                        message.guild.id,
                    )
                    if check is not None:
                        x = await self.bot.embed_build.alt_convert(
                            message.interaction.user, check[0]
                        )
                        x["allowed_mentions"] = AllowedMentions.all()
                        await message.channel.send(**x)
                        await self.bot.db.execute(
                            "UPDATE bumpreminder SET time = $1, channel_id = $2, user_id = $3 WHERE guild_id = $4",
                            datetime.datetime.now() + datetime.timedelta(hours=2),
                            message.channel.id,
                            message.interaction.user.id,
                            message.guild.id,
                        )

    @Cog.listener("on_message")
    async def on_boost(self, message: Message):
        if message.guild:
            if "MessageType.premium_guild" in str(message.type):
                if message.guild.id == 1005150492382478377:
                    res = await self.bot.db.fetchrow(
                        "SELECT * FROM donor WHERE user_id = $1", message.author.id
                    )
                    if not res:
                        await self.bot.db.execute(
                            "INSERT INTO donor VALUES ($1,$2,$3)",
                            message.author.id,
                            datetime.datetime.now().timestamp(),
                            "boosted",
                        )

                member = message.author

                results = await self.bot.db.fetch(
                    "SELECT * FROM boost WHERE guild_id = $1", message.guild.id
                )
                for result in results:
                    channel = self.bot.get_channel(result["channel_id"])
                    if channel:
                        perms = channel.permissions_for(member.guild.me)
                        if perms.send_messages and perms.embed_links:
                            x = await self.bot.embed_build.alt_convert(
                                member, result["message"]
                            )
                            await channel.send(**x)
                            await asyncio.sleep(0.4)

    @Cog.listener("on_message")
    async def on_autoresponder(self, message: Message):
        if message.author.bot:
            return

        if not message.guild:
            return

        for row in await self.bot.db.fetch(
            "SELECT * FROM autoresponder WHERE guild_id = $1", message.guild.id
        ):
            if row["strict"] is True:
                if str(row["trigger"]).lower() == message.content.lower():
                    ctx = await self.bot.get_context(message)
                    x = await self.bot.embed_build.convert(ctx, row["response"])

                    await ctx.send(**x)
            else:
                if str(row["trigger"]).lower() in message.content.lower():
                    ctx = await self.bot.get_context(message)
                    x = await self.bot.embed_build.convert(ctx, row["response"])

                    await ctx.send(**x)

    @Cog.listener("on_message")
    async def on_autoreact(self, message: Message):
        if message.author.bot:
            return

        if not message.guild:
            return

        if not message.guild.me.guild_permissions.add_reactions:
            return

        words = message.content.lower().split()
        results = await self.bot.db.fetch(
            "SELECT * FROM autoreact WHERE guild_id = $1", message.guild.id
        )
        for result in results:
            if result["trigger"] in words:
                bucket = await self.get_autoreact_cd(message)

                if bucket:
                    return

                reactions = orjson.loads(result["reactions"])
                ctx = await self.bot.get_context(message)
                for reaction in reactions:
                    x = await ValidAutoreact().convert(ctx, reaction)
                    if x:
                        await message.add_reaction(x)
                return

    @Cog.listener("on_message")
    async def uwulock(self, message: Message):
        if message.author.bot:
            return

        uwulock_enabled = await self.bot.db.fetchval(
            "SELECT EXISTS(SELECT 1 FROM uwu_lock WHERE guild_id = $1 AND user_id = $2)",
            message.guild.id,
            message.author.id,
        )

        if uwulock_enabled:
            flags = uwuify.YU | uwuify.STUTTER
            uwuified_content = uwuify.uwu(message.content, flags=flags)
            await message.delete()
            webhook = await self.webhook(message.channel)

            await webhook.send(
                content=uwuified_content,
                username=message.author.name,
                avatar_url=message.author.avatar.url,
            )

    @Cog.listener("on_message_delete")
    async def snipes(self, message: Message):
        if message.author.bot:
            return

        get_snipes = self.bot.cache.get("snipe")
        payload = [
            {
                "channel": message.channel.id,
                "name": str(message.author),
                "avatar": message.author.display_avatar.url,
                "message": message.content,
                "attachments": message.attachments,
                "stickers": message.stickers,
                "created_at": message.created_at.timestamp(),
            }
        ]

        if get_snipes:
            lol = self.bot.cache.get("snipe")
            lol.append(
                {
                    "channel": message.channel.id,
                    "name": str(message.author),
                    "avatar": message.author.display_avatar.url,
                    "message": message.content,
                    "attachments": message.attachments,
                    "stickers": message.stickers,
                    "created_at": message.created_at.timestamp(),
                }
            )
            return await self.bot.cache.set("snipe", lol)
        else:
            await self.bot.cache.set("snipe", payload)

    @Cog.listener("on_message_edit")
    async def edit_snipe(self, before: Message, after: Message):
        if before.author.bot:
            return
        if before.content == after.content:
            return

        get_snipes = self.bot.cache.get("edit_snipe")
        if get_snipes:
            lol = self.bot.cache.get("edit_snipe")
            lol.append(
                {
                    "channel": before.channel.id,
                    "name": str(before.author),
                    "avatar": before.author.display_avatar.url,
                    "before": before.content,
                    "after": after.content,
                }
            )
            return await self.bot.cache.set("edit_snipe", lol)
        else:
            payload = [
                {
                    "channel": before.channel.id,
                    "name": str(before.author),
                    "avatar": before.author.display_avatar.url,
                    "before": before.content,
                    "after": after.content,
                }
            ]
            return await self.bot.cache.set("edit_snipe", payload)

    @Cog.listener("on_message")
    async def reposter(self, message: Message):
        if (
            message.guild
            and not message.author.bot
            and message.content.startswith("Akari")
        ):
            if re.search(
                r"\bhttps?:\/\/(?:m|www|vm)\.tiktok\.com\/\S*?\b(?:(?:(?:usr|v|embed|user|video)\/|\?shareId=|\&item_id=)(\d+)|(?=\w{7})(\w*?[A-Z\d]\w*)(?=\s|\/$))\b",
                message.content[len("Akari") + 1 :],
            ):
                return await self.repost_tiktok(message)
            elif re.search(
                r"((?:https?:\/\/)?(?:www\.)?instagram\.com\/(?:p|reel)\/([^/?#&]+)).*",
                message.content[len("Akari") + 1 :],
            ):
                return await self.repost_instagram(message)

    @Cog.listener("on_message")
    async def imageonly_check(self, message: Message):

        if not message.guild:
            return

        if not message.guild.me.guild_permissions.manage_messages:
            return

        if await self.bot.db.fetchrow(
            """
       SELECT * FROM imgonly
       WHERE guild_id = $1
       AND channel_id = $2
       """,
            message.guild.id,
            message.channel.id,
        ):
            if not message.author.guild_permissions.manage_messages:
                cooldown = await self.get_ratelimit(message)
                if not message.attachments:
                    await message.delete()



async def setup(bot: Akari) -> None:
    await bot.add_cog(Listeners(bot))
