"""App settings, error pages and database migrations."""
import sqlite3
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from flask_migrate import check, downgrade, upgrade

from app import instance_secret_key
from helpers import page_text, register, task_names
from models import db


def table_names(app):
    with app.app_context():
        return set(sa.inspect(db.engine).get_table_names())


# Settings

def test_debug_is_off_by_default(make_app, monkeypatch):
    monkeypatch.delenv('FLASK_DEBUG', raising=False)
    assert make_app().debug is False


def test_settings_from_environment(make_app, monkeypatch):
    monkeypatch.setenv('FLASK_SECRET_KEY', 'from-the-environment')
    app = make_app(SECRET_KEY=None)
    assert app.config['SECRET_KEY'] == 'from-the-environment'


def test_secret_key_is_created_once_and_reused(tmp_path):
    fake_app = SimpleNamespace(instance_path=str(tmp_path / 'instance'))
    key = instance_secret_key(fake_app)
    assert len(key) == 64
    assert (tmp_path / 'instance' / 'secret_key').read_text() == key
    assert instance_secret_key(fake_app) == key


# Error pages

def test_unknown_page_uses_error_template(client):
    response = client.get('/no-such-page')
    assert response.status_code == 404
    assert '<h1>404 Not Found</h1>' in page_text(response)
    assert 'Back to your tasks' in page_text(response)


# Migrations

def test_new_database_gets_all_tables(app):
    assert {'todo', 'users', 'alembic_version'} <= table_names(app)


def test_models_match_migrations(app):
    """Fails if a model was changed without adding a migration for it."""
    with app.app_context():
        check()


def test_migrations_can_be_undone_and_redone(app):
    with app.app_context():
        downgrade(revision='base')
    assert table_names(app) == {'alembic_version'}
    with app.app_context():
        upgrade()
    assert {'todo', 'users'} <= table_names(app)


def test_auto_migrate_can_be_turned_off(make_app):
    app = make_app(AUTO_MIGRATE=False)
    assert 'todo' not in table_names(app)


@pytest.fixture
def old_database(tmp_path):
    """A database made by the original version of the app, before migrations."""
    path = tmp_path / 'old.db'
    con = sqlite3.connect(path)
    con.execute('CREATE TABLE todo (id INTEGER NOT NULL, content VARCHAR(200) NOT NULL, '
                'date_created DATETIME, PRIMARY KEY (id))')
    con.executemany('INSERT INTO todo (content, date_created) VALUES (?, ?)', [
        ('Old task one', '2026-01-05 21:10:54.200523'),
        ('Old task two', '2026-01-05 21:10:58.207710'),
    ])
    con.commit()
    con.close()
    return path.name


def test_old_database_is_upgraded_and_tasks_go_to_first_account(make_app, old_database):
    app = make_app(old_database)
    first, second = app.test_client(), app.test_client()

    register(first, 'sam')
    page = first.get('/')
    assert task_names(page) == ['Old task one', 'Old task two']
    assert '2 existing tasks were added to your account.' in page_text(page)

    register(second, 'alex')
    assert task_names(second.get('/')) == []
