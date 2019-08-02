from discord.ext import commands
import logging
token = "[TOKEN]"
description = "Lynn 3.0_DEV"

logging.basicConfig(format='%(asctime)s | [%(levelname)s] (%(filename)s) - %(message)s',
                    level=logging.INFO,
                    handlers=[
                        logging.FileHandler("logs/bot.log"),
                        logging.StreamHandler()
                    ])

def get_prefix(bot, message):
    prefixes = ['%', 'lynn ']

    if not message.guild:
        return '%'

    return commands.when_mentioned_or(*prefixes)(bot, message)

api_keys = {
    "tracker":          "[KEY]",
    "steam":            "[KEY]",
    "darksky":          "[KEY]",
    "omdb":             "[KEY]",
    "mapbox":           "[KEY]"
}

steamIDs = {
        # Discord ID        :  Steam ID
        "123456789123456789": "123456789123456789",
}
