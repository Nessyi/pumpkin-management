from typing import Optional, Union

import nextcord
from nextcord.ext import commands

from pie import check, i18n, logger, utils
from pie.acl.database import ACL_group
from ..verify.database import VerifyMember
from ..verify.enums import VerifyStatus


_ = i18n.Translator("modules/mgmt").translate
guild_log = logger.Guild.logger()


class Whois(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.check(check.acl)
    @commands.command()
    async def roleinfo(self, ctx, role: nextcord.Role):
        """Display role information."""
        acl_group: Optional[ACL_group] = ACL_group.get_by_role(
            guild_id=ctx.guild.id, role_id=role.id
        )

        embed = utils.discord.create_embed(
            author=ctx.author,
            title=role.name,
            description=role.id,
        )
        embed.add_field(
            name=_(ctx, "Member count"),
            value=f"{len(role.members)}",
        )
        embed.add_field(
            name=_(ctx, "Taggable"),
            value=_(ctx, "Yes") if role.mentionable else _(ctx, "No"),
        )
        if acl_group is not None:
            embed.add_field(
                name=_(ctx, "ACL group"),
                value=acl_group.name,
            )
        await ctx.reply(embed=embed)

    @commands.guild_only()
    @commands.check(check.acl)
    @commands.command()
    async def channelinfo(self, ctx, channel: nextcord.TextChannel):
        """Display channel information."""
        if ctx.author not in channel.members:
            ctx.reply(
                _(
                    ctx,
                    "You don't have permission to view information about this channel.",
                )
            )
            return

        webhook_count = len(await channel.webhooks())
        role_count: int = 0
        user_count: int = 0
        for overwrite in channel.overwrites:
            if isinstance(overwrite, nextcord.Role):
                role_count += 1
            else:
                user_count += 1

        topic: str = f"{channel.topic}\n" if channel.topic else ""
        embed = utils.discord.create_embed(
            author=ctx.author,
            title=f"#{channel.name}",
            description=f"{topic}{channel.id}",
        )

        if role_count:
            embed.add_field(
                name=_(ctx, "Role count"),
                value=f"{role_count}",
            )
        if user_count:
            embed.add_field(
                name=_(ctx, "User count"),
                value=f"{user_count}",
            )
        if webhook_count:
            embed.add_field(
                name=_(ctx, "Webhook count"),
                value=f"{webhook_count}",
            )
        await ctx.reply(embed=embed)

    @commands.guild_only()
    @commands.check(check.acl)
    @commands.command()
    async def whois(self, ctx, member: Union[nextcord.Member, int]):
        """See database info on member."""
        dc_member: Optional[nextcord.Member] = None
        user_id: Optional[int] = None

        if type(member) == nextcord.Member:
            user_id = member.id
            dc_member = member
        elif type(member) == int:
            user_id = member

        db_member: Optional[VerifyMember]
        db_member = VerifyMember.get_by_member(ctx.guild.id, user_id)

        if db_member is not None and dc_member is None:
            dc_member = ctx.guild.get_member(db_member.user_id)

        if db_member is None and dc_member is None:
            await ctx.reply(_(ctx, "No such user."))
            return

        await self._whois_reply(ctx, db_member, dc_member)
        await guild_log.info(ctx.author, ctx.channel, f"Whois lookup for {member}.")

    @commands.guild_only()
    @commands.check(check.acl)
    @commands.command()
    async def rwhois(self, ctx, address: str):
        db_member = VerifyMember.get_by_address(ctx.guild.id, address)

        if db_member is None:
            await ctx.reply(_(ctx, "Member is not in a database."))
            return

        dc_member = ctx.guild.get_member(db_member.user_id)

        await self._whois_reply(ctx, db_member, dc_member)
        await guild_log.info(
            ctx.author, ctx.channel, f"Reverse whois lookup for {address}."
        )

    async def _whois_reply(self, ctx, db_member, dc_member):
        description: str
        if dc_member is not None:
            description = f"{dc_member.name} ({dc_member.id})"
        else:
            description = f"{db_member.user_id}"

        embed = utils.discord.create_embed(
            author=ctx.author,
            title=_(ctx, "Whois"),
            description=description,
        )

        if db_member is not None:
            embed.add_field(
                name=_(ctx, "Address"),
                value=db_member.address,
                inline=False,
            )
            embed.add_field(
                name=_(ctx, "Verification code"),
                value=f"`{db_member.code}`",
            )
            embed.add_field(
                name=_(ctx, "Verification status"),
                value=f"{VerifyStatus(db_member.status).name}",
            )
            embed.add_field(
                name=_(ctx, "Timestamp"),
                value=utils.time.format_datetime(db_member.timestamp),
                inline=False,
            )

        if dc_member is not None:
            avatar_url: str = dc_member.display_avatar.replace(size=256).url
            embed.set_thumbnail(url=avatar_url)

            dc_member_roles = list(r.name for r in dc_member.roles[::-1][:-1])
            if dc_member_roles:
                embed.add_field(
                    name=_(ctx, "Roles"),
                    value=", ".join(dc_member_roles),
                )

        await ctx.reply(embed=embed)


def setup(bot) -> None:
    bot.add_cog(Whois(bot))
