# Sales Order & Inventory Management

Fresher / Trainee Software Developer technical assignment for Savyant Systems.
Submission folder: **PiyushShinde_TechnicalAssignment**.

The application manages customers, products, multi-item sales orders and stock.
It uses **Python / Flask, HTML, CSS, plain JavaScript, MySQL, REST JSON APIs and Git**.
PyMySQL is the database driver; pytest runs the automated tests. There is no frontend
framework, ORM, alternate database, container platform or external service requirement.

The **Stockroom** interface includes a public landing page, a purple gradient theme,
and shop-style printable sales bills. These additions use the same stack and database.

## 1. Requirements

- Python **3.11-3.14**; verified with Python 3.14.
- MySQL **8.0.16 or newer**, preferably the 8.4 LTS series. Verified with MySQL 8.4.11.
- Git and a current browser supporting `fetch`, `<dialog>` and JavaScript `BigInt`.
- Python packages in `requirements.txt`; development tests in `requirements-dev.txt`.

## 2. Local setup

Start your local MySQL service first. In a MySQL administrator session, create two
databases and a local application account. Replace the password placeholder yourself:

```sql
CREATE DATABASE sales_inventory CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE DATABASE sales_inventory_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'sales_app'@'127.0.0.1' IDENTIFIED BY 'REPLACE_WITH_YOUR_LOCAL_PASSWORD';
GRANT ALL PRIVILEGES ON sales_inventory.* TO 'sales_app'@'127.0.0.1';
GRANT ALL PRIVILEGES ON sales_inventory_test.* TO 'sales_app'@'127.0.0.1';
```

From the submission directory:

```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell instead:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

Copy `.env.example` to `.env` (Windows: `Copy-Item .env.example .env`). Set the database
password and connection details. Generate a session secret with this command and paste
the result as `SECRET_KEY` in `.env`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
python -m flask --app app init-db
```

`init-db` requires an **existing, empty database** and refuses to overwrite tables.
`sql/schema.sql` is the complete schema; no migration service is needed. The app reads
`.env` itself. Environment variables take precedence over the file. Do not commit `.env`.

### Sample accounts and data

Create these fictional accounts, choosing a local password of at least 12 characters
at each hidden prompt. No fixed password or real credential is committed:

```bash
python -m flask --app app create-user --name "Demo Admin" --email admin@example.test --role Admin
python -m flask --app app create-user --name "Demo Sales" --email sales@example.test --role "Sales User"
python -m flask --app app create-user --name "Other Sales" --email other@example.test --role "Sales User"
python -m flask --app app seed-sample
python -m flask --app app run --host 127.0.0.1 --port 5000
```

Open **http://127.0.0.1:5000** and sign in with an account/password you just created.
For noninteractive local setup, `create-user --password-env VARIABLE_NAME` reads a
password from that environment variable. The variable's value is never printed.

`seed-sample` requires empty customer/product tables and an Admin plus Sales User.
It loads `sql/sample_data.sql`: three customers, four products and opening movements.
It then creates one Confirmed, one Draft and one Cancelled example order through the
same business logic as the API. The Confirmed sample has subtotal 4,500.00, discount
450.00 and grand total **4,050.00**. Its Keyboard/Mouse stock becomes 18/47.

## 3. Using the application

- **Customers:** search name/email/mobile; Admin can filter status, create, edit,
  deactivate, or delete an unreferenced customer. Sales Users see active records only.
- **Products:** search code/name and filter category/status. Admin can create/edit,
  deactivate, import CSV, and adjust stock with a mandatory reason. Product codes are
  unique without case sensitivity. Negative prices/stock and fractional stock are rejected.
- **Sales orders:** select an active customer and add active products. Selection fetches
  current price and stock. Add/remove rows and change quantities while Draft. The browser
  previews totals and prevents duplicate submissions; the server independently validates
  all fields and recalculates all saved money. Save Draft before confirming saved values.
- **Confirm:** asks for confirmation, verifies every stock quantity, then deducts stock
  and records movements. **Cancel:** asks for confirmation and restores stock only if the
  order was Confirmed. Confirmed/Cancelled order contents cannot be edited. Repeated
  requests for the same state succeed without applying stock twice.
- **Reports (Admin):** customer sales with inclusive order-date range and zero-sales
  customers; product gross sales; stock strictly below an entered threshold; stock
  movement history showing product, movement, signed quantity, order, reason, user and UTC time.
- **CSV (Admin):** upload the required six columns. Invalid rows display physical CSV
  line numbers and reasons. Any error rolls back the whole file. Nonzero opening stock
  creates an Opening movement. Examples: `samples/products_valid.csv` and
  `samples/products_invalid.csv`. Imported codes use IMP-* to avoid seed-code collisions;
  the header and example Keyboard/Mouse values follow the assignment format.

### Landing page and shop bills

The home URL `/` is a public landing page. Use **Sign in / Enter your workspace** to
open the protected application. The sidebar logo and **Visit home page** return home.

For a **Confirmed** order, click **Bill** in the order list or **Generate bill** in its detail
dialog. Choose **Shop receipt** (80 mm wide) or **A4 bill**, then **Print / Save PDF**.
Choose your printer or the browser's **Save as PDF** destination. Both layouts show the
shop name, unique bill reference, order number/date, customer, salesperson, product
codes/names, quantities, saved rates/amounts, subtotal, discount and grand total in INR.
The shop name defaults to the clearly generic `The Trading Store`; optionally set
`SHOP_NAME`, `SHOP_ADDRESS`, and `SHOP_PHONE` in `.env`, then restart the application.
Empty address/phone fields are omitted, so no contact details are invented.

Bills are read-only views of Confirmed orders: viewing/printing does not create another
sale, deduct stock or record a payment. Draft and Cancelled orders return 409, and Sales
Users can only access their own orders' bills. Monetary values come from the saved order,
including rate snapshots; customer/shop contact details come from current master/configuration
data. This is not an added accounting or payment system. Browser paper/printer settings can
override the suggested print sizes; the receipt stylesheet suggests 80 x 297 mm paper.
Printing and PDF saving use the browser's native dialog, with no added dependencies.

## 4. Roles and security

| Role | Backend-enforced permissions |
| --- | --- |
| Admin | Modify customers/products, adjust stock, manage every order, view reports, import CSV |
| Sales User | View active customers/products; create, read, edit Draft, confirm and cancel their own orders |

Authenticated pages redirect to login. JSON endpoints return 401 when unauthenticated.
Every order-ID operation checks ownership, including edits, confirmations and cancellations.
Passwords use Werkzeug's **scrypt** password hashing. Session cookies are HTTP-only,
SameSite=Lax, signed with your secret, and expire after eight hours. Logout clears the
session. Every mutating API call, including login, requires a per-session CSRF token.
Login rotates the session token. SQL parameters are bound, and rendered data is escaped.
JSON errors never expose password hashes, secrets or internal tracebacks.

## 5. Database design and stock consistency

There are exactly six business entities:

| Entity | Relationships / decisions |
| --- | --- |
| User | Unique email; role; scrypt hash. One user creates many orders/movements. |
| Customer | One customer has many orders. Status supports safe deactivation. |
| Product | Unique code; category; DECIMAL price; whole-number stock; active status. |
| Sales Order | Customer and creator foreign keys; unique UUID-based order number; date/status; persisted Decimal totals. |
| Sales Order Item | Belongs to one order and one product. Unique (order, product); positive quantity; snapshot rate and amount. |
| Stock Movement | Product and creator foreign keys; optional related order; signed change, type, reason and UTC timestamp. |

Money uses `DECIMAL(16,2)` in MySQL and Python `Decimal`. All amounts and discount
amounts round to two decimals using **ROUND_HALF_UP**. Price and discount inputs accept
at most two fractional decimals. Rates come from the database, never the browser.
Existing draft rows retain their saved rates when quantities change; newly added products
use their current prices. Browser-supplied rates, totals, status and creator cannot override
the server. An order needs at least one item and discount must be **0-20% inclusive**.

`quantity * rate = amount`; item amounts sum to subtotal; `subtotal * discount / 100`
is rounded once to discount amount; grand total is subtotal less discount amount.

All tables use **InnoDB** with foreign keys and CHECK constraints. Foreign keys use
`ON DELETE RESTRICT`: any order prevents customer deletion; any order item or stock
movement prevents product deletion. Deactivation preserves these references. Useful
indexes cover status/category, stock, creator, customer, status/date, product items and
movement product/time. Unique keys protect emails, product codes, order numbers and
duplicate products/events.

Each order transition begins one transaction, locks the order with `SELECT ... FOR UPDATE`,
checks the latest status/owner, then locks product rows **in increasing primary-key order**.
It validates all stock before updating any row. Stock updates, movement inserts and the
order status commit together. Failure rolls everything back. Other confirmations or stock
adjustments wait for the same row locks and read the committed stock before deciding.
The order lock serializes retries; a unique order/product/movement key is an additional
guard. Deadlocks/lock timeouts roll back and return a retryable 409. Drafts reserve no stock.
This follows [MySQL's locking-read guidance](https://dev.mysql.com/doc/refman/8.4/en/innodb-locking-reads.html).

Customer summary joins orders directly, never item rows, avoiding duplicated order totals.
Date and Confirmed filters are in the LEFT JOIN so customers with zero matching orders
remain. Product sales sums item amounts **before order-level discount**. Cancelled and
Draft orders contribute to neither sales summary. Standalone queries are in
`sql/report_queries.sql` (all five requested queries).

## 6. API documentation

See **[docs/API.md](docs/API.md)** for authentication, endpoint permissions, validation,
example requests/responses and HTTP errors. The web interface calls these same APIs.

## 7. Automated tests

Install `requirements-dev.txt`, create the separate `sales_inventory_test` database,
and set `TEST_DB_NAME` in `.env`. Test credentials come from the same DB_* connection
settings. The test suite **drops/recreates its six tables in that test database**, never
the application database. A guard requires its name to end in `_test` and differ from DB_NAME.

```bash
# Pure calculation/debugging tests, no database needed:
python -m pytest tests/test_calculations.py -q
# Complete suite, including real MySQL transactions and simultaneous requests:
python -m pytest -q
```

Tests cover the nine mandatory scenarios, actual parallel confirmations/retries, stock
movements, snapshot pricing, Draft editing/cancellation, duplicate/empty items, master
data validation/deletion, role restrictions, CSRF/login/logout, pagination/search, all-or-nothing
CSV import and sales/stock reporting. The tests do not replace MySQL with SQLite or mocks.
See [docs/VERIFICATION.md](docs/VERIFICATION.md) for the recorded execution results.

## 8. Assumptions and limits

- One currency (**INR**, display choice) and one stock location. Whole-number quantities.
- Taxes, delivery, purchasing and payment processing are outside scope, as instructed.
- A customer/product must be active when selected for a Draft. An inactive product also
  prevents confirmation; cancelling a previously Confirmed order still restores it.
- Order-date ranges are inclusive. Movement timestamps are UTC; order dates are date-only.
- Product code is an ASCII letter/number/hyphen/underscore identifier, max 50 characters.
  Master fields have schema-aligned length limits and customer email/mobile are validated.
- Maximum stock/quantity is 2,000,000,000; supported calculated money is at most
  999,999,999,999.99; an order supports 100 products. CSV supports 5000 rows and the
  complete upload/request limit is 2 MB. Overflows are rejected explicitly.
- A zero opening quantity has no stock change, so no Opening movement is added for zero.
- A unique-code collision caused by a concurrent import returns 409 with the row number
  and rolls back the file. Malformed multi-line records identify their
  ending physical line. Blank physical CSV lines are ignored by the CSV parser.
- Users are created through the CLI. Registration, password recovery and public hosting
  are outside the requested scope. The Flask local development server is used for the demo.
- No incomplete required application feature is intentionally deferred. The candidate must
  personally review and understand the solution before submitting or demonstrating it.

## 9. Submission contents

| Required deliverable | Location |
| --- | --- |
| Complete Python/JavaScript source and Git history | `app/`, `tests/`, `.git/` in the submission archive |
| Schema and sample data | `sql/schema.sql`, `sql/sample_data.sql`, `seed-sample` command |
| Setup/accounts/design/assumptions/limitations | This README and `.env.example` |
| API examples | `docs/API.md` |
| Five SQL queries | `sql/report_queries.sql` |
| Valid and invalid CSV | `samples/` |
| Automated tests and instructions | `tests/`, section 7 |
| Corrected debugging exercise/explanation/tests | `app/validation.py`, `docs/DEBUGGING.md`, `tests/test_calculations.py` |
| AI usage disclosure | `AI_USAGE.md` |
| 5-8 minute working demo | Git-tracked `demo.mp4` included in the submission archive; `docs/DEMO_GUIDE.md` |

`docs/REQUIREMENTS.md` maps all 14 parts and the interview/instruction notes to the
implementation. The Git history contains meaningful development commits and the
merged `feature/product-csv-import` and `feature/landing-and-shop-bills` branches.
Inspect with `git log --graph --oneline --all`.
No real credentials, environment, virtual environment or dependency downloads are in Git.
The repository archive retains `.git` so no hosted repository is required. Public hosting
is optional. The assignment deadline is **within three calendar days of receipt**; the
candidate is responsible for submitting the named archive within that deadline.

For interview preparation, see `docs/INTERVIEW_GUIDE.md`: business-flow explanations,
code locations, the demonstration sequence and practical live-change exercises.
