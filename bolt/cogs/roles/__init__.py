from .cog import Roles


def setup(bot):
    bot.add_cog(Roles(bot))
