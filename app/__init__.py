"""Flask application factory, session security, JSON errors and local setup commands."""
import os
import secrets
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import click
import pymysql
from flask import Flask, g, jsonify, redirect, render_template, request, session
from flask.json.provider import DefaultJSONProvider
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash
from . import db
from .validation import Problem, customer_data, text

ROOT = Path(__file__).resolve().parent.parent


class JSONProvider(DefaultJSONProvider):
    @staticmethod
    def default(value):
        if isinstance(value, Decimal):
            return format(value, '.2f')
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return DefaultJSONProvider.default(value)


def load_environment():
    # No additional dotenv dependency. Values may be plain or quoted, one KEY=VALUE per line.
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('\"\''))


def create_app(overrides=None):
    load_environment()
    app = Flask(__name__)
    app.json_provider_class = JSONProvider
    app.json = JSONProvider(app)
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        DB_HOST=os.environ.get('DB_HOST', '127.0.0.1'),
        DB_PORT=int(os.environ.get('DB_PORT', '3306')),
        DB_USER=os.environ.get('DB_USER', 'sales_app'),
        DB_PASSWORD=os.environ.get('DB_PASSWORD', ''),
        DB_NAME=os.environ.get('DB_NAME', 'sales_inventory'),
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax',
        SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true',
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    if overrides:
        app.config.update(overrides)
    secret = app.config['SECRET_KEY']
    if not secret or len(secret) < 32 or secret.startswith('replace-'):
        raise RuntimeError('Set SECRET_KEY to a random value of at least 32 characters in .env.')
    app.teardown_appcontext(db.close_db)

    @app.before_request
    def load_user_and_protect():
        g.user = None
        if session.get('user_id'):
            g.user = db.query('SELECT id,name,email,role FROM users WHERE id=%s',
                              (session['user_id'],), one=True)
            if not g.user:
                session.clear()
        if request.path.startswith('/api/'):
            public = request.endpoint in ('api.session_info', 'api.login')
            if not public and not g.user:
                raise Problem('Please log in.', 401)
            if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                expected, supplied = session.get('csrf_token'), request.headers.get('X-CSRF-Token')
                if not expected or not supplied or not secrets.compare_digest(expected, supplied):
                    raise Problem('Invalid or missing CSRF token. Refresh and try again.', 403)

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; form-action 'self'"
        if not request.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.errorhandler(Problem)
    def problem(error):
        body = {'error': error.message}
        if error.details is not None:
            body['details'] = error.details
        return jsonify(body), error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(pymysql.IntegrityError)
    def integrity_error(error):
        if error.args[0] == 1062:
            return jsonify(error='A unique value already exists. Check the product code or email. No changes were saved.'), 409
        return jsonify(error='This record is referenced or violates a database constraint. Deactivate it instead of deleting.'), 409

    @app.errorhandler(pymysql.OperationalError)
    def database_error(error):
        app.logger.error('Database operation failed (code %s)', error.args[0])
        if error.args[0] in (1205, 1213):
            return jsonify(error='A conflicting update occurred. No changes were saved; retry the action.'), 409
        return jsonify(error='Database unavailable. Check local database setup.'), 503

    @app.errorhandler(Exception)
    def unexpected(error):
        app.logger.exception('Unexpected application error')
        return jsonify(error='An unexpected error occurred. Please try again.'), 500

    @app.get('/login')
    def login_page():
        return redirect('/') if g.user else render_template('login.html')

    @app.get('/')
    def home():
        return redirect('/orders')

    @app.get('/<any(orders,customers,products,reports):page>')
    def workspace(page):
        if not g.user:
            return redirect('/login')
        if page == 'reports' and g.user['role'] != 'Admin':
            raise Problem('Admin access is required.', 403)
        return render_template('workspace.html', page=page, user=g.user)

    from .routes import api
    app.register_blueprint(api)
    register_commands(app)
    return app


def run_sql_file(path):
    for statement in path.read_text().split(';'):
        if statement.strip():
            db.execute(statement)


def register_commands(app):
    @app.cli.command('init-db')
    def init_db():
        """Create the schema in an existing EMPTY MySQL database (never drop tables)."""
        if db.query('SHOW TABLES'):
            raise click.ClickException('Database is not empty. init-db never overwrites existing data.')
        run_sql_file(ROOT / 'sql' / 'schema.sql')
        db.get_db().commit()
        click.echo('Created all six tables and constraints.')

    @app.cli.command('create-user')
    @click.option('--name', required=True)
    @click.option('--email', required=True)
    @click.option('--role', type=click.Choice(['Admin', 'Sales User']), required=True)
    @click.option('--password-env', help='Read password from this environment variable instead of an interactive prompt.')
    def create_user(name, email, role, password_env):
        """Create a local account with a password chosen by you; hashes use scrypt."""
        checked = customer_data(dict(name=name, email=email, mobile='0000000000', city='Local'))
        password = os.environ.get(password_env) if password_env else click.prompt('Password', hide_input=True, confirmation_prompt=True)
        if not password or len(password) < 12:
            raise click.ClickException('Use a password of at least 12 characters.')
        with db.transaction():
            db.execute('INSERT INTO users (name,email,password_hash,role) VALUES (%s,%s,%s,%s)',
                       (checked['name'], checked['email'].lower(), generate_password_hash(password), role))
        click.echo(f'Created {role}: {checked["email"].lower()}')

    @app.cli.command('seed-sample')
    def seed_sample():
        """Load fictional master data into empty tables and representative orders."""
        from .services import save_order, transition_order
        admin = db.query("SELECT id,name,role FROM users WHERE role='Admin' ORDER BY id LIMIT 1", one=True)
        sales = db.query("SELECT id,name,role FROM users WHERE role='Sales User' ORDER BY id LIMIT 1", one=True)
        if not admin or not sales:
            raise click.ClickException('First create an Admin and a Sales User.')
        if db.query('SELECT id FROM customers LIMIT 1') or db.query('SELECT id FROM products LIMIT 1'):
            raise click.ClickException('Sample data requires empty customer and product tables.')
        with db.transaction():
            run_sql_file(ROOT / 'sql' / 'sample_data.sql')
        products = db.query('SELECT id FROM products ORDER BY id')
        customer = db.query('SELECT id FROM customers ORDER BY id LIMIT 1', one=True)
        payload = dict(customer_id=customer['id'], discount_percentage=10,
                       items=[dict(product_id=products[0]['id'], quantity=2),
                              dict(product_id=products[1]['id'], quantity=3)])
        confirmed = save_order(payload, sales)
        transition_order(confirmed['id'], 'confirm', sales)
        save_order(dict(payload, discount_percentage=0), sales)
        cancelled = save_order(dict(payload, items=[dict(product_id=products[1]['id'], quantity=1)]), admin)
        transition_order(cancelled['id'], 'cancel', admin)
        click.echo('Loaded fictional customers, products, opening movements, and three example orders.')
