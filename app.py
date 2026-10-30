import os
import re
import secrets

from flask import Flask, render_template
from flask_migrate import Migrate, upgrade
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

import auth
import tasks
from models import db

migrate = Migrate()
# Every POST form must include a csrf_token field, so other websites
# can't submit forms on a logged-in user's behalf.
csrf = CSRFProtect()


def create_app(test_config=None):
    """Create and configure the app.

    Any setting can be changed with an environment variable that starts
    with FLASK_, for example FLASK_DEBUG=1. The database can also be set
    with DATABASE_URL, as hosting services do. Tests pass their own
    settings in test_config.
    """
    app = Flask(__name__)
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=database_url_from_env() or 'sqlite:///test.db',
        # Bring the database up to date every time the app starts.
        AUTO_MIGRATE=True,
        # Set when a hosting service's proxy sits in front of the app.
        BEHIND_PROXY=False,
    )
    app.config.from_prefixed_env()
    if test_config:
        app.config.update(test_config)
    if not app.config['SECRET_KEY']:
        app.config['SECRET_KEY'] = instance_secret_key(app)
    if app.config['BEHIND_PROXY']:
        # The proxy handles HTTPS and passes the visitor's details in
        # X-Forwarded-* headers; trust one proxy's worth of them.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    db.init_app(app)
    migrate.init_app(app, db, directory=os.path.join(app.root_path, 'migrations'))
    csrf.init_app(app)
    auth.login_manager.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(tasks.bp)
    app.register_error_handler(HTTPException, handle_http_error)
    app.register_error_handler(CSRFError, handle_csrf_error)

    if app.config['AUTO_MIGRATE']:
        # Create the database tables, or bring an older database up to date.
        with app.app_context():
            upgrade()

    return app


def database_url_from_env():
    """Return DATABASE_URL, ready for SQLAlchemy, or None if it isn't set.

    Hosting services give PostgreSQL URLs starting with postgres:// or
    postgresql://; SQLAlchemy needs postgresql+psycopg:// to use the
    psycopg (version 3) driver.
    """
    url = os.environ.get('DATABASE_URL')
    if not url:
        return None
    return re.sub(r'^postgres(ql)?://', 'postgresql+psycopg://', url)


def instance_secret_key(app):
    """Return a random secret key saved in the instance folder, creating it
    the first time. The key signs the session cookie, which holds who is
    logged in, so it must stay private: instance/ is not in git."""
    path = os.path.join(app.instance_path, 'secret_key')
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()

    key = secrets.token_hex(32)
    os.makedirs(app.instance_path, exist_ok=True)
    with open(path, 'w') as f:
        f.write(key)
    return key


def handle_http_error(error):
    return render_template('error.html', error=error), error.code


def handle_csrf_error(error):
    error.description = ('This form has expired or was sent from another site. '
                         'Go back, reload the page and try again.')
    return handle_http_error(error)


if __name__ == '__main__':
    # Debug mode stays off unless FLASK_DEBUG=1 is set.
    create_app().run()
