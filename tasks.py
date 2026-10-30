from flask import (Blueprint, abort, current_app, flash, redirect,
                   render_template, request, url_for)
from sqlalchemy.exc import SQLAlchemyError

from models import TASK_MAX_LENGTH, Todo, db

bp = Blueprint('tasks', __name__)

TASK_NOT_FOUND = 'That task does not exist. It may have been deleted.'


def clean_content(raw):
    """Return (content, error) for the text typed into a task form."""
    content = raw.strip()
    if not content:
        return content, "Task can't be empty."
    if len(content) > TASK_MAX_LENGTH:
        return content, f'Task must be {TASK_MAX_LENGTH} characters or fewer.'
    return content, None


def all_tasks():
    """Every task, oldest first."""
    return db.session.scalars(db.select(Todo).order_by(Todo.date_created)).all()


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
        task_content, error = clean_content(request.form.get('content', ''))
        if error:
            return render_template('index.html', tasks=all_tasks(), error=error,
                                   content=task_content), 400

        new_task = Todo(content=task_content)
        db.session.add(new_task)
        save_changes('add your task')
        flash('Task added.', 'success')
        return redirect(url_for('tasks.index'))

    return render_template('index.html', tasks=all_tasks())


@bp.route('/toggle/<int:task_id>', methods=['POST'])
def toggle(task_id):
    """Mark a task as done, or as not done if it already was."""
    task = db.get_or_404(Todo, task_id, description=TASK_NOT_FOUND)
    task.completed = not task.completed
    save_changes('update that task')
    return redirect(url_for('tasks.index'))


@bp.route('/delete/<int:task_id>', methods=['POST'])
def delete(task_id):
    task_to_delete = db.get_or_404(Todo, task_id, description=TASK_NOT_FOUND)
    db.session.delete(task_to_delete)
    save_changes('delete that task')
    flash('Task deleted.', 'success')
    return redirect(url_for('tasks.index'))


@bp.route('/update/<int:task_id>', methods=['GET', 'POST'])
def update(task_id):
    task = db.get_or_404(Todo, task_id, description=TASK_NOT_FOUND)

    if request.method == 'POST':
        content, error = clean_content(request.form.get('content', ''))
        if error:
            return render_template('update.html', task=task, error=error,
                                   content=content), 400

        task.content = content
        save_changes('update your task')
        flash('Task updated.', 'success')
        return redirect(url_for('tasks.index'))

    return render_template('update.html', task=task, content=task.content)
