# Task Master

A small to-do list web app built with [Flask](https://flask.palletsprojects.com/)
and [Flask-SQLAlchemy](https://flask-sqlalchemy.readthedocs.io/). Tasks are
stored in a SQLite database.

## Features

- Add, edit and delete tasks (1–200 characters; blank tasks are rejected)
- Mark tasks as done (and undo it); done tasks are crossed out
- See when each task was added

## Requirements

- Python 3.12 or newer

## Getting started

### Windows (PowerShell)

```powershell
python -m venv env
env\Scripts\activate
pip install -r requirements.txt
python app.py
```

### macOS / Linux

```bash
python3 -m venv env
source env/bin/activate
pip install -r requirements.txt
python app.py
```

Then open <http://127.0.0.1:5000> in your browser.

The database is created automatically the first time the app starts, at
`instance/test.db`. To start over with an empty list, stop the app and delete
that file.

You can also start the app with Flask's own command:

```bash
flask --app app run
```

## Debug mode

Debug mode reloads the app when you change the code and shows detailed error
pages in the browser. Those pages include a debugger that can run Python
code, so debug mode is off by default and must never be on when other people
can reach the app. Turn it on only while developing:

```powershell
# Windows (PowerShell)
$env:FLASK_DEBUG = "1"
python app.py
```

```bash
# macOS / Linux
FLASK_DEBUG=1 python app.py
```

Or use `flask --app app run --debug`.

## Settings

Settings are read from environment variables that start with `FLASK_`. For
example, to use a different database file:

```bash
FLASK_SQLALCHEMY_DATABASE_URI=sqlite:///other.db python app.py
```

## Project layout

```
app.py              Creates and configures the Flask app (create_app)
models.py           Database model (Todo)
tasks.py            Pages and actions for tasks (Flask blueprint)
migrations/         Database migrations (Flask-Migrate / Alembic)
templates/          HTML templates (Jinja)
static/css/         Stylesheet
requirements.txt    Python packages the app needs
```

## Changing the database

The app uses [Flask-Migrate](https://flask-migrate.readthedocs.io/) to keep
the database in step with the code. When the app starts it applies any
migrations the database is missing, so existing tasks are kept when new
columns are added.

If you change a model in `models.py`, create a migration for it:

```bash
flask --app app db migrate -m "Describe the change"
```

Check the new file in `migrations/versions/`, then start the app to apply it.

Because the app upgrades the database whenever it starts (including when you
run a `flask` command), a `flask db downgrade` is undone the next time the app
loads. To undo a migration, turn the automatic upgrade off for that command:

```bash
FLASK_AUTO_MIGRATE=false flask --app app db downgrade
```

On Windows PowerShell, run `$env:FLASK_AUTO_MIGRATE = "false"` first, then
the `flask` command. Remove the setting afterwards with
`Remove-Item Env:FLASK_AUTO_MIGRATE`.

## Updating requirements.txt

After installing a new package, save the list of packages with:

```bash
python -m pip freeze > requirements.txt
```

In Windows PowerShell 5, `>` saves the file as UTF-16, which GitHub shows as
a binary file. Use this instead:

```powershell
python -m pip freeze | Out-File -Encoding utf8 requirements.txt
```
