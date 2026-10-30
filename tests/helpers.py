"""Small helpers shared by the tests."""
import re
from html import unescape


def register(client, username, password='password1', confirm=None):
    return client.post('/register', data={
        'username': username,
        'password': password,
        'confirm': password if confirm is None else confirm,
    })


def login(client, username, password='password1', **query):
    return client.post('/login', query_string=query,
                       data={'username': username, 'password': password})


def add_task(client, content, **fields):
    return client.post('/', data={'content': content, **fields})


def page_text(response):
    return unescape(response.get_data(as_text=True))


def task_names(response):
    """Task names in the order they appear in the list."""
    return re.findall(r'class="task-text">([^<]*)<', page_text(response))


def flashes(response):
    return re.findall(r'role="status">([^<]*)<', page_text(response))


def form_error(response):
    match = re.search(r'role="alert">([^<]*)<', page_text(response))
    return match.group(1) if match else None
