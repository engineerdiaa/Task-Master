from datetime import date, datetime

from flask import abort, current_app
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash, generate_password_hash

# Give constraints and indexes predictable names, so migrations can
# refer to them on every database.
db = SQLAlchemy(metadata=MetaData(naming_convention={
    'ix': 'ix_%(column_0_label)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(constraint_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s',
}))

TASK_MAX_LENGTH = 200
USERNAME_MAX_LENGTH = 30

# Stored as numbers so tasks can be sorted by priority.
PRIORITIES = {1: 'Low', 2: 'Medium', 3: 'High'}
DEFAULT_PRIORITY = 2


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


class User(UserMixin, db.Model):
    # "user" is a reserved word in PostgreSQL, so use "users".
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(USERNAME_MAX_LENGTH), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, password):
        # Only a salted hash is stored, never the password itself.
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User %r>' % self.username


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(TASK_MAX_LENGTH), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now)
    completed = db.Column(db.Boolean, nullable=False, default=False,
                          server_default=db.false())
    due_date = db.Column(db.Date)
    priority = db.Column(db.Integer, nullable=False, default=DEFAULT_PRIORITY,
                         server_default=str(DEFAULT_PRIORITY))
    # Empty only for tasks made before accounts existed; the first account
    # to be created takes those over (see auth.register).
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)

    @property
    def priority_label(self):
        return PRIORITIES.get(self.priority, 'Unknown')

    @property
    def is_overdue(self):
        """True if the task isn't done and its due date has passed."""
        return (not self.completed and self.due_date is not None
                and self.due_date < date.today())

    @property
    def is_due_today(self):
        return not self.completed and self.due_date == date.today()

    def __repr__(self):
        return '<Task %r>' % self.id
