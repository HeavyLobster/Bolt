import itertools
import logging
from contextlib import suppress
from datetime import datetime
from operator import attrgetter

import discord
import humanize
import peewee_async
from discord.ext import commands
from peewee import DoesNotExist

from bolt.cogs.mod.models import Mute
from bolt.cogs.mod.mutes import unmute_member
from bolt.database import objects
from bolt.paginator import LinePaginator
from .constants import INFRACTION_TYPE_EMOJI
from .models import Infraction
from .types import InfractionType


log = logging.getLogger(__name__)


class Infractions:
    """Infraction management, create / read / update / delete."""

    def __init__(self, bot):
        self.bot = bot
        log.debug('Loaded Cog Infractions.')

    def __unload(self):
        log.debug('Unloaded Cog Infractions.')

    @commands.group(aliases=['infr', 'infractions'])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def infraction(self, _):
        """Contains infraction management commands."""

    @infraction.command(name='reason')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def infraction_reason(self, ctx, id_: int, *, new_reason: str):
        """Change the reason of the given infraction ID to the given new reason."""

        try:
            infraction = await objects.get(
                Infraction,
                Infraction.id == id_,
                Infraction.guild_id == ctx.guild.id
            )
        except DoesNotExist:
            await ctx.send(embed=discord.Embed(
                title="Failed to find infraction #`{0}` on this guild.".format(id_),
                colour=discord.Colour.red()
            ))
        else:
            infraction.reason = new_reason
            await objects.update(infraction, only=['reason'])

            response_embed = discord.Embed(
                title="Successfully edited infraction #`{0}`.".format(id_),
                colour=discord.Colour.green(),
                timestamp=datetime.utcnow()
            ).add_field(
                name="New reason",
                value=new_reason
            ).set_footer(
                text='Authored by {0} ({1})'.format(ctx.author, ctx.author.id),
                icon_url=ctx.author.avatar_url
            )
            await ctx.send(embed=response_embed)

    @infraction.command(name='delete')
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def infraction_delete(self, ctx, id_: int):
        """Delete the given infraction from the database."""

        try:
            infraction = await objects.get(
                Infraction,
                Infraction.id == id_,
                Infraction.guild_id == ctx.guild.id
            )
        except DoesNotExist:
            await ctx.send(embed=discord.Embed(
                title='Failed to find infraction #`{0}` on this Guild.'.format(id_),
                colour=discord.Colour.red()
            ))
        else:
            info_response = discord.Embed(
                title='Successfully deleted infraction #`{0}`.'.format(id_),
                colour=discord.Colour.green()
            )

            if infraction.type == InfractionType.mute:

                # If an active mute for the original infraction was not found,
                # we can safely ignore the `DoesNotExist` error. This simply means
                # that there is no currently active mute, so we're done here.
                with suppress(DoesNotExist):
                    active_mute = await objects.get(
                        Mute,
                        active=True,
                        infraction_id=infraction.id
                    )
                    member = discord.utils.get(ctx.guild.members, id=infraction.user_id)
                    await unmute_member(member, ctx.guild, active_mute)

                    time_until_unmute = active_mute.expiry - datetime.utcnow()
                    expiry_string = humanize.naturaldelta(time_until_unmute)
                    info_response.description = (
                        "The accompanying mute expiring in {0} was also deleted, and the user was unmuted.".format(expiry_string)
                    )

            await objects.delete(infraction)
            await ctx.send(embed=info_response)

    @infraction.command(name='detail')
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def infraction_detail(self, ctx, id_: int):
        """Look up the given infraction ID in the database."""

        try:
            infraction = await objects.get(
                Infraction,
                Infraction.id == id_,
                Infraction.guild_id == ctx.guild.id
            )
        except DoesNotExist:
            await ctx.send(embed=discord.Embed(
                title='Failed to find infraction ID `{0}`.'.format(id_),
                colour=discord.Colour.red()
            ))
        else:
            infraction_embed = discord.Embed(
                title='Infraction: `{0}`'.format(infraction.id),
                colour=discord.Colour.blue()
            )

            infraction_user = self.bot.get_user(infraction.user_id)
            infraction_embed.add_field(
                name='User',
                value=('`{0}` (`{1}`)'.format(infraction_user, infraction_user.id)
                       if infraction_user is not None
                       else 'unknown user (`{0}`)'.format(infraction.user_id))
            )

            infraction_embed.add_field(
                name='Type',
                value='{0} {1}'.format(INFRACTION_TYPE_EMOJI[infraction.type], infraction.type.value.title())
            ).add_field(
                name='Creation',
                value=infraction.created_on.strftime('%d.%m.%y %H:%M')
            ).add_field(
                name='Last edited',
                value=(infraction.edited_on.strftime('%d.%m.%y %H:%M')
                       if infraction.edited_on is not None
                       else 'never')
            ).add_field(
                name='Reason',
                value=infraction.reason or '',
                inline=False
            )

            author_moderator = self.bot.get_user(infraction.moderator_id)
            if author_moderator is not None:
                infraction_embed.set_footer(
                    text='Authored by {0} ({1})'.format(author_moderator, author_moderator.id),
                    icon_url=author_moderator.avatar_url
                )
            else:
                infraction_embed.set_footer(
                    text='Authored by unknown user (ID: {0})'.format(infraction.moderator_id)
                )

            await ctx.send(embed=infraction_embed)

    @infraction.command(name='list')
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def infraction_list(self, ctx, *types: InfractionType):
        """List all infractions, or infractions with the specified type(s)."""

        if types:
            all_infractions = await peewee_async.execute(
                Infraction.select()
                          .where(Infraction.guild_id == ctx.guild.id,
                                 Infraction.type.in_(types))
                          .order_by(Infraction.created_on.desc())
            )
            selected_types = "`, `".join("`{0}`".format(type_.value) for type_ in types)
            title = 'Infractions with types `{0}` on {1}'.format(selected_types, ctx.guild.name)
        else:
            all_infractions = await peewee_async.execute(
                Infraction.select()
                          .where(Infraction.guild_id == ctx.guild.id)
                          .order_by(Infraction.created_on.desc())
            )
            title = 'All infractions on {0}'.format(ctx.guild.name)

        lines = []
        for infraction in all_infractions:
            user = self.bot.get_user(infraction.user_id)
            if user is not None:
                user_string = '`{0}` (`{1}`)'.format(user, user.id)
            else:
                user_string = 'unknown user (`{0}`)'.format(infraction.user_id)
            infraction_emoji = INFRACTION_TYPE_EMOJI[infraction.type]

            creation_string = infraction.created_on.strftime('%d.%m.%y %H:%M')
            lines.append(
                '• [`{0}`] {1} on {2} created {3}'.format(infraction.id, infraction_emoji, user_string, creation_string)
            )

        if not lines:
            response = discord.Embed(
                title=title,
                description="Seems like there's nothing here yet.",
                colour=discord.Colour.blue()
            )
            await ctx.send(response)
        else:
            initial_embed = discord.Embed(title=title, colour=discord.Colour.blue())
            paginator = LinePaginator(ctx, lines, 10, initial_embed)
            await paginator.send()

    @infraction.command(name='user')
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def infraction_user(self, ctx, *, user: discord.User):
        """Look up infractions for the specified user."""

        user_infractions = await peewee_async.execute(
            Infraction.select()
                      .where(Infraction.guild_id == ctx.guild.id,
                             Infraction.user_id == user.id)
                      .order_by(Infraction.type)
        )

        if not user_infractions:
            return await ctx.send(embed=discord.Embed(
                title='No recorded infractions for `{0}` (`{1}`).'.format(user, user.id),
                colour=discord.Colour.blue()
            ))

        most_recent = max(user_infractions, key=attrgetter('created_on'))
        creation_string = most_recent.created_on.strftime('%d.%m.%y %H:%M')
        response = discord.Embed(
            title='Infractions for `{0}` (`{1}`)'.format(user, user.id),
            colour=discord.Colour.blue()
        ).set_footer(
            text='total infractions: {0}, most recent: #{1} at {2}'.format(len(user_infractions), most_recent.id, creation_string),
            icon_url=user.avatar_url
        )

        for infraction_type, infractions in itertools.groupby(
            user_infractions, key=attrgetter('type')
        ):
            response.add_field(
                name='{0} {1}s'.format(INFRACTION_TYPE_EMOJI[infraction_type], infraction_type.value),
                value='\n'.join(
                    "• [`{0}`] added {1} ago".format(infraction.id, humanize.naturaldelta(datetime.utcnow() - infraction.created_on))
                    for infraction in infractions
                )
            )

        await ctx.send(embed=response)
