# Task Master

A small to-do list web app built with [Flask](https://flask.palletsprojects.com/)
and [Flask-SQLAlchemy](https://flask-sqlalchemy.readthedocs.io/). Tasks are
stored in a SQLite database.

## Features

- Add, edit and delete tasks
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

## Project layout

```
app.py              The Flask app: database model and routes
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

If you change the model in `app.py`, create a migration for it:

```bash
flask --app app db migrate -m "Describe the change"
```

Check the new file in `migrations/versions/`, then start the app to apply it.

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
