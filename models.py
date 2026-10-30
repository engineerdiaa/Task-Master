from datetime import date, datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

TASK_MAX_LENGTH = 200

# Stored as numbers so tasks can be sorted by priority.
PRIORITIES = {1: 'Low', 2: 'Medium', 3: 'High'}
DEFAULT_PRIORITY = 2


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(TASK_MAX_LENGTH), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now)
    completed = db.Column(db.Boolean, nullable=False, default=False,
                          server_default=db.false())
    due_date = db.Column(db.Date)
    priority = db.Column(db.Integer, nullable=False, default=DEFAULT_PRIORITY,
                         server_default=str(DEFAULT_PRIORITY))

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
