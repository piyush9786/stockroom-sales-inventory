# Verification record

Verified on **7 November 2026 (Asia/Kolkata)** in the development environment.

## Runtime

- Python 3.14.4; Flask 3.1.3; PyMySQL 1.1.3; Werkzeug 3.1.9; pytest 9.2.0.
- Actual MySQL Community Server **8.4.11**, InnoDB, utf8mb4; no substitute database.
- Google Chrome 153 for browser checks. Browser/recording tools are development tools,
  not application runtime dependencies or additional product technologies.

## Automated result

**65 passed in 11.15 seconds.** The final run had no warnings.

The complete suite exercised real MySQL transactions and foreign keys in a separate,
disposable test database. It includes the assignment's nine required scenarios and
checks actual competing confirmations/retries using separate connections. Concurrent
CSV imports were synchronized after their real database validation reads; exactly one
committed, and the other rolled back with its conflicting row number. No database
query results or stock operations were mocked.

The development environment also contained unrelated global pytest plugins; the final
run disabled automatic discovery of those plugins. A normal fresh virtual environment
installed from `requirements-dev.txt` needs only the README's `python -m pytest -q`.

## Browser workflows checked

- Admin login, session restoration and logout.
- Customer create, search and edit.
- Dynamic product rows, asynchronous current price/stock, item quantities and live totals.
- The assignment's Keyboard x2 and Mouse x3 example: subtotal 4,500.00, 10% discount
  450.00, total **4,050.00** in both preview and saved server response.
- Draft save, Confirmed read-only contents, cancellation and Cancelled read-only contents.
- Invalid CSV shows row errors; the valid sample successfully imports two products.
- Customer/product/report screens; Sales User screens hide Admin operations.
- A 390 x 844 mobile viewport and 1440 x 1000 desktop viewport were visually inspected.
  Wide data tables remain horizontally scrollable on small screens.
- The checked application flows produced **zero application JavaScript runtime errors**.

## Other checks

- All five statements in `sql/report_queries.sql` executed successfully in MySQL against
  seeded data. Customer sales were 4,050.00 and top product quantities were 3 and 2.
- Python compilation, JavaScript syntax checking and Git whitespace checks passed.
- The repository includes a real feature branch and merge commit, not a fabricated log.
- Git-tracked files exclude `.env`, local credentials, environments and temporary downloads.

The demo recording and final archive are verified separately during packaging; their
completion details are recorded in `docs/DEMO_GUIDE.md`. Tests verify behavior under the
documented limits; this record does not assert performance at unspecified production loads.
