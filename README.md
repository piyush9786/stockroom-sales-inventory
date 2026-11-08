# Stockroom — Sales & Inventory Management

A local web application for managing customers, products, sales orders and stock.
Built for the **Savyant Systems Fresher / Trainee Software Developer assignment**.

**Stack:** Python with Flask, MySQL, HTML, CSS and plain JavaScript. The application
uses JSON REST APIs, PyMySQL for database access, Git for version control and pytest
for tests. No frontend framework, ORM, alternate database, container platform or
external service is required.

The interface includes a landing page, a gradient workspace and printable shop receipts
and A4 bills. These use the same application stack and six business entities.

- **Repository:** [stockroom-sales-inventory](https://github.com/piyush9786/stockroom-sales-inventory)
- **Submission folder:** `PiyushShinde_TechnicalAssignment`
- **Demo:** [6-minute application walkthrough](demo.mp4) · [video guide](docs/DEMO_GUIDE.md)

## Find what you need

- [Install and run locally](#local-setup)
- [Create login accounts](#6-create-login-accounts)
- [Try your first order](#using-the-application)
- [Roles and permissions](#roles-and-permissions)
- [Assumptions](#assumptions)
- [Limitations](#limitations)
- [Run the tests](#automated-tests)
- [Troubleshooting](#troubleshooting)
- [Submission contents](#submission-contents)

## Requirements

Install these before starting:

| Requirement | Supported / verified version |
| --- | --- |
| Python | Python 3.11–3.14; verified with 3.14.4 |
| MySQL Community Server | 8.0.16 or newer; 8.4 LTS recommended; verified with 8.4.11 |
| Git | Needed to clone the repository and inspect its history |
| Browser | A current browser supporting `fetch`, `<dialog>` and JavaScript `BigInt` |

MySQL must be running locally. Python packages are listed in `requirements.txt`;
`requirements-dev.txt` also installs the test tools. SQLite is not used.

## Local setup

Follow the steps in order. Run terminal commands from the project directory unless a
step says otherwise. The examples use a local MySQL server on port **3306** and the
application on port **5000**; change the configuration if your MySQL port differs.

### 1. Get the project

Clone the public repository:

```bash
git clone https://github.com/piyush9786/stockroom-sales-inventory.git
cd stockroom-sales-inventory
```

If you received the submission ZIP instead, extract it and open a terminal inside
`PiyushShinde_TechnicalAssignment`. Both options contain the same application files.
The submission ZIP also retains the `.git` history.

### 2. Create a Python environment and install packages

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

**Windows PowerShell:**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

After activation, `python` should refer to the project environment. The commands below
use that environment. Installing `requirements-dev.txt` includes everything needed to
run both the application and its tests; `requirements.txt` is sufficient to run only
the application.

### 3. Create the MySQL databases and database user

Open a MySQL administrator session, for example:

```bash
mysql -u root -p
```

Run the following **inside MySQL**, replacing `CHOOSE_A_LOCAL_DATABASE_PASSWORD` with
a password you choose. This is the database connection password, separate from the
application login passwords created in step 6.

```sql
CREATE DATABASE sales_inventory
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE sales_inventory_test
  CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;

CREATE USER 'sales_app'@'127.0.0.1'
  IDENTIFIED BY 'CHOOSE_A_LOCAL_DATABASE_PASSWORD';

GRANT ALL PRIVILEGES ON sales_inventory.*
  TO 'sales_app'@'127.0.0.1';
GRANT ALL PRIVILEGES ON sales_inventory_test.*
  TO 'sales_app'@'127.0.0.1';
```

Use `exit` to leave MySQL and return to your terminal. The first database stores
application data. The second is a separate, disposable database for automated tests.
These commands are for a fresh setup; if the databases or user already exist, check
that their settings and permissions match rather than deleting existing data.

### 4. Configure the application

Copy the example configuration:

**Linux / macOS:**

```bash
cp .env.example .env
```

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

Generate a random session secret:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Open `.env` in a text editor. Replace `SECRET_KEY` with the generated value and
`DB_PASSWORD` with the database password from step 3. Check these settings:

| Setting | What to enter |
| --- | --- |
| `SECRET_KEY` | The generated secret; at least 32 characters, not the example placeholder |
| `DB_HOST` | `127.0.0.1` for the local database user created above |
| `DB_PORT` | `3306`, or the port your MySQL server uses |
| `DB_USER` | `sales_app` |
| `DB_PASSWORD` | Your database connection password |
| `DB_NAME` | `sales_inventory` |
| `TEST_DB_NAME` | `sales_inventory_test`; reserved for tests |
| `SESSION_COOKIE_SECURE` | `false` for local HTTP; `true` requires HTTPS |
| `SHOP_NAME` | Optional bill heading; defaults to `The Trading Store` |
| `SHOP_ADDRESS`, `SHOP_PHONE` | Optional bill details; blank values are omitted |

The application reads `.env` itself. Existing operating-system environment variables
with the same names take precedence. Keep `.env` private; Git ignores it. Restart the
application after changing settings.

### 5. Create the application tables

Back in the terminal, with the Python environment active:

```bash
python -m flask --app app init-db
```

Expected message: `Created all six tables and constraints.`

The database must already exist and be empty. This command uses `sql/schema.sql` and
refuses to overwrite an existing database's tables. No migration service is required.
The test suite creates its own tables later; do not initialize the test database here.

### 6. Create login accounts

Create one Admin and one Sales User:

```bash
python -m flask --app app create-user --name "Demo Admin" --email admin@example.test --role Admin
python -m flask --app app create-user --name "Demo Sales" --email sales@example.test --role "Sales User"
```

Each command asks for a password and asks you to enter it again. Choose a password of
**at least 12 characters**. Nothing appears while you type; this is expected. The
application stores a scrypt password hash, not the password itself.

For checking ownership restrictions, optionally create a second Sales User:

```bash
python -m flask --app app create-user --name "Other Sales" --email other@example.test --role "Sales User"
```

| Login email | Role | Password |
| --- | --- | --- |
| `admin@example.test` | Admin | The password you chose for Demo Admin |
| `sales@example.test` | Sales User | The password you chose for Demo Sales |
| `other@example.test` | Sales User, optional | The password you chose for Other Sales |

These are fictional local accounts. There is no shared default login password.
New users are created through this command; there is no registration page.
For noninteractive setup, add `--password-env VARIABLE_NAME` to read the password
from an environment variable. Its value is not printed.

### 7. Load sample data — optional, recommended for review

Run this after creating the Admin and Sales User, **before manually adding customers
or products**:

```bash
python -m flask --app app seed-sample
```

Expected message: `Loaded fictional customers, products, opening movements, and three example orders.`

The command requires empty customer and product tables. It loads
`sql/sample_data.sql`: three customers, four products and opening stock movements.
It then uses the application's order logic to create one Confirmed order, one Draft
and one Cancelled order.

The Confirmed sample contains 2 Keyboards at ₹1,500.00 and 3 Mice at ₹500.00:

| Calculation | Amount |
| --- | ---: |
| Subtotal | ₹4,500.00 |
| Discount, 10% | ₹450.00 |
| Grand total | **₹4,050.00** |

After confirmation, Keyboard stock is **18** and Mouse stock is **47**. The Draft
reserves no stock; the Cancelled sample was cancelled from Draft and changes no stock.
Skip this step if you want to start with empty customer, product and order lists.

### 8. Start the application and sign in

```bash
python -m flask --app app run --host 127.0.0.1 --port 5000
```

Open **http://127.0.0.1:5000**. Use **Sign in / Enter your workspace**, then enter one
of the emails from step 6 and the password you chose for that account.

Keep the terminal running while using the application. Press **Ctrl+C** to stop it.
On a later visit, activate the same Python environment and run the start command
again. Database initialization, account creation and sample loading are one-time steps.

## Using the application

### Customers and products

- **Customers:** search by name, email or mobile. Admin can filter status, add, edit,
  deactivate and delete customers that have no orders. Sales Users see active customers.
- **Products:** search by code/name and filter by category/status. Admin can add, edit,
  deactivate or delete unreferenced products. Codes are unique without case sensitivity.
  Prices and stock cannot be negative; stock must be a whole number.
- **Stock adjustments:** Admin enters a positive or negative whole-number change and
  a reason. The resulting stock cannot be negative. Every accepted change is recorded.

### Create, confirm and cancel an order

1. Sign in and open **Orders**. Create an order for an active customer.
2. Add active products and enter positive whole-number quantities. Each product may
   appear once. Selecting a product fetches its current price and stock.
3. Enter a discount from **0% to 20%** and review the live totals.
4. Save the Draft. Save any later edits before confirming so the saved values are used.
5. Confirm the saved order. If any product has insufficient stock, the entire
   confirmation fails and stock remains unchanged.
6. Open the bill for a Confirmed order, or cancel the order when required.

| Order state / action | Stock effect | Can edit order contents? |
| --- | --- | --- |
| Save Draft | No stock reserved or deducted | Yes |
| Confirm Draft | Deduct all item quantities together | No, after confirmation |
| Cancel Draft | No stock change | No, after cancellation |
| Cancel Confirmed | Restore its deducted quantities once | No |
| Repeat an already completed confirm/cancel | No second stock change | No |

The browser previews totals, displays validation/API errors, asks before confirming or
cancelling, and disables pending actions. The server independently validates every
request and calculates all saved financial values.

### Print a shop receipt or A4 bill

For a **Confirmed** order, click **Bill** in the list or **Generate bill** in its detail
dialog. Choose **Shop receipt** or **A4 bill**, then **Print / Save PDF**. Select your
printer or the browser's **Save as PDF** destination.

Both layouts include shop details, a unique bill reference, order number/date,
customer, salesperson, product codes/names, quantities, saved rates/amounts, subtotal,
discount and grand total. Set the optional `SHOP_*` settings in `.env` to change the
shop heading/details, then restart. No contact details are invented for blank fields.

Viewing or printing a bill changes no stock, creates no sale and records no payment.
Draft and Cancelled bills are rejected with HTTP 409. Sales Users can view only their
own orders' bills. Saved rates/totals remain fixed; customer contact details and shop
settings reflect their current values. Browser printing adds no dependency.

### Import products from CSV — Admin only

Open **Products → Import CSV** and select a UTF-8 CSV file with exactly these six
column names, with no missing or additional columns:

```csv
product_code,product_name,category,price,stock_quantity,status
IMP-001,Keyboard,Accessories,1500,20,Active
IMP-002,Mouse,Accessories,500,50,Active
```

Use [the valid sample](samples/products_valid.csv) and
[the invalid sample](samples/products_invalid.csv) to try both outcomes. Status must
be `Active` or `Inactive`; duplicate codes and invalid/negative numeric values are
rejected. The `IMP-*` example codes avoid collisions with the seeded product codes.
Reimporting existing codes is rejected.

If any row is invalid, **the whole file is rejected** and physical line numbers and
reasons are shown. Successful imports create Opening movements for nonzero stock.

### Reports — Admin only

| Report | What it shows |
| --- | --- |
| Customer sales | Confirmed order count and net sales; inclusive order-date range; customers with zero matching sales remain visible |
| Product sales | Confirmed quantity sold and gross item value before order-level discounts |
| Low stock | Products with stock strictly below the entered threshold |
| Stock movements | Product, movement type, signed quantity, related order, reason, user and UTC time |

Draft and Cancelled orders do not count as sales. Customer sales totals use orders
directly, avoiding duplicated totals caused by joining order items.

## Roles and permissions

| Action | Admin | Sales User |
| --- | --- | --- |
| View customers/products | All, with filters | Active records only |
| Add, edit or delete customers/products | Yes, with reference checks | No |
| Adjust stock or import CSV | Yes | No |
| Create orders | Yes | Yes |
| Read, edit Draft, confirm or cancel orders | All orders | Own orders only |
| Generate bills | Any Confirmed order | Own Confirmed orders only |
| View reports | Yes | No |

Permissions are enforced by the backend, including every order-ID operation. Changing
a URL or calling an API directly does not bypass ownership or role checks.

Protected pages redirect to login; unauthenticated JSON API requests return 401.
Passwords use Werkzeug scrypt hashing. Sessions use signed, HTTP-only, SameSite=Lax
cookies and expire after eight hours. Logout clears the session. Mutating API calls,
including login, require a per-session CSRF token; login rotates it. Database queries
bind parameters, rendered text is escaped, and JSON errors omit secrets, password
hashes and internal tracebacks.

## Assumptions

- **Scope:** one stock location, one currency (**INR**, a display choice) and whole-number
  quantities. Taxes, delivery, purchasing and payment processing are excluded as instructed.
- **Order selection:** customers/products must be active when saving a Draft. Inactive
  products also prevent confirmation. Cancelling an existing Confirmed order still restores
  its stock, including products that have since been deactivated.
- **Pricing:** rates come from the database. Existing Draft rows keep their saved rate when
  quantities change; newly added products use their current price. Browser-supplied rates,
  totals, creator and status cannot override server values.
- **Money:** Python `Decimal` and MySQL `DECIMAL(16,2)` are used. Prices/discount inputs
  accept at most two decimal places. Money rounds to two places using `ROUND_HALF_UP`.
  Item amount is quantity × rate; subtotal is the sum of item amounts. The percentage
  discount is rounded once, then subtracted from subtotal to obtain the grand total.
- **Dates:** order dates contain no time; report date ranges include both endpoints.
  Stock movement timestamps use UTC.
- **Identifiers:** order numbers are UUID-based and unique. Product codes allow ASCII
  letters, numbers, hyphens and underscores, up to 50 characters. Master fields have
  schema-aligned length limits; customer email and mobile values are validated.
- **History:** customer deletion is blocked by any order; product deletion is blocked by
  any order item or stock movement. Deactivate referenced records to preserve history.
- **Opening stock:** zero stock produces no Opening movement because no stock changed.

## Limitations

- **Local demonstration:** the app uses Flask's local development server. Public hosting
  is optional for the assignment; a production deployment is not included.
- **Account management:** users are created through the command line. Self-registration
  and password recovery are not implemented.
- **Capacity limits:** at most 100 different products per order; quantity/stock up to
  2,000,000,000; supported calculated money up to 999,999,999,999.99. Overflows are rejected.
- **CSV/request size:** at most 5,000 product rows and 2 MB for the complete HTTP request,
  including the upload. Blank physical CSV lines are ignored. A malformed multi-line
  record identifies its ending physical line. A concurrent duplicate-code import returns
  409 with the conflicting row number and rolls back the file.
- **Printing:** shop receipts use an 80 mm layout with a suggested 80 × 297 mm page; A4
  is also available. Browser paper/printer settings can override the suggested sizes.
  Bills are sales summaries, without added tax, accounting or payment functionality.
- **Verification scope:** tests cover the documented behavior; no performance claim is
  made for unspecified production loads.

No required assignment feature is intentionally deferred. Review
[the requirement-by-requirement checklist](docs/REQUIREMENTS.md) for implementation
evidence and [AI_USAGE.md](AI_USAGE.md) for the assistance disclosure.

## Automated tests

Complete setup through step 4 and install `requirements-dev.txt`. Tests use the same
`DB_HOST`, `DB_PORT`, `DB_USER` and `DB_PASSWORD`, but connect to `TEST_DB_NAME`.

**The full suite drops and recreates its six tables in the test database.** Use a
disposable database: its name must end in `_test` and must differ from `DB_NAME`.
The fixture enforces both checks. Do not point it at data you want to keep. Tests create
their own accounts/data; application sample accounts are not needed.

```bash
# Calculation/debugging tests only; no database connection needed:
python -m pytest tests/test_calculations.py -q

# Full suite using the separate real MySQL database:
python -m pytest -q
```

Latest recorded full result: **70 passed in 13.04 seconds**, on 8 November 2026.
The development environment disabled unrelated globally installed pytest plugins;
a fresh virtual environment uses the normal command above. See
[the verification record](docs/VERIFICATION.md) for the environment and checks.

Coverage includes all nine required scenarios, competing confirmations/retries,
stock movements, saved prices, Draft editing/cancellation, duplicate/empty items,
master validation/deletion, roles/ownership, CSRF/login/logout, pagination/search,
atomic CSV imports, reports and bills. Integration tests use actual MySQL transactions
and separate connections; stock/database results are not replaced by SQLite or mocks.

## Project structure and database design

```text
app/
  __init__.py       App setup, configuration, page routes and setup commands
  routes.py         JSON endpoints, authentication and permission checks
  services.py       Order lifecycle, stock adjustments and transactions
  db.py             MySQL connections and parameterized queries
  validation.py     Shared validation and Decimal calculations
  csv_import.py     All-or-nothing product imports
  templates/        Landing, login, workspace and printable bill pages
  static/           Plain JavaScript and CSS
sql/                Schema, sample data and five standalone report queries
samples/            Valid and invalid product CSV files
tests/              Calculation and real-MySQL integration tests
docs/               API, requirements, debugging, demo and verification guides
.env.example        Local configuration template; no real credentials
demo.mp4            Six-minute application walkthrough
AI_USAGE.md         AI assistance disclosure
```

There are exactly six business entities:

| Entity | Purpose and relationships |
| --- | --- |
| User | Unique email, role and password hash; creates orders and stock movements |
| Customer | Has many orders; status allows deactivation |
| Product | Unique code, category, decimal price, whole-number stock and status |
| Sales Order | Customer/creator foreign keys, unique order number, date, state and saved totals |
| Sales Order Item | Order/product foreign keys; unique product per order, positive quantity, saved rate and amount |
| Stock Movement | Product/creator foreign keys, optional related order, signed change, type, reason and UTC timestamp |

All tables use InnoDB, foreign keys and CHECK constraints. References use
`ON DELETE RESTRICT`. Indexes cover status/category, stock, creator, customer,
status/date, order-item products and movement product/time. Unique keys protect emails,
product codes, order numbers, duplicate products and duplicate stock events.

**Stock consistency:** a transition starts one transaction, locks the order with
`SELECT ... FOR UPDATE`, checks its latest status/owner, then locks products in
increasing primary-key order. It validates every quantity before changing stock.
Stock updates, movement inserts and order status commit together, or all roll back.
Competing confirmations/adjustments wait for the same locks and then read committed
stock. The order lock serializes retries; a unique movement key adds protection.
Deadlocks/lock timeouts roll back and return retryable HTTP 409. Drafts reserve no stock.
See [MySQL's locking-read guidance](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html).

## API documentation

[docs/API.md](docs/API.md) explains authentication/CSRF, permissions, endpoint payloads,
example requests/responses, pagination and HTTP errors. The web interface uses these
same JSON APIs.

The five standalone queries in [sql/report_queries.sql](sql/report_queries.sql) cover
top customers, top products, never-ordered customers, year/month sales and low stock.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `python` or `py` is not found | Install a supported Python version. Use `python3` on Linux/macOS or `py -3` on Windows to create the environment. |
| PowerShell blocks activation | Use `.venv\Scripts\python.exe` in place of `python` in the install/setup/run commands; activation is not required when using that executable directly. |
| MySQL connection refused | Start MySQL and check `DB_HOST`/`DB_PORT` in `.env`. |
| MySQL access denied | Match the password from step 3, use `DB_USER=sales_app` and `DB_HOST=127.0.0.1`, and check database grants. |
| Unknown database | Create the database in step 3 and match `DB_NAME` or `TEST_DB_NAME`. |
| `Set SECRET_KEY...` error | Replace the example secret with the generated value, at least 32 characters. Check for an overriding environment variable. |
| `Database is not empty` | Tables already exist. Skip `init-db` for that database; it will not overwrite your data. |
| Sample loading is rejected | Create an Admin and Sales User first; customer/product tables must be empty. Skip seeding if you already entered data. |
| Login fails | Use an account created in step 6 and its chosen password, not the database password. There is no default password. |
| Login does not stay active on local HTTP | Keep `SESSION_COOKIE_SECURE=false` locally and restart after changing it. |
| Port 5000 is in use | Start with `--port 5002` instead and open `http://127.0.0.1:5002`. |
| Stock confirmation fails | Check available quantities and product status. A failed confirmation leaves the order Draft and changes no stock. |
| CSRF error | Refresh the page and retry. Direct API clients must follow the token flow in `docs/API.md`. |
| Test database guard fails | Use a separate `TEST_DB_NAME` ending in `_test`; it must differ from `DB_NAME`. |

## Submission contents

| Required deliverable | Location |
| --- | --- |
| Complete source and Git history | `app/`, `tests/`, repository history; `.git/` retained in the submission ZIP |
| Database schema and sample data | [schema.sql](sql/schema.sql), [sample_data.sql](sql/sample_data.sql), `seed-sample` command |
| Setup, account creation, assumptions and limitations | This README and [.env.example](.env.example) |
| API examples | [docs/API.md](docs/API.md) |
| Five SQL queries | [sql/report_queries.sql](sql/report_queries.sql) |
| Valid and invalid CSV | [samples/](samples/) |
| Automated tests and instructions | [tests/](tests/) and the Automated tests section above |
| Debugging fix, explanation and tests | [validation.py](app/validation.py), [docs/DEBUGGING.md](docs/DEBUGGING.md), [test_calculations.py](tests/test_calculations.py) |
| AI usage disclosure | [AI_USAGE.md](AI_USAGE.md) |
| 5–8 minute demo | Git-tracked [demo.mp4](demo.mp4), verified as 6 minutes; [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) |

[docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) maps all 14 assignment parts and the
interview/instruction notes. The history includes meaningful commits and the merged
`feature/product-csv-import` and `feature/landing-and-shop-bills` branches:

```bash
git log --graph --oneline --all
```

Real credentials, `.env`, virtual environments and dependency downloads are excluded
from Git and the submission ZIP. The repository URL or a Git archive retaining history
satisfies the PDF; public hosting is optional. Use the submission name
`PiyushShinde_TechnicalAssignment` and submit within **three calendar days of receipt**.
Sending the submission remains the candidate's responsibility.

AI assisted extensively with this project, as disclosed in `AI_USAGE.md`. Before
submission or interview, personally review, run and practise explaining the solution.
[docs/INTERVIEW_GUIDE.md](docs/INTERVIEW_GUIDE.md) provides code locations, business-flow
explanations, a demo sequence and small live-change exercises.
