from datetime import date

from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from sqlalchemy.exc import SQLAlchemyError

from models import DEFAULT_PRIORITY, PRIORITIES, TASK_MAX_LENGTH, Todo, db

bp = Blueprint('tasks', __name__)

TASK_NOT_FOUND = 'That task does not exist. It may have been deleted.'

# Ways the list can be sorted: URL value -> (label, ORDER BY columns).
# Every order ends with the id so tasks added at the same moment stay put.
SORT_ORDERS = {
    'added': ('Date added', (Todo.date_created, Todo.id)),
    # Tasks without a due date go last.
    'due': ('Due date', (Todo.due_date.is_(None), Todo.due_date, Todo.id)),
    'priority': ('Priority', (Todo.priority.desc(), Todo.date_created, Todo.id)),
}
DEFAULT_SORT = 'added'

# Which tasks to show: URL value -> (label, WHERE condition or None).
STATUS_FILTERS = {
    'all': ('All', None),
    'active': ('Active', Todo.completed.is_(False)),
    'done': ('Done', Todo.completed.is_(True)),
}
DEFAULT_STATUS = 'all'


@bp.context_processor
def template_values():
    return {
        'view': view_args(),
        'SORT_ORDERS': SORT_ORDERS,
        'STATUS_FILTERS': STATUS_FILTERS,
        'PRIORITIES': PRIORITIES,
        'TASK_MAX_LENGTH': TASK_MAX_LENGTH,
    }


def view_args():
    """The list options (sort order, filter, search) in the current URL.

    Links and forms pass these along, so after adding, editing or deleting
    a task the user comes back to the same view of their list. Unknown or
    default values are left out.
    """
    args = {}
    sort = request.args.get('sort')
    if sort in SORT_ORDERS and sort != DEFAULT_SORT:
        args['sort'] = sort
    status = request.args.get('status')
    if status in STATUS_FILTERS and status != DEFAULT_STATUS:
        args['status'] = status
    search = request.args.get('q', '').strip()[:TASK_MAX_LENGTH]
    if search:
        args['q'] = search
    return args


def back_to_list():
    return redirect(url_for('tasks.index', **view_args()))


def list_tasks():
    """The tasks to show, filtered and sorted as picked in the URL."""
    view = view_args()
    _, order = SORT_ORDERS[view.get('sort', DEFAULT_SORT)]
    _, condition = STATUS_FILTERS[view.get('status', DEFAULT_STATUS)]

    query = db.select(Todo).order_by(*order)
    if condition is not None:
        query = query.where(condition)
    if 'q' in view:
        # autoescape makes % and _ in the search match literally.
        query = query.where(Todo.content.icontains(view['q'], autoescape=True))
    return db.session.scalars(query).all()


def read_task_form(form):
    """Check the fields sent by an add or edit form.

    Returns (values, error): values holds the cleaned-up fields, ready to
    set on a Todo, and error is a message to show the user, or None.
    """
    content = form.get('content', '').strip()
    due_text = form.get('due_date', '').strip()
    priority_text = form.get('priority', str(DEFAULT_PRIORITY))
    values = {'content': content, 'due_date': None, 'priority': DEFAULT_PRIORITY}

    if not content:
        return values, "Task can't be empty."
    if len(content) > TASK_MAX_LENGTH:
        return values, f'Task must be {TASK_MAX_LENGTH} characters or fewer.'
    if due_text:
        try:
            values['due_date'] = date.fromisoformat(due_text)
        except ValueError:
            return values, 'Due date must be a real date, like 2026-12-31.'
    try:
        values['priority'] = int(priority_text)
    except ValueError:
        values['priority'] = None
    if values['priority'] not in PRIORITIES:
        return values, 'Priority must be ' + ', '.join(PRIORITIES.values()) + '.'
    return values, None


def save_changes(action):
    """Commit the session. If the database fails, undo the changes and
    show an error page that says what couldn't be done."""
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception('Database error while trying to %s', action)
        abort(500, description=f'There was a problem trying to {action}. '
                               'Please try again.')


@bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        values, error = read_task_form(request.form)
        if error:
            return render_template('index.html', tasks=list_tasks(), error=error,
                                   form=request.form), 400

        new_task = Todo(**values)
        db.session.add(new_task)
        save_changes('add your task')
        flash('Task added.', 'success')
        return back_to_list()

    form = {'priority': str(DEFAULT_PRIORITY)}
    return render_template('index.html', tasks=list_tasks(), form=form)


@bp.route('/toggle/<int:task_id>', methods=['POST'])
def toggle(task_id):
    """Mark a task as done, or as not done if it already was."""
    task = db.get_or_404(Todo, task_id, description=TASK_NOT_FOUND)
    task.completed = not task.completed
    save_changes('update that task')
    return back_to_list()


@bp.route('/delete/<int:task_id>', methods=['POST'])
def delete(task_id):
    task_to_delete = db.get_or_404(Todo, task_id, description=TASK_NOT_FOUND)
    db.session.delete(task_to_delete)
    save_changes('delete that task')
    flash('Task deleted.', 'success')
    return back_to_list()


@bp.route('/update/<int:task_id>', methods=['GET', 'POST'])
def update(task_id):
    task = db.get_or_404(Todo, task_id, description=TASK_NOT_FOUND)

    if request.method == 'POST':
        values, error = read_task_form(request.form)
        if error:
            return render_template('update.html', task=task, error=error,
                                   form=request.form), 400

        for field, value in values.items():
            setattr(task, field, value)
        save_changes('update your task')
        flash('Task updated.', 'success')
        return back_to_list()

    form = {
        'content': task.content,
        'due_date': task.due_date.isoformat() if task.due_date else '',
        'priority': str(task.priority),
    }
    return render_template('update.html', task=task, form=form)
