import logging

import discord
from discord.ext import commands


log = logging.getLogger(__name__)


class Purging:
    """Commands to aid in purging messages."""

    def __init__(self):
        log.debug("Loaded Cog Purging.")

    def __unload(self):
        log.debug("Unloaded Cog Purging.")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge(self, ctx, limit: int):
        """Purge a given amount of messages. View subcommands for more specific purging.

        Requires the `manage_messages` permission on both the Bot and
        the User that invokes the Command. Only works on Guilds.

        For more specific purge commands, use the various subcommands.

        **Examples:**
        purge - deletes 100 messages
        purge 50 - deletes 50 messages
        """

        total = len(await ctx.message.channel.purge(limit=limit))

        info_response = discord.Embed(
            title=f'Purged a total of `{total}` messages.',
            colour=discord.Colour.green()
        ).set_footer(
            text=f'Purged by {ctx.author} ({ctx.author.id})',
            icon_url=ctx.author.avatar_url
        )

        await ctx.send(embed=info_response)

    @purge.command(name='id')
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    async def purge_id(self, ctx, *ids_to_purge: int):
        """Purge up to 1000 Messages sent by the User with the given ID.

        Useful when you want to purge Messages from one or more users that left the Server.

        **Examples:**
        purge id 129301
            searches the past 1000 messages for messages from the user and purges them.
        purge id 129301 128195
            searches the past 1000 messages for messages from these ID's and purges them.
        """

        if not ids_to_purge:
            return await ctx.send(embed=discord.Embed(
                title='Failed to purge by ID:',
                description='You need to specify at least one ID to purge.',
                color=discord.Colour.red()
            ))

        total = len(await ctx.message.channel.purge(
            check=lambda m: m.author.id in ids_to_purge,
            limit=1000
        ))
        pruned_ids = f'`{"`, `".join(str(x) for x in ids_to_purge)}`'

        info_response = discord.Embed(
            title=f'Purged a total of `{total}` messages.',
            description=f'Affected IDs: {pruned_ids}',
            colour=discord.Colour.green()
        )
        info_response.set_footer(
            text=f'Purged by {ctx.author} ({ctx.author.id})',
            icon_url=ctx.author.avatar_url
        )

        await ctx.send(embed=info_response)

    @purge.command(name='containing')
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True, read_message_history=True)
    async def purge_containing(self, ctx, amount: int, *, message_contents: str):
        """Purges up to `amount` Messages containing the specified contents.

        **Examples:**
        purge containing 30 evil
            deletes messages in the last 30 messages containing 'evil'
        purge containing 80 zalgo comes
            deletes messages in the last 80 messages containing 'zalgo comes'
        """

        total = len(await ctx.message.channel.purge(
            check=lambda m: message_contents in m.content,
            limit=amount
        ))

        info_response = discord.Embed(
            title=f'Purged a total of `{total}` messages.',
            description=f'Specified message content: `{message_contents}`.',
            colour=discord.Colour.green()
        )
        info_response.set_footer(
            text=f'Purged by {ctx.author} ({ctx.author.id})',
            icon_url=ctx.author.avatar_url
        )

        await ctx.send(embed=info_response)

    @purge.command(name='user')
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    async def purge_user(self, ctx, amount: int, *to_purge: discord.Member):
        """Purge a mentioned Member, or a list of mentioned Members.

        **Examples:**
        purge user 300 @Person#1337 @Robot#7331
            purges messages from Person and Robot in the past 300 Messages.
        purge user 40 @Person#1337
            purges messages from Person in the past 40 Messages.
        """

        if not to_purge:
            return await ctx.send(embed=discord.Embed(
                title='Failed to purge User(s)',
                description='You need to mention at least one User to purge.',
                color=discord.Colour.red()
            ))

        total = len(await ctx.message.channel.purge(
            check=lambda m: m.author in to_purge,
            limit=amount
        ))

        affected_users = ', '.join(f'`{member}` (`{member.id}`)' for member in to_purge)
        info_response = discord.Embed(
            title=f'Purged a total of `{total}` messages.',
            description=f'Affected users: {affected_users}',
            colour=discord.Colour.green()
        )
        info_response.set_footer(
            text=f'Purged by {ctx.author} ({ctx.author.id})',
            icon_url=ctx.author.avatar_url
        )

        await ctx.send(embed=info_response)
