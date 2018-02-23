import io
from operator import itemgetter

import discord
from discord.ext import commands
from sqlalchemy import and_

from ...bot.config import CONFIG
from ..base import OptionalCog
from .api import LeagueAPIClient
from .converters import Region
from .models import (
    champion as champion_model,
    permitted_role as perm_role_model,
    summoner as summoner_model
)
from .util import has_permission_role


TABLE_HEADER = ("\# | **Summoner Name** | **Server** | **Points**\n"
                "--:|--|--|--\n")


class League(OptionalCog):
    """Contains League of Legends-related commands."""

    RESTRICTED = False

    def __init__(self, bot):
        self.bot = bot
        self.league_client = LeagueAPIClient(CONFIG['league']['key'])

    @commands.group(aliases=['l'])
    @commands.guild_only()
    async def league(self, *_):
        pass

    @league.command(name="setpermrole")
    @commands.has_permissions(manage_roles=True)
    async def set_permitted_role(self, ctx, role: discord.Role):
        """
        Sets the role which members must have
        to modify any settings for this Guild.
        """

        query = perm_role_model.select().where(perm_role_model.c.guild_id == ctx.guild.id)
        result = await self.bot.db.execute(query)
        exists = await result.first() is not None

        if exists:
            await ctx.send(embed=discord.Embed(
                title="Failed to set permitted role:",
                description="A role is already set. Remove it using `rmpermrole`.",
                colour=discord.Colour.red()
            ))
        else:
            query = perm_role_model.insert().values(id=role.id, guild_id=ctx.guild.id)
            await self.bot.db.execute(query)
            await ctx.send(embed=discord.Embed(
                description=f"Successfully set permitted role to {role.mention}.",
                colour=discord.Colour.green()
            ))

    @league.command(name="rmpermrole")
    @commands.has_permissions(manage_roles=True)
    async def remove_permitted_role(self, ctx):
        """
        Remove any role set set previously with setpermrole.
        """

        query = perm_role_model.select().where(perm_role_model.c.guild_id == ctx.guild.id)
        result = await self.bot.db.execute(query)
        exists = await result.first() is not None

        if not exists:
            await ctx.send(embed=discord.Embed(
                title="Cannot remove permitted role:",
                description="No permitted role is set.",
                colour=discord.Colour.red()
            ))
        else:
            query = perm_role_model.delete(perm_role_model.c.guild_id == ctx.guild.id)
            await self.bot.db.execute(query)
            await ctx.send(embed=discord.Embed(
                description="Successfully removed permitted role",
                colour=discord.Colour.green()
            ))

    @league.command(name="setchamp")
    @commands.check(has_permission_role)
    async def set_champion(self, ctx, name: str):
        """
        Sets the champion to be associated with
        this Guild for tracking user mastery.
        """

        query = champion_model.select().where(champion_model.c.guild_id == ctx.guild.id)
        result = await self.bot.db.execute(query)
        exists = await result.first() is not None

        if exists:
            await ctx.send(embed=discord.Embed(
                title="Failed to set associated Champion:",
                description="A champion is already set. Remove it using `rmchamp`.",
                colour=discord.Colour.red()
            ))
        else:
            champion_data = await self.league_client.get_champion(name)
            if champion_data is not None:
                query = champion_model.insert().values(guild_id=ctx.guild.id, champion_id=champion_data['id'])
                await self.bot.db.execute(query)
                await ctx.send(embed=discord.Embed(
                    description=f"Successfully associated Champion `{name}` with this Guild.",
                    colour=discord.Colour.green()
                ))
            else:
                await ctx.send(embed=discord.Embed(
                    title="Failed to set associated Champion:",
                    description=f"No champion named `{name}` was found.",
                    colour=discord.Colour.red()
                ))

    @league.command(name="rmchamp")
    @commands.check(has_permission_role)
    async def remove_champion(self, ctx):
        """
        Removes the champion associated with a guild, if set.
        """

        query = champion_model.select().where(champion_model.c.guild_id == ctx.guild.id)
        result = await self.bot.db.execute(query)
        exists = await result.first() is not None

        if not exists:
            await ctx.send(embed=discord.Embed(
                title="Failed to disassociate champion:",
                description="This guild has no associated champion set.",
                colour=discord.Colour.red()
            ))
        else:
            query = champion_model.delete(champion_model.c.guild_id == ctx.guild.id)
            await self.bot.db.execute(query)
            await ctx.send(embed=discord.Embed(
                description="Successfully disassociated champion from this Guild.",
                colour=discord.Colour.green()
            ))

    @league.command(name="adduser")
    @commands.check(has_permission_role)
    async def add_user(self, ctx, region: Region, *name: str):
        """
        Add a user to the mastery leaderboard for this guild.
        """

        name = ' '.join(name)
        summoner_data = await self.league_client.get_summoner(region, name)
        if summoner_data is None:
            return await ctx.send(embed=discord.Embed(
                title="Failed to add User:",
                description=f"No user named `{name}` in `{region}` found.",
                colour=discord.Colour.red()
            ))

        query = summoner_model.select().where(and_(
            summoner_model.c.id == summoner_data['id'],
            summoner_model.c.guild_id == ctx.guild.id
        ))
        result = await self.bot.db.execute(query)
        exists = await result.first() is not None

        if exists:
            await ctx.send(embed=discord.Embed(
                title="Failed to add User:",
                description=f"`{name}` in `{region}` is already added.",
                colour=discord.Colour.red()
            ))
        else:
            query = summoner_model.insert().values(
                id=summoner_data['id'],
                guild_id=ctx.guild.id,
                region=region
            )
            await self.bot.db.execute(query)
            await ctx.send(embed=discord.Embed(
                description=f"Successfully added `{name}` to the database.",
                colour=discord.Colour.green()
            ))

    @league.command(name="rmuser")
    @commands.check(has_permission_role)
    async def remove_user(self, ctx, region: Region, *name: str):
        """
        Removes a user from the mastery leaderboard for this guild.
        """

        name = ' '.join(name)
        summoner_data = await self.league_client.get_summoner(region, name)
        if summoner_data is None:
            return await ctx.send(embed=discord.Embed(
                title="Failed to remove user:",
                description=f"`{name}` in `{region}` was not found.",
                colour=discord.Colour.red()
            ))

        query = summoner_model.select().where(and_(
            summoner_model.c.id == summoner_data['id'],
            summoner_model.c.guild_id == ctx.guild.id
        ))
        result = await self.bot.db.execute(query)
        exists = await result.first() is not None

        if not exists:
            await ctx.send(embed=discord.Embed(
                title="Failed to remove user:",
                description=f"`{name}` in `{region}` is not in the database.",
                colour=discord.Colour.red()
            ))
        else:
            query = summoner_model.delete(and_(
                summoner_model.c.id == summoner_data['id'],
                summoner_model.c.guild_id == ctx.guild.id
            ))
            await self.bot.db.execute(query)
            await ctx.send(embed=discord.Embed(
                description=f"Successfully removed `{name}` from the database.",
                colour=discord.Colour.green()
            ))

    @league.command(name="buildtable")
    @commands.check(has_permission_role)
    async def build_table(self, ctx):
        """
        Builds a table with the added users on this
        Guild along with their mastery scores and regions
        and outputs it in valid Markdown.
        """

        query = champion_model.select().where(champion_model.c.guild_id == ctx.guild.id)
        result = await self.bot.db.execute(query)
        champion_row = await result.first()

        if champion_row is None:
            await ctx.send(embed=discord.Embed(
                title="Cannot build table:",
                description="This command requires the champion to be set with `setchamp`.",
                colour=discord.Color.red()
            ))
        else:
            query = summoner_model.select().where(summoner_model.c.guild_id == ctx.guild.id)
            result = await self.bot.db.execute(query)
            summoners = await result.fetchall()

            summoner_masteries = [
                (s, await self.league_client.get_mastery(s.region, s.id, champion_row.champion_id))
                for s in summoners
            ]

            with io.StringIO(TABLE_HEADER) as result:
                result.seek(len(TABLE_HEADER))
                for idx, (summ, score) in enumerate(sorted(summoner_masteries, key=itemgetter(1), reverse=True)):
                    summoner_data = await self.league_client.get_summoner(summ.region, summ.id)
                    result.write(f"{idx + 1} | {summoner_data['name']} | {summ.region} | {score:,}\n")

                result.seek(0)
                await ctx.send(f"Done. Total entries: {len(summoner_masteries)}.",
                               file=discord.File(result, filename="table.md"))