import os
import tempfile

import pytest
from telegram import telegram
from urllib.parse import urlparse



@pytest.fixture(scope='module')
def app():
    from app import make_app
    app = make_app()
    with app.app_context() as ctx:
        yield app


@pytest.fixture
def client(app):
    db_fd, app.config['DATABASE'] = tempfile.mkstemp()
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(app.config['DATABASE'])


@pytest.fixture
def mock_message_update():
    yield {
        'id': 0,
        'message': {
            'id': 0,
            'date': 0,
            'chat': {
                'id': 0,
                'type': 'private',
            },
            'text': 'some text',
        },
    }


def test_index_not_found(client):
    rv = client.get('/')
    assert rv.status_code == 404


def test_bot_sets_webhook_as_telegram_recommended_or_from_config(client, app):
    bot_api_token = app.bot._api_token
    
    webhook_url_should_end_with = urlparse(app.config['BOT_WEBHOOK_URL']).path
    if not webhook_url_should_end_with:
        webhook_url_should_end_with = '/{}/'.format(bot_api_token)

    print('webhook_app_path:', webhook_url_should_end_with)
    assert app.bot.webhookinfo().url.endswith(webhook_url_should_end_with)


def test_app_handles_telegram_recommended_url(client, app, mock_message_update):
    rv = client.get('/{}/'.format(app.bot._api_token), json=mock_message_update)
    assert rv.status_code == 200
