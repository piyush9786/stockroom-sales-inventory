# Working application demonstration

The submission archive includes `demo.mp4`, a **6-minute** captioned screen-capture
walkthrough of the actual Flask/MySQL application, refreshed on **8 November 2026**.
It shows the current Stockroom landing page, gradient workspace and shop/A4 bills.
Only fictional local accounts and data are shown. The walkthrough is edited to remove
idle upload delays and hold completed screens long enough to read. It has no spoken
narration. Recording tools are not application dependencies.

Verified duration: **360 seconds**, within the required 5-8 minutes. The finished video
is H.264, 1280 x 1200, with captions below the application view. It was decoded for
verification; the completed application flows produced no JavaScript console errors.

The recording used a separate sample database and login cookie from the main preview.
Current still previews are included as `landing-page.jpg`, `workspace-redesign.jpg`,
`shop-receipt.jpg`, and `a4-bill.jpg` in this directory.

The demo covers:

| Time | Demonstration |
| --- | --- |
| 00:00 | Current landing page and gradient design |
| 00:09 | Admin login and protected workspace |
| 00:27 | Customer creation, search and editing |
| 01:03 | Product catalogue and stock adjustment with a mandatory reason |
| 01:30 | Invalid CSV errors with row numbers and no imported products |
| 02:06 | Successful valid CSV import |
| 02:15 | Multi-item Draft creation; stock unchanged |
| 02:42 | Subtotal 4,500, 10% discount 450, grand total 4,050 |
| 02:51 | Confirmation, stock deduction and read-only contents |
| 03:09 | Shop receipt and A4 bill previews with stored values |
| 03:36 | Cancellation and stock restoration |
| 03:54 | Insufficient-stock confirmation rejected; Draft and stock retained |
| 04:21 | Date-filtered customer sales, including zero-sales customers |
| 04:39 | Product quantity/gross sales |
| 04:48 | Low-stock report |
| 04:57 | Stock movement history with sale/cancellation/adjustment records |
| 05:06 | Sales User login, own-order list and active-only master data |
| 05:33 | Server denial of another user's order ID; logout |
| 05:51 | Landing page and submission recap |

Still previews from the recording are provided in `order-editor.png` and
`stock-history.png` in this documentation directory.

The current-interface recording replaces the earlier 5:55 recording in the archive.
For interview preparation, use `INTERVIEW_GUIDE.md` and practise explaining the
real-MySQL concurrency tests, row-lock ordering, Decimal rounding, snapshots and Git history.
