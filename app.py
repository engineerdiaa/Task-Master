import os

from flask import Flask, render_template
from flask_migrate import Migrate, upgrade
from werkzeug.exceptions import HTTPException

import tasks
from models import TASK_MAX_LENGTH, db

migrate = Migrate()


def create_app(test_config=None):
    """Create and configure the app.

    Any setting can be changed with an environment variable that starts
    with FLASK_, for example FLASK_DEBUG=1. Tests pass their own settings
    in test_config.
    """
    app = Flask(__name__)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI='sqlite:///test.db',
    )
    app.config.from_prefixed_env()
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db, directory=os.path.join(app.root_path, 'migrations'))
    app.register_blueprint(tasks.bp)
    app.register_error_handler(HTTPException, handle_http_error)
    app.jinja_env.globals['TASK_MAX_LENGTH'] = TASK_MAX_LENGTH

    # Create the database tables, or bring an older database up to date.
    with app.app_context():
        upgrade()

    return app


def handle_http_error(error):
    return render_template('error.html', error=error), error.code


if __name__ == '__main__':
    # Debug mode stays off unless FLASK_DEBUG=1 is set.
    create_app().run()
