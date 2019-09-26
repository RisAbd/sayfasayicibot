#!/usr/bin/env python3

import logging
from flask_sqlalchemy import SQLAlchemy
from flask import Flask
from telegram import telegram
from . import config, management
from urllib.parse import urlparse

logger = logging.getLogger(__name__)
logger.setLevel(config.LOGLEVEL)

db = SQLAlchemy()


def make_app():
    bot = telegram.Bot.by(token=config.BOT_API_TOKEN)

    target_webhook_url = config.BOT_WEBHOOK_URL
    if not urlparse(target_webhook_url).path:
        target_webhook_url += '/{}/'.format(bot._api_token)

    webhook_url = bot.webhookinfo().url
    logger.debug('WEBHOOK_URL: %r', webhook_url)

    if webhook_url != target_webhook_url:
        bot.delete_webhook()
        r = bot.set_webhook(target_webhook_url)
        logger.info('SET_WEBHOOK: %r', r)

    app = Flask(__name__)
    app.config.from_object(config)
    app.cli.add_command(management.bootstrap)
    app.config['SQLALCHEMY_DATABASE_URI'] = config.DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    app.db = db
    app.bot = bot

    from .webhook import bp
    app.register_blueprint(bp, url_prefix='')

    return app
