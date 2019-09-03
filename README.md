# Sayfa sayici Bot

```bash
$ pipenv install
$ echo '
BOT_API_TOKEN=$token
LOGLEVEL=DEBUG
FLASK_APP=app:make_app()
FLASK_DEBUG=1
FLASK_ENV=development
BOT_WEBHOOK_URL=https://example.com/bot
' >> .env
$ git submodule init
$ git submodule update
$ pipenv run flask bootstrap
$ pipenv run gunicorn -w1 -b :5000 'app:make_app()'
```
