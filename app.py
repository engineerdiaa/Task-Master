import os

from flask import Flask, abort, render_template, request, redirect
from flask_migrate import Migrate, upgrade
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)
# render_as_batch lets migrations change columns on SQLite, which has
# limited ALTER TABLE support.
migrate = Migrate(app, db, directory=os.path.join(app.root_path, 'migrations'),
                  render_as_batch=True)

TASK_MAX_LENGTH = 200
TASK_NOT_FOUND = 'That task does not exist. It may have been deleted.'
app.jinja_env.globals['TASK_MAX_LENGTH'] = TASK_MAX_LENGTH

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(TASK_MAX_LENGTH), nullable=False)
    date_created= db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return '<Task %r>' % self.id

def clean_content(raw):
    """Return (content, error) for the text typed into a task form."""
    content = raw.strip()
    if not content:
        return content, "Task can't be empty."
    if len(content) > TASK_MAX_LENGTH:
        return content, f'Task must be {TASK_MAX_LENGTH} characters or fewer.'
    return content, None

def save_changes(action):
    """Commit the session. If the database fails, undo the changes and
    show an error page that says what couldn't be done."""
    try:
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        app.logger.exception('Database error while trying to %s', action)
        abort(500, description=f'There was a problem trying to {action}. '
                               'Please try again.')

@app.errorhandler(HTTPException)
def handle_http_error(error):
    return render_template('error.html', error=error), error.code

@app.route('/', methods= ['POST', 'GET'])
def index():
    if request.method == 'POST':
        task_content, error = clean_content(request.form.get('content', ''))
        if error:
            tasks = Todo.query.order_by(Todo.date_created).all()
            return render_template('index.html', tasks=tasks, error=error,
                                   content=task_content), 400

        new_task = Todo(content=task_content)
        db.session.add(new_task)
        save_changes('add your task')
        return redirect('/')

    else:
        tasks = Todo.query.order_by(Todo.date_created).all()
        return render_template('index.html', tasks = tasks)
    
@app.route('/delete/<int:id>', methods=['POST'])
def delete(id):
    task_to_delete = Todo.query.get_or_404(id, description=TASK_NOT_FOUND)
    db.session.delete(task_to_delete)
    save_changes('delete that task')
    return redirect('/')

@app.route('/update/<int:id>', methods=['GET', 'post'])
def update(id):
    task = Todo.query.get_or_404(id, description=TASK_NOT_FOUND)

    if request.method == 'POST':
        content, error = clean_content(request.form.get('content', ''))
        if error:
            return render_template('update.html', task=task, error=error,
                                   content=content), 400

        task.content = content
        save_changes('update your task')
        return redirect('/')
    else:
        return render_template('update.html', task=task, content=task.content)


# Create the database tables, or bring an older database up to date.
with app.app_context():
    upgrade()


if __name__ == "__main__":
    app.run(debug=True)