import logging
from datetime import datetime
from os import environ

import humanize
from discord import Colour, Embed, Guild


log = logging.getLogger(__name__)


class BotLog:
    """Bot logging utilities."""

    def __init__(self, bot):
        self.bot = bot
        self.channel = None
        log.debug("Loaded Cog BotLog.")

    def __unload(self):
        log.debug("Unloaded Cog BotLog.")

    async def on_ready(self):
        if 'BOTLOG_CHANNEL_ID' not in environ:
            log.warning("No bot log channel is set, bot logging will NOT be enabled.")
        else:
            log_channel_id = environ['BOTLOG_CHANNEL_ID']
            try:
                self.channel = self.bot.get_channel(int(log_channel_id))
            except ValueError:
                log.error("{0} is not a valid channel ID, must be an integer".format(log_channel_id))
            else:
                if self.channel is None:
                    log.error("Failed to find bot log channel under ID {0}".format(log_channel_id))
                else:
                    info_embed = Embed(
                        title="Logged in and ready",
                        colour=Colour.green()
                    ).add_field(
                        name="Total members",
                        value="`{0}`".format(len(self.bot.users))
                    ).add_field(
                        name="Total guilds",
                        value="`{0}`".format(len(self.bot.guilds))
                    ).add_field(
                        name="Total commands",
                        value="`{0}`".format(len(self.bot.commands))
                    )
                    await self.channel.send(embed=info_embed)

    async def on_guild_join(self, guild: Guild):
        if self.channel is not None:
            info_embed = Embed(
                title="Joined a Guild",
                colour=Colour.blurple()
            ).add_field(
                name="Total guild members",
                value="`{0}`".format(guild.member_count)
            ).add_field(
                name="Total channels",
                value="`{0}`".format(len(guild.channels))
            ).add_field(
                name="Owner",
                value="{0} (`{1}`)".format(guild.owner, guild.owner.id)
            ).add_field(
                name="Creation",
                value="{0} ({1})".format(guild.created_at.strftime('%d.%m.%y %H:%M'), humanize.naturaldelta(datetime.utcnow() - guild.created_at))
                      
            ).set_author(
                name="{0} ({0})".format(guild, guild.id)
            )

            if guild.icon_url:
                info_embed.set_thumbnail(url=guild.icon_url)

            await self.channel.send(embed=info_embed)
