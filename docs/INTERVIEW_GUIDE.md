# Explain and demonstrate the project

Use this as a study guide. Practise the explanations in your own words and make the
small changes yourself; a guide cannot replace your understanding of the submitted code.

## Start with the business flow

"This is a Flask and MySQL application for a small trading company. Admin maintains
customers/products and adjusts stock. Sales Users manage their own orders. A Draft
does not affect stock. Confirmation validates all quantities and updates stock, order
status and movement history in one transaction. A confirmed order can be cancelled,
which restores stock once. Sales reports count Confirmed orders only."

The landing page and gradient theme are presentation additions. The printable bill
reads saved order values; it does not create a second sale or record a payment.

## The questions you should be able to answer

| Question | Explanation and code to study |
| --- | --- |
| Why Flask and plain JavaScript? | Both fit the specified stack and keep the application small. Templates provide pages; JavaScript calls the same JSON endpoints used by API clients. `app/__init__.py`, `app/routes.py`, `app/static/app.js`. |
| Why six tables? | Users create orders/movements; customers have orders; orders have many items; items reference products; movements audit changes to product stock. Foreign keys preserve history. `sql/schema.sql`. |
| How do you calculate money? | Use Python Decimal and MySQL DECIMAL, never browser totals. For Keyboard 2 x 1500 plus Mouse 3 x 500, subtotal is 4500; a 10% discount is 450; grand total is 4050. ROUND_HALF_UP gives a consistent two-decimal result. `app/validation.py`. |
| What if product price changes? | Each order item stores a rate snapshot. Existing Draft rows retain that rate on edit; newly added products use the current database price. `save_order` in `app/services.py`. |
| Why not deduct stock on Draft save? | The specification says Drafts do not reserve stock. Availability is checked at confirmation, so a valid Draft can still be rejected later if another order used the stock. |
| How do simultaneous confirmations stay safe? | Begin a transaction, lock the order, lock products in sorted ID order using FOR UPDATE, validate every item, then update stock, movements and status together. A competing request waits and reads the committed stock. Failure rolls back all writes. `transition_order` and `lock_products`. |
| Why do retries not change stock twice? | The order row lock serializes requests. If its current status is already the requested target, return without applying stock changes again. A unique stock-event key adds another constraint. |
| How do you stop someone changing an order ID in the URL? | The backend reloads the authenticated user and checks the order's creator for every read/write/transition/bill. UI visibility is only convenience. `accessible_order`, API routes and bill route. |
| Why do customer reports include zeros without double counting? | LEFT JOIN orders directly to customers, with Confirmed/date filters inside the join condition. Do not join item rows when summing order grand totals. `reports` in `app/routes.py`. |
| Why is CSV import all-or-nothing? | Validate all rows and database duplicates before insertion; perform inserts and opening movements in one transaction. A bad row raises an error and nothing is committed. `app/csv_import.py`. |
| What was wrong in the debugging exercise? | `total = amount` overwrote earlier amounts. Accumulate with `total += amount` after validating quantity and rate. Empty input returns Decimal 0.00; missing/invalid data raises a clear error. |
| What does Git history show? | Meaningful development commits and real feature branch merges. Run `git log --graph --oneline --all` and explain one change. |

## Demonstration sequence

1. Open the landing page and log in as Admin.
2. Show customer/product search, status filters and an adjustment with a reason.
3. Import an invalid CSV and show that nothing was imported; then import a valid file.
4. Create a two-product Draft with a 10% discount. Explain why stock has not changed.
5. Confirm it and show deducted stock, movement history and its shop/A4 bill.
6. Cancel it and show stock restoration. Explain the retry behavior covered by tests.
7. Try an order with an unavailable quantity; show the whole confirmation being rejected.
8. Show sales reports, including a customer with zero matching Confirmed orders.
9. Log in as Sales User; show own orders and denied access to another user's order.
10. Run `python -m pytest -q` and point out the real-MySQL concurrency tests.

## Practise one live change

Choose one exercise, implement it on a new Git branch, and run the relevant tests:

- Add a new product category through master data without changing the schema.
- Change the shop name/address in `.env`, restart, and verify the printable bill.
- Add a report filter while preserving zero-sales customers.
- If an interviewer changes the permitted discount range, identify the backend validator,
  database CHECK constraint, browser min/max, preview calculation bound, tests and
  documentation that must change together. Keep the submitted 0-20% rule until asked.

## Honest AI disclosure

Keep `AI_USAGE.md` in the submission. AI assisted extensively with this project. Explain
what you have personally reviewed and practised, and demonstrate your understanding
through the code and a live change. Do not claim unaided authorship.
