#!/usr/bin/env python3 

import time
import logging
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from telegram import telegram
from . import config, management

logger = logging.getLogger(__name__)
logger.setLevel(config.LOGLEVEL)

db = SQLAlchemy()


def make_app():
    bot = telegram.Bot.by(token=config.BOT_API_TOKEN)
    webhook_url = bot.webhookinfo().url
    logger.debug('WEBHOOK_URL: %r', webhook_url)
    if webhook_url != config.BOT_WEBHOOK_URL:
        bot.delete_webhook()
        r = bot.set_webhook(config.BOT_WEBHOOK_URL)
        logger.info('SET_WEBHOOK: %r', r)

    app = Flask(__name__)
    app.cli.add_command(management.bootstrap)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    from . import models
    app.db = db
    app.bot = bot

    from .webhook import bp
    app.register_blueprint(bp, url_prefix='')

    return app
