"""Due dates, priorities, sorting, filtering, searching and keeping the
current view of the list."""
import re
from datetime import date, timedelta

import pytest

from helpers import add_task, form_error, page_text, task_names
from models import Todo, db


def days_from_now(days):
    return (date.today() + timedelta(days=days)).isoformat()


def row_class(response, name):
    """The CSS class of the table row for the task called name."""
    match = re.search(r'<tr class="([^"]*)">(?:(?!</tr>).)*class="task-text">'
                      + re.escape(name) + '<', page_text(response), re.S)
    return match.group(1)


# Due dates

def test_due_date_saved_and_shown(app, user):
    add_task(user, 'Pay rent', due_date='2030-01-31')
    with app.app_context():
        assert db.session.get(Todo, 1).due_date == date(2030, 1, 31)
    assert '2030-01-31' in page_text(user.get('/'))


def test_overdue_and_due_today_are_marked(user):
    add_task(user, 'Late', due_date=days_from_now(-1))
    add_task(user, 'Today', due_date=days_from_now(0))
    add_task(user, 'Later', due_date=days_from_now(3))
    add_task(user, 'Late but done', due_date=days_from_now(-1))
    user.post('/toggle/4')

    page = user.get('/')
    assert row_class(page, 'Late') == 'overdue'
    assert row_class(page, 'Today') == 'due-today'
    assert row_class(page, 'Later') == ''
    assert row_class(page, 'Late but done') == 'done'
    assert page_text(page).count('>Overdue<') == 1


@pytest.mark.parametrize('bad_date', ['2026-02-30', 'tomorrow', '31/12/2026'])
def test_invalid_due_date_rejected(user, bad_date):
    response = add_task(user, 'Pay rent', due_date=bad_date)
    assert response.status_code == 400
    assert form_error(response) == 'Due date must be a real date, like 2026-12-31.'


def test_edit_can_change_and_clear_due_date(app, user):
    add_task(user, 'Pay rent', due_date='2030-01-31')
    assert 'value="2030-01-31"' in page_text(user.get('/update/1'))

    user.post('/update/1', data={'content': 'Pay rent', 'due_date': ''})
    with app.app_context():
        assert db.session.get(Todo, 1).due_date is None


# Priorities

def test_priority_saved_and_shown(app, user):
    add_task(user, 'Urgent', priority='3')
    with app.app_context():
        assert db.session.get(Todo, 1).priority == 3
    assert re.search(r'class="priority priority-3"[^>]*>High<', page_text(user.get('/')))
    assert '<option value="3" selected>High</option>' in page_text(user.get('/update/1'))


@pytest.mark.parametrize('bad_priority', ['0', '4', 'high', '', '²'])
def test_invalid_priority_rejected(user, bad_priority):
    response = add_task(user, 'Urgent', priority=bad_priority)
    assert response.status_code == 400
    assert form_error(response) == 'Priority must be Low, Medium, High.'


# Sorting

@pytest.fixture
def mixed_tasks(user):
    add_task(user, 'A', due_date=days_from_now(5), priority='1')
    add_task(user, 'B', priority='3')
    add_task(user, 'C', due_date=days_from_now(1), priority='2')
    add_task(user, 'D', due_date=days_from_now(9), priority='3')
    return user


@pytest.mark.parametrize('sort, expected', [
    ('', ['A', 'B', 'C', 'D']),
    ('added', ['A', 'B', 'C', 'D']),
    ('due', ['C', 'A', 'D', 'B']),        # no due date goes last
    ('priority', ['B', 'D', 'C', 'A']),   # high first, then oldest
    ('nonsense', ['A', 'B', 'C', 'D']),
])
def test_sorting(mixed_tasks, sort, expected):
    assert task_names(mixed_tasks.get('/', query_string={'sort': sort})) == expected


# Filtering and searching

@pytest.fixture
def searchable_tasks(user):
    for name in ['Buy milk', 'Buy BREAD', 'Call mum', '100% done', 'snake_case notes']:
        add_task(user, name)
    user.post('/toggle/1')
    user.post('/toggle/3')
    return user


@pytest.mark.parametrize('query, expected', [
    ({}, ['Buy milk', 'Buy BREAD', 'Call mum', '100% done', 'snake_case notes']),
    ({'status': 'active'}, ['Buy BREAD', '100% done', 'snake_case notes']),
    ({'status': 'done'}, ['Buy milk', 'Call mum']),
    ({'q': 'buy'}, ['Buy milk', 'Buy BREAD']),            # not case-sensitive
    ({'q': 'BUY', 'status': 'active'}, ['Buy BREAD']),
    ({'q': '%'}, ['100% done']),                          # % is not a wildcard
    ({'q': '_'}, ['snake_case notes']),                   # nor is _
    ({'q': '   '}, ['Buy milk', 'Buy BREAD', 'Call mum', '100% done', 'snake_case notes']),
])
def test_filter_and_search(searchable_tasks, query, expected):
    assert task_names(searchable_tasks.get('/', query_string=query)) == expected


def test_no_matches_message(searchable_tasks):
    page = page_text(searchable_tasks.get('/?q=zzz&sort=due'))
    assert 'No tasks match.' in page
    assert '<a href="/?sort=due">Show all tasks</a>' in page


# Keeping the current view

VIEW = '?sort=due&status=active&q=buy'


@pytest.mark.parametrize('url, data', [
    ('/', {'content': 'Buy eggs'}),
    ('/toggle/1', {}),
    ('/update/1', {'content': 'Buy oat milk'}),
    ('/delete/1', {}),
])
def test_actions_return_to_same_view(user, url, data):
    add_task(user, 'Buy milk')
    response = user.post(url + VIEW, data=data)
    assert response.headers['Location'] == '/' + VIEW


def test_links_and_forms_keep_view(user):
    add_task(user, 'Buy milk')
    page = page_text(user.get('/' + VIEW))
    for url in ['/update/1', '/toggle/1', '/delete/1', '/']:
        assert f'"{url}{VIEW}"' in page
    assert f'href="/{VIEW}" class="cancel"' in page_text(user.get('/update/1' + VIEW))


def test_unknown_view_options_dropped(user):
    add_task(user, 'Buy milk')
    assert user.post('/toggle/1?sort=bad&status=bad&extra=1').headers['Location'] == '/'
