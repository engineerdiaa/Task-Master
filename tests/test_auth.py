"""Accounts: registering, logging in and out, privacy between users, and
protection against forged forms (CSRF)."""
import re

import pytest

from helpers import add_task, flashes, form_error, login, page_text, register, task_names
from models import Todo, User, db


# Registering

def test_register_logs_in(app, client):
    response = register(client, 'Sam')
    assert response.status_code == 302
    assert response.headers['Location'] == '/'

    page = client.get('/')
    assert flashes(page) == ['Welcome, sam! Your account is ready.']
    assert 'Signed in as <strong>sam</strong>' in page_text(page)


def test_password_is_stored_hashed(app, client):
    register(client, 'sam', 'password1')
    with app.app_context():
        user = db.session.scalars(db.select(User)).one()
    assert 'password1' not in user.password_hash
    assert user.check_password('password1')
    assert not user.check_password('password2')


@pytest.mark.parametrize('username, password, confirm, message', [
    ('ab', 'password1', None, 'Username must be 3-30'),
    ('a' * 31, 'password1', None, 'Username must be 3-30'),
    ('bad name', 'password1', None, 'Username must be 3-30'),
    ('sam', 'short', None, 'Password must be at least 8 characters.'),
    ('sam', 'x' * 201, None, 'Password must be 200 characters or fewer.'),
    ('sam', 'password1', 'password2', "The two passwords don't match."),
])
def test_register_rejects_bad_input(app, client, username, password, confirm, message):
    response = register(client, username, password, confirm)
    assert response.status_code == 400
    assert form_error(response).startswith(message)
    with app.app_context():
        assert db.session.scalar(db.select(db.func.count(User.id))) == 0


def test_usernames_are_not_case_sensitive(app):
    register(app.test_client(), 'sam')
    response = register(app.test_client(), 'SAM')
    assert response.status_code == 400
    assert form_error(response) == 'That username is taken. Please choose another.'


# Logging in and out

def test_pages_need_login(client):
    response = client.get('/update/1')
    assert response.status_code == 302
    assert response.headers['Location'] == '/login?next=%2Fupdate%2F1'
    assert flashes(client.get('/login')) == ['Please log in to see your tasks.']


def test_login_and_logout(app, client):
    register(app.test_client(), 'sam')

    response = login(client, 'SAM')
    assert response.status_code == 302
    assert client.get('/').status_code == 200

    assert client.get('/logout').status_code == 405  # logging out is a POST
    response = client.post('/logout')
    assert response.headers['Location'] == '/login'
    assert client.get('/').status_code == 302


@pytest.mark.parametrize('username, password', [('sam', 'wrong-password'), ('nobody', 'password1')])
def test_login_failure_does_not_say_why(app, client, username, password):
    register(app.test_client(), 'sam')
    response = login(client, username, password)
    assert response.status_code == 400
    assert form_error(response) == 'Wrong username or password.'


@pytest.mark.parametrize('next_url, expected', [
    ('/?sort=due', '/?sort=due'),
    ('https://evil.example/', '/'),
    ('//evil.example/', '/'),
    ('/\\evil.example', '/'),
    ('javascript:alert(1)', '/'),
])
def test_login_only_follows_local_next_urls(app, client, next_url, expected):
    register(app.test_client(), 'sam')
    response = login(client, 'sam', next=next_url)
    assert response.headers['Location'] == expected


def test_keep_me_logged_in_sets_cookie(app, client):
    register(app.test_client(), 'sam')
    response = client.post('/login', data={'username': 'sam', 'password': 'password1',
                                            'remember': '1'})
    assert any(c.startswith('remember_token=') for c in response.headers.getlist('Set-Cookie'))


# Privacy between users

def test_users_only_see_their_own_tasks(app):
    sam, alex = app.test_client(), app.test_client()
    register(sam, 'sam')
    register(alex, 'alex')
    add_task(sam, 'Sam task')
    add_task(alex, 'Alex task')

    assert task_names(sam.get('/')) == ['Sam task']
    assert task_names(alex.get('/')) == ['Alex task']


@pytest.mark.parametrize('method, url', [
    ('get', '/update/1'),
    ('post', '/update/1'),
    ('post', '/toggle/1'),
    ('post', '/delete/1'),
])
def test_other_users_tasks_are_not_found(app, method, url):
    sam, alex = app.test_client(), app.test_client()
    register(sam, 'sam')
    register(alex, 'alex')
    add_task(sam, 'Sam task')

    response = getattr(alex, method)(url, data={'content': 'changed'})
    assert response.status_code == 404
    with app.app_context():
        task = db.session.get(Todo, 1)
        assert (task.content, task.completed) == ('Sam task', False)


# CSRF protection

@pytest.fixture
def csrf_app(make_app):
    return make_app(WTF_CSRF_ENABLED=True)


def csrf_token(response):
    return re.search(r'name="csrf_token" value="([^"]+)"', page_text(response)).group(1)


def test_forms_without_csrf_token_are_refused(csrf_app):
    client = csrf_app.test_client()
    data = {'username': 'sam', 'password': 'password1', 'confirm': 'password1'}

    response = client.post('/register', data=data)
    assert response.status_code == 400
    assert 'This form has expired or was sent from another site' in page_text(response)

    data['csrf_token'] = csrf_token(client.get('/register'))
    assert client.post('/register', data=data).status_code == 302


def test_every_post_form_has_csrf_token(csrf_app):
    client = csrf_app.test_client()
    token = csrf_token(client.get('/register'))
    client.post('/register', data={'username': 'sam', 'password': 'password1',
                                   'confirm': 'password1', 'csrf_token': token})
    client.post('/', data={'content': 'Buy milk', 'csrf_token': token})

    for url in ['/', '/update/1']:
        html = page_text(client.get(url))
        assert html.count('method="POST"') == html.count('name="csrf_token"') > 0
