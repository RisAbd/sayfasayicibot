import os
from decouple import config
import logging

BOT_API_TOKEN = config("BOT_API_TOKEN", cast=str)
BOT_WEBHOOK_URL = config("BOT_WEBHOOK_URL", cast=str)

RESOURCES_DIRECTORY = config(
    "RESOURCES_DIRECTORY", cast=str, default="./resources/"
)
_DEFAULT_DATABASE_URL = "sqlite:///" + os.path.join(
    os.path.abspath(RESOURCES_DIRECTORY), "data.db"
)
DATABASE_URL = config("DATABASE_URL", cast=str, default=_DEFAULT_DATABASE_URL)

_LOGLEVEL = config("LOGLEVEL", default="INFO", cast=str)
LOGLEVEL = getattr(logging, _LOGLEVEL)


PORT = config("PORT", cast=int, default=5000)
HOST = config("HOST", cast=str, default="0.0.0.0")
