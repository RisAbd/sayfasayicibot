import os
import click
from flask.cli import with_appcontext


@click.command()
@with_appcontext
def bootstrap():
    from app import db, config  # noqa: F401

    print("making resources directory...", end=" ")
    os.makedirs(config.RESOURCES_DIRECTORY, exist_ok=True)
    print("done.")
