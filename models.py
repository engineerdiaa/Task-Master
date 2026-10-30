from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

TASK_MAX_LENGTH = 200


class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(TASK_MAX_LENGTH), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.now)
    completed = db.Column(db.Boolean, nullable=False, default=False,
                          server_default=db.false())

    def __repr__(self):
        return '<Task %r>' % self.id
