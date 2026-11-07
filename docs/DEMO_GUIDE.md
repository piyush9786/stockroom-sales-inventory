# Working application demonstration

The submission archive includes `demo.mp4`, a 5-8 minute screen recording of the actual
Flask/MySQL application. It uses fictional local data and accounts. Captions explain the
actions; the recording has no spoken narration. Recording tools are not app dependencies.

Verified duration: **5 minutes 55 seconds** (355.2 seconds), within the required 5-8
minutes. The recording completed with no capture errors and no application JavaScript
runtime errors.

The demo covers:

1. Admin login and the orders workspace.
2. Customer creation/search/editing and status filtering.
3. Product creation/editing, stock adjustment with reason, and category/code search.
4. Invalid CSV row errors with no imported products, followed by a valid CSV import.
5. Multi-item Draft creation with live amounts and a 10% discount; stock unchanged.
6. Confirmation and stock deduction; Confirmed contents read-only.
7. Cancellation and stock restoration; Cancelled contents read-only.
8. Insufficient stock rejection without partial confirmation.
9. Customer/product sales, low stock and movement history reports.
10. Sales login, active-only master access, own-order visibility and backend denial of
    another user's order; logout.

Still previews from the recording are provided in `order-editor.png` and
`stock-history.png` in this documentation directory.

For a personal narrated replacement, create sample users/data following the README and
record those same flows in 5-8 minutes. Also be ready to explain the real-MySQL
concurrency tests, row-lock ordering, Decimal rounding, snapshots and Git history.
