# Sayfa sayici Bot

```bash
$ pipenv install
$ echo '
BOT_API_TOKEN=$token
LOGLEVEL=DEBUG
FLASK_APP=app:make_app()
FLASK_DEBUG=1
FLASK_ENV=development
BOT_WEBHOOK_URL=https://example.com
' >> .env
$ git submodule init
$ git submodule update
$ pipenv run flask bootstrap
$ pipenv run flask db upgrade
$ pipenv run gunicorn -w1 -b :5000 'app:make_app()'
```
