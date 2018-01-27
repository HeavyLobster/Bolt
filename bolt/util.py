import json
import logging

import discord
from discord.ext import commands

from bolt.models import prefix as prefix_model

with open("config.json") as f:
    CONFIG = json.load(f)


def create_logger(name, filemode='a', level=logging.INFO):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        logger_file = logging.FileHandler(filename=f'logs/{name}.log', mode=filemode)
        logger_file.setFormatter(logging.Formatter('[%(levelname)s] %(asctime)s (%(name)s): %(message)s'))
        logger.addHandler(logger_file)
    return logger


async def get_prefix(bot, msg):
    # Works without prefix in DMs
    if isinstance(msg.channel, discord.abc.PrivateChannel):
        return commands.when_mentioned_or(*CONFIG['discord']['prefixes'], '')(bot, msg)

    # Check for custom per-guild prefix
    query = prefix_model.select().where(prefix_model.c.guild_id == msg.guild.id)
    res = await bot.db.execute(query)
    prefix_row = await res.first()
    if prefix_row is not None:
        return commands.when_mentioned_or(prefix_row.prefix)(bot, msg)
    return commands.when_mentioned_or(*CONFIG['discord']['prefixes'])(bot, msg)