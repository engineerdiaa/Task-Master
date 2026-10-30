"""Run the main features against a real PostgreSQL database, the kind a
hosting service provides. Skipped unless TEST_DATABASE_URL is set, e.g.

    TEST_DATABASE_URL=postgresql://postgres@localhost/taskmaster pytest

The database should be empty; the test removes its tables again at the end.
"""
import os
import re
from datetime import date, timedelta

import pytest
from flask_migrate import check, downgrade

from helpers import add_task, page_text, register, task_names

TEST_DATABASE_URL = os.environ.get('TEST_DATABASE_URL')

pytestmark = pytest.mark.skipif(not TEST_DATABASE_URL,
                                reason='TEST_DATABASE_URL is not set')


@pytest.fixture
def pg_app(make_app, monkeypatch):
    # Goes through DATABASE_URL, the same way a hosting service sets it.
    monkeypatch.setenv('DATABASE_URL', TEST_DATABASE_URL)
    app = make_app(SQLALCHEMY_DATABASE_URI=None)
    yield app
    with app.app_context():
        downgrade(revision='base')


def test_app_works_on_postgresql(pg_app):
    assert pg_app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql+psycopg://')
    with pg_app.app_context():
        check()  # the migrations built exactly what the models describe

    sam, alex = pg_app.test_client(), pg_app.test_client()
    register(sam, 'sam')
    register(alex, 'alex')
    soon = (date.today() + timedelta(days=1)).isoformat()
    later = (date.today() + timedelta(days=5)).isoformat()
    add_task(sam, 'Buy milk', due_date=later, priority='1')
    add_task(sam, 'Pay 100% of rent', due_date=soon, priority='3')
    add_task(sam, 'Call mum')
    add_task(alex, 'Alex task')

    assert sam.post('/toggle/1').status_code == 302
    assert sam.post('/update/3', data={'content': 'Call mum today', 'priority': '2'}).status_code == 302

    assert task_names(sam.get('/?sort=due')) == ['Pay 100% of rent', 'Buy milk', 'Call mum today']
    assert task_names(sam.get('/?sort=priority')) == ['Pay 100% of rent', 'Call mum today', 'Buy milk']
    assert task_names(sam.get('/?status=done')) == ['Buy milk']
    assert task_names(sam.get('/?q=MUM')) == ['Call mum today']
    assert task_names(sam.get('/?q=%')) == ['Pay 100% of rent']
    assert task_names(alex.get('/')) == ['Alex task']
    assert alex.post('/delete/1').status_code == 404

    assert sam.post('/delete/2').status_code == 302
    assert 'Pay 100% of rent' not in page_text(sam.get('/'))
    assert re.search(r'Signed in as <strong>sam</strong>', page_text(sam.get('/')))
