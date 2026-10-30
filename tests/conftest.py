import pytest

from app import create_app
from helpers import register
from models import db


@pytest.fixture
def make_app(tmp_path):
    """Return a function that creates an app with its own database file.

    Settings can be overridden; a setting passed as None is left out.
    Database connections are closed and the files deleted after the test.
    """
    apps = []

    def make(db_name='test.db', **settings):
        config = {
            'TESTING': True,
            'SECRET_KEY': 'test',
            # Most tests post forms directly; test_auth.py checks CSRF itself.
            'WTF_CSRF_ENABLED': False,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{tmp_path / db_name}',
            **settings,
        }
        app = create_app({k: v for k, v in config.items() if v is not None})
        apps.append(app)
        return app

    yield make
    for app in apps:
        with app.app_context():
            db.engine.dispose()


@pytest.fixture
def app(make_app):
    return make_app()


@pytest.fixture
def client(app):
    """A browser that is not logged in."""
    return app.test_client()


@pytest.fixture
def user(client):
    """A browser logged in as "sam"."""
    register(client, 'sam')
    client.get('/')  # show (and so clear) the welcome message
    return client
