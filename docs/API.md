# JSON REST API

Base URL for the documented local setup: `http://127.0.0.1:5000/api`.
All endpoints require a logged-in session except GET `/session` and POST `/login`.
All writes require the `X-CSRF-Token` from `/session` (rotated by login).
Send `Content-Type: application/json` for JSON writes; CSV uses multipart form data.
Cookies must be preserved. Browser fetch uses `credentials: 'same-origin'`.
Money is returned as a two-decimal **string**, whole-number quantities/counts as integers.

## Login and logout

1. GET `/session`, preserving the session cookie:

```json
{"user": null, "csrf_token": "<session-token>"}
```

2. POST `/login` with `X-CSRF-Token: <session-token>` and your locally chosen password:

```json
{"email":"sales@example.test","password":"<password-you-created>"}
```

200 response (illustrative user ID; actual IDs depend on local data):

```json
{"user":{"id":2,"name":"Demo Sales","email":"sales@example.test","role":"Sales User"},"csrf_token":"<new-token>"}
```

Use the **new** token for subsequent writes. POST `/logout` clears the session and
returns `{"message":"Logged out."}`. GET `/session` returns the current safe user fields
and token, never a password hash. Incorrect login returns 401 with a generic message.

## Endpoint catalogue

| Method / endpoint | Access and behavior |
| --- | --- |
| GET `/customers` | Active customers for Sales; Admin may use `status=Active/Inactive/All`; search `q` by name/email/mobile |
| GET `/customers/{id}` | View permitted customer; Sales cannot view inactive records |
| POST `/customers` | Admin only; create |
| PUT `/customers/{id}` | Admin only; full editable fields |
| DELETE `/customers/{id}` | Admin only; 204 if unreferenced, 409 otherwise |
| GET `/products` | Active by default; `q`, `category`, pagination; Admin may filter status |
| GET `/products/{id}` | Current product price/stock/status; Sales sees active only |
| POST `/products` | Admin only; creates opening stock/movement atomically |
| PUT `/products/{id}` | Admin only; editable master fields, excluding stock |
| DELETE `/products/{id}` | Admin only; rejects order-item or movement references |
| POST `/products/{id}/stock-adjustments` | Admin only; signed whole-number change and mandatory reason |
| POST `/products/import` | Admin only; multipart field `file`; UTF-8 CSV; atomic |
| GET `/orders` | Admin: all; Sales: own; optional `q` and `status` |
| POST `/orders` | Creates a Draft, 201; creator/status/rates/totals come from server |
| GET `/orders/{id}` | Accessible order and item snapshots; 403 if another Sales User owns it |
| PUT `/orders/{id}` | Accessible Draft only; same payload as creation |
| POST `/orders/{id}/confirm` | Accessible Draft; validates/deducts all stock in one transaction |
| POST `/orders/{id}/cancel` | Accessible Draft or Confirmed; restores Confirmed stock exactly once |
| GET `/reports/customer-sales` | Admin; optional inclusive `start_date`, `end_date` in YYYY-MM-DD |
| GET `/reports/product-sales` | Admin; same optional date range; gross item value before order discount |
| GET `/reports/low-stock` | Admin; whole-number `threshold`, default 10, strictly below |
| GET `/reports/stock-movements` | Admin; optional `product_id`, pagination; UTC timestamps |

Customer/product/order lists and movement history accept `page` (default 1) and
`per_page` (default 20, maximum 100). Their response has `items`, `page`, `per_page`,
`total`. The other reports return `{"items":[...]}`. No CORS service is needed.

## Product search example

`GET /api/products?q=keyboard&page=1&per_page=20`

```json
{"items":[{"id":1,"product_code":"PRD-001","name":"Keyboard","category":"Accessories","price":"1500.00","stock_quantity":20,"status":"Active"}],"page":1,"per_page":20,"total":1}
```

## Create / edit masters

POST `/api/customers` (201) or PUT `/api/customers/{id}` (200):

```json
{"name":"Acme Traders","email":"orders@acme.example","mobile":"9000000001","city":"Pune","status":"Active"}
```

POST `/api/products` (201):

```json
{"product_code":"PRD-010","name":"Keyboard","category":"Accessories","price":"1500.00","stock_quantity":20,"status":"Active"}
```

PUT uses the same product master fields **without** `stock_quantity`. Change existing
stock through POST `/api/products/{id}/stock-adjustments`:

```json
{"quantity_change":-2,"reason":"Damaged items removed after stock count"}
```

200 returns the product with updated stock. Missing reason, zero/fractional change, or
negative resulting stock is rejected. Deactivation is a PUT with `status: "Inactive"`.

## Create and retrieve an order

POST `/api/orders` (same payload for PUT `/api/orders/{id}`):

```json
{"customer_id":1,"order_date":"2026-11-07","discount_percentage":"10.00","items":[{"product_id":1,"quantity":2},{"product_id":2,"quantity":3}]}
```

201 response; GET `/api/orders/1` returns the same shape:

```json
{
  "id":1,
  "order_number":"SO-<32-character-uppercase-UUID>",
  "customer_id":1,
  "customer_name":"Acme Traders",
  "order_date":"2026-11-07",
  "status":"Draft",
  "discount_percentage":"10.00",
  "subtotal":"4500.00",
  "discount_amount":"450.00",
  "grand_total":"4050.00",
  "created_by":2,
  "items":[
    {"id":1,"sales_order_id":1,"product_id":1,"quantity":2,"rate":"1500.00","amount":"3000.00","product_name":"Keyboard","product_code":"PRD-001","stock_quantity":20,"product_status":"Active"},
    {"id":2,"sales_order_id":1,"product_id":2,"quantity":3,"rate":"500.00","amount":"1500.00","product_name":"Mouse","product_code":"PRD-002","stock_quantity":50,"product_status":"Active"}
  ]
}
```

Order number is generated, so clients must use the actual response rather than this
placeholder. Current stock in the response is informational; saved `rate` is historical.
Sending `rate`, `amount`, totals, status or creator from the browser does not override the
server. Empty/duplicate items, nonpositive/fractional quantities, inactive selections or
discount outside 0-20 are rejected.

POST `/api/orders/1/confirm` with no body returns 200 and the updated order, now
Confirmed. Repeating it returns 200 without deducting again. Insufficient stock returns
409 and leaves all products, movements and order state unchanged.

POST `/api/orders/1/cancel` returns 200 and Cancelled. A previously Confirmed order's
stock is restored once; cancelling a Draft changes no stock. Repeating cancel is safe.
Attempting to confirm a Cancelled order or edit Confirmed/Cancelled contents returns 409.

## Reports

`GET /api/reports/customer-sales?start_date=2026-11-01&end_date=2026-11-30`:

```json
{"items":[{"id":1,"customer":"Acme Traders","confirmed_order_count":1,"total_sales":"4050.00"},{"id":2,"customer":"Bluebird Supplies","confirmed_order_count":0,"total_sales":"0.00"}]}
```

Product summary rows contain `id`, `product_code`, `product`, `quantity_sold`,
`gross_item_value`. Low-stock rows contain `id`, `product_code`, `product`, `category`,
`stock_quantity`, `status`. Movement rows contain `id`, `product`, `product_code`,
`movement_type`, `quantity_change`, `order_number` (null for non-order stock changes),
`reason`, `created_at`, `created_by` (the user's name).

## CSV import

POST `/api/products/import` with multipart form field `file` containing the sample CSV.
The request carries the CSRF header and session cookie; let fetch set the multipart
Content-Type boundary. Success (201): `{"imported":2}`.

Validation failure (400):

```json
{"error":"Import rejected. No products were imported.","details":[{"row":3,"reason":"Price must be between 0 and 999999999999.99."}]}
```

## Errors and status codes

| Status | Meaning |
| --- | --- |
| 200 | Read, edit, login/logout, adjustment, successful/idempotent transition |
| 201 | Created order/customer/product or successful CSV import |
| 204 | Deleted unreferenced master record; no response body |
| 400 | Validation failure or malformed JSON/CSV |
| 401 | Missing authentication or invalid login |
| 403 | Insufficient role, another user's order or invalid CSRF token |
| 404 | Missing record or route |
| 409 | Invalid transition, insufficient stock, protected reference, unique collision or conflicting transaction |
| 413 | Request/upload exceeds 2 MB |
| 503 | Database unavailable |
| 500 | Generic unexpected server error; internal details remain server-side |

Errors have `{"error":"Clear message"}` plus optional `details` for CSV row errors.
