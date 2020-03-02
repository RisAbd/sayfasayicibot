import os
import tempfile
import pytest


@pytest.fixture(scope="module")
def app():
    from app import make_app

    app = make_app()
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    db_fd, app.config["DATABASE"] = tempfile.mkstemp()
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client

    os.close(db_fd)
    os.unlink(app.config["DATABASE"])
