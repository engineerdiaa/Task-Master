import re
from urllib.parse import urlsplit

from flask import (Blueprint, flash, redirect, render_template, request,
                   url_for)
from flask_login import LoginManager, current_user, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from models import USERNAME_MAX_LENGTH, Todo, User, db, save_changes

bp = Blueprint('auth', __name__)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to see your tasks.'
login_manager.login_message_category = 'info'

USERNAME_PATTERN = re.compile(r'[a-z0-9_.-]{3,%d}' % USERNAME_MAX_LENGTH)
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 200


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@bp.context_processor
def template_values():
    return {
        'USERNAME_MAX_LENGTH': USERNAME_MAX_LENGTH,
        'PASSWORD_MIN_LENGTH': PASSWORD_MIN_LENGTH,
        'PASSWORD_MAX_LENGTH': PASSWORD_MAX_LENGTH,
    }


def safe_next_url(target):
    """Return target if it is a path on this site, otherwise None.

    The login page sends people on to the "next" URL it was given. Only
    following local paths stops a link like /login?next=https://evil.example
    from sending someone to another site after they log in.
    """
    if not target or not target.startswith('/') or '\\' in target:
        return None
    parts = urlsplit(target)
    if parts.scheme or parts.netloc:
        return None
    return target


def check_new_account(username, password, confirm):
    """Return an error message for the registration form, or None."""
    if not USERNAME_PATTERN.fullmatch(username):
        return (f'Username must be 3-{USERNAME_MAX_LENGTH} characters: letters, '
                'numbers, dots, dashes or underscores.')
    if len(password) < PASSWORD_MIN_LENGTH:
        return f'Password must be at least {PASSWORD_MIN_LENGTH} characters.'
    if len(password) > PASSWORD_MAX_LENGTH:
        return f'Password must be {PASSWORD_MAX_LENGTH} characters or fewer.'
    if password != confirm:
        return "The two passwords don't match."
    if db.session.scalar(db.select(User.id).filter_by(username=username)):
        return 'That username is taken. Please choose another.'
    return None


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('tasks.index'))

    if request.method == 'POST':
        # Usernames are not case-sensitive: "Sam" and "sam" are the same.
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        error = check_new_account(username, password,
                                  request.form.get('confirm', ''))
        if error:
            return render_template('register.html', error=error,
                                   username=username), 400

        first_account = not db.session.scalar(db.select(User.id).limit(1))
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.flush()
        except IntegrityError:
            # Someone else took the name between the check and now.
            db.session.rollback()
            return render_template('register.html', username=username,
                                   error='That username is taken. Please choose another.'), 400

        adopted = 0
        if first_account:
            # Tasks made before accounts existed belong to the first account.
            adopted = db.session.execute(
                db.update(Todo).where(Todo.user_id.is_(None)).values(user_id=user.id)
            ).rowcount
        save_changes('create your account')

        login_user(user)
        flash(f'Welcome, {user.username}! Your account is ready.', 'success')
        if adopted:
            tasks = 'task was' if adopted == 1 else 'tasks were'
            flash(f'{adopted} existing {tasks} added to your account.', 'info')
        return redirect(url_for('tasks.index'))

    return render_template('register.html', username='')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    next_url = safe_next_url(request.args.get('next'))
    if current_user.is_authenticated:
        return redirect(next_url or url_for('tasks.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip().lower()
        password = request.form.get('password', '')
        user = db.session.scalar(db.select(User).filter_by(username=username))
        if user is None or not user.check_password(password):
            # Same message either way, so it doesn't reveal which usernames exist.
            return render_template('login.html', username=username, next_url=next_url,
                                   error='Wrong username or password.'), 400

        login_user(user, remember=bool(request.form.get('remember')))
        return redirect(next_url or url_for('tasks.index'))

    return render_template('login.html', username='', next_url=next_url)


@bp.route('/logout', methods=['POST'])
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
