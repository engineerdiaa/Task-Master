"""Adding, listing, editing, ticking and deleting tasks."""
import pytest
from sqlalchemy.exc import OperationalError

from helpers import add_task, flashes, form_error, page_text, task_names
from models import Todo, db


def get_task(app, task_id):
    with app.app_context():
        return db.session.get(Todo, task_id)


def test_empty_list_says_so(user):
    assert 'You have no tasks yet' in page_text(user.get('/'))


def test_add_task(app, user):
    response = add_task(user, '  Buy milk  ')
    assert response.status_code == 302
    assert response.headers['Location'] == '/'

    page = user.get('/')
    assert task_names(page) == ['Buy milk']  # spaces trimmed
    assert flashes(page) == ['Task added.']
    task = get_task(app, 1)
    assert task.completed is False
    assert task.due_date is None
    assert task.priority_label == 'Medium'


def test_tasks_listed_oldest_first(user):
    for name in ['first', 'second', 'third']:
        add_task(user, name)
    assert task_names(user.get('/')) == ['first', 'second', 'third']


@pytest.mark.parametrize('content, message', [
    ('', "Task can't be empty."),
    ('    ', "Task can't be empty."),
    ('x' * 201, 'Task must be 200 characters or fewer.'),
])
def test_add_rejects_bad_text(app, user, content, message):
    response = add_task(user, content)
    assert response.status_code == 400
    assert form_error(response) == message
    assert get_task(app, 1) is None


def test_add_keeps_typed_text_after_error(user):
    response = add_task(user, 'Typed text', due_date='not-a-date')
    assert 'value="Typed text"' in page_text(response)


def test_add_accepts_200_characters(user):
    assert add_task(user, 'x' * 200).status_code == 302


def test_add_without_content_field(user):
    assert user.post('/', data={}).status_code == 400


def test_update_task(app, user):
    add_task(user, 'Buy milk')
    form = page_text(user.get('/update/1'))
    assert 'value="Buy milk"' in form

    response = user.post('/update/1', data={'content': 'Buy oat milk'})
    assert response.status_code == 302
    assert get_task(app, 1).content == 'Buy oat milk'
    assert flashes(user.get('/')) == ['Task updated.']


def test_update_rejects_empty_text(app, user):
    add_task(user, 'Buy milk')
    response = user.post('/update/1', data={'content': ''})
    assert response.status_code == 400
    assert form_error(response) == "Task can't be empty."
    assert get_task(app, 1).content == 'Buy milk'


def test_toggle_marks_done_and_back(app, user):
    add_task(user, 'Buy milk')

    assert user.post('/toggle/1').status_code == 302
    assert get_task(app, 1).completed is True
    assert '<tr class="done">' in page_text(user.get('/'))

    user.post('/toggle/1')
    assert get_task(app, 1).completed is False


def test_delete_task(app, user):
    add_task(user, 'Buy milk')
    response = user.post('/delete/1')
    assert response.status_code == 302
    assert get_task(app, 1) is None
    assert 'Task deleted.' in flashes(user.get('/'))


@pytest.mark.parametrize('url', ['/delete/1', '/toggle/1'])
def test_changes_need_post(app, user, url):
    add_task(user, 'Buy milk')
    assert user.get(url).status_code == 405
    assert get_task(app, 1) is not None


@pytest.mark.parametrize('method, url', [
    ('get', '/update/99'),
    ('post', '/update/99'),
    ('post', '/toggle/99'),
    ('post', '/delete/99'),
])
def test_missing_task_is_404(user, method, url):
    response = getattr(user, method)(url, data={'content': 'x'})
    assert response.status_code == 404
    assert 'That task does not exist' in page_text(response)


def test_cancel_link_on_edit_page(user):
    add_task(user, 'Buy milk')
    assert 'href="/" class="cancel"' in page_text(user.get('/update/1'))


def test_database_error_shows_error_page(app, user, monkeypatch):
    def broken_commit():
        raise OperationalError('INSERT', {}, Exception('disk I/O error'))

    monkeypatch.setattr(db.session, 'commit', broken_commit)
    response = add_task(user, 'Buy milk')
    monkeypatch.undo()

    assert response.status_code == 500
    assert 'There was a problem trying to add your task' in page_text(response)
    assert get_task(app, 1) is None
    # The failed change was rolled back, so the next one works.
    assert add_task(user, 'Buy milk').status_code == 302
