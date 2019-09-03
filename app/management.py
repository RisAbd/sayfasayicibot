
import os
import click
from flask.cli import AppGroup, with_appcontext


@click.command()
@with_appcontext
def bootstrap():
    from app import db, config
    print('making resources directory...', end=' ')
    os.makedirs(config.RESOURCES_DIRECTORY, exist_ok=True)
    print('done.')
    print('creating database schema...', end=' ')
    db.create_all()
    print('done.')
