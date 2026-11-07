# Assignment coverage checklist

Source reviewed: all 18 pages of the provided Fresher / Trainee Software Developer
technical assignment, including all 14 parts, deliverables, interview notes and ground rules.

| Part | Requirements and implementation evidence |
| --- | --- |
| 1. Technology | Python Flask backend; HTML/CSS/plain JavaScript; MySQL; authenticated JSON REST; Git; pytest. Dependencies/runtime versions in README. No optional frontend framework added. |
| 2. Login/access | Login/logout, scrypt hashing, protected pages/APIs, Admin/Sales User roles, own-order checks on every operation, locally chosen sample passwords; `app/__init__.py`, `app/routes.py`, access tests. |
| 3. Database | All minimum fields for User, Customer, Product, Sales Order, Sales Order Item, Stock Movement; PK/FK/CHECK/unique constraints, indexes and Decimal money; `sql/schema.sql`, sample-data SQL/CLI and README relationships. Referenced master deletion restricted. |
| 4. Master data | Customer create/view/edit/delete-unreferenced, name/email/mobile search, status filtering; product create/view/edit/delete-unreferenced, code/name search, category/status filters, unique code, nonnegative price/stock; Admin writes only. Forms/APIs and master-data tests. |
| 5. Orders | Active customer/products, multiple rows, UUID order number, database price snapshots, Draft quantity/edit/remove, no duplicates, at least one item, discount 0-20, backend totals and two-decimal ROUND_HALF_UP. Browser rates/totals/status/creator cannot override. `app/services.py`, validation, order editor and tests. |
| 6. Lifecycle/stock | Draft does not reserve; confirm checks all stock; insufficient product rolls back; transition/stock/movements one transaction; Confirmed/Cancelled contents read-only; cancel restores Confirmed stock once; repeated confirm/cancel safe; actual concurrent confirmations/retries tested. Admin stock adjustment with mandatory reason, movement and no negative result. Locking approach explained in README. |
| 7. JavaScript | Product price/stock fetch, dynamic add/remove rows, live item/subtotal/discount/grand total, form/client error messages, confirmation/cancellation dialogs, success/failure handling with fetch, pending action buttons disabled. Server validation is authoritative. `app/static/app.js`. |
| 8. REST | Required product list, order create/retrieve/confirm/cancel endpoints plus supporting management/edit/report APIs; shared permissions, pagination, clear JSON, HTTP status codes, missing/invalid/unauthenticated/forbidden handling, no secrets/tracebacks in responses. `docs/API.md`. |
| 9. Reports/SQL | Customer Confirmed order count/net sales with inclusive date range, zero-sales customers, no item-join multiplication; product quantity/gross value; threshold stock; movement history with required fields. Five standalone queries: top customers, top products, never-ordered customers, year/month totals, below-threshold products. `sql/report_queries.sql`, report routes/tests. |
| 10. CSV | Admin-only exact six-column format; required values; file/database duplicate codes; numeric/sign/status validation; physical line and reason errors; all-or-nothing transaction; Opening movements for nonzero opening stock; valid/invalid samples and tests. `app/csv_import.py`. |
| 11. Debugging | Corrected shared calculate_total; cause, empty list, missing keys and invalid quantity/rate explanation in `docs/DEBUGGING.md`; tests verify 350 and validation. |
| 12. Tests | All nine mandatory scenarios plus additional role/authentication, data-integrity, report, CSV and real-concurrency checks; pytest command and separate MySQL test DB documented. `tests/`, `docs/VERIFICATION.md`. |
| 13. Git/quality | Meaningful development commits; `feature/product-csv-import` developed/merged into main; `.gitignore`, `.env.example`; credentials/environments/generated dependencies excluded. Routes, validation, services, CSV and DB separated. Git history retained in archive. |
| 14. AI | `AI_USAGE.md` explicitly identifies Codex, assisted tasks, original prompt, automated/code review and corrections. Candidate responsibility to understand/debug/modify disclosed. |

## Deliverables and instructions

The README's submission table maps all ten deliverables, including the 5-8 minute demo.
The archive uses the required `FullName_TechnicalAssignment` pattern. Local setup is
documented; public hosting is optional and is not needed. Deadline is three calendar
days after receipt; submission itself is the candidate's responsibility. Real credentials,
virtual environments and dependency downloads are excluded from submission.

Scope is one currency/location and integer quantities. Taxes, delivery, purchasing and
payment processing are excluded. Sales reports count Confirmed orders only. The
interface is deliberately simple and functional, with clear errors and server-side financial
validation. Assumptions/limits and verification are documented rather than concealed.

## Technical interview preparation

The assignment says shortlisted candidates must demonstrate the app, explain design
decisions and make a small live change. Review Python, JavaScript and SQL; validation
and error handling; transaction/stock consistency; the debugging fix; Git branch/merge
history; and how to adapt a requirement. `AI_USAGE.md` is a disclosure, not evidence of
the candidate's independent ability. Run the setup/tests yourself before submission.
