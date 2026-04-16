# RetailDash — Django Electronics Retail Platform

A Django 5.x application combining an internal operations dashboard for staff and a customer-facing storefront for an electronics retail business.

## Stack

- **Backend**: Django 5.x, Python 3.12
- **Database**: SQLite (development) — swap `DATABASE_URL` for PostgreSQL in production
- **Frontend**: Tailwind CSS (Play CDN), HTMX for dynamic interactions
- **Auth**: Two separate auth systems — internal staff login and customer portal login

---

## Getting Started

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd bangalore
python3.12 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Copy the example env file and adjust as needed:

```bash
cp retail_dashboard/.env.example retail_dashboard/.env
```

Key variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `django-insecure-...` |
| `DEBUG` | Debug mode | `True` |
| `DATABASE_URL` | Database connection | `sqlite:////absolute/path/to/db.sqlite3` |
| `ALLOWED_HOSTS` | Comma-separated hosts | `localhost,127.0.0.1` |

### 4. Run migrations

```bash
cd retail_dashboard
python manage.py migrate
```

### 5. Seed sample data

Populates categories, products, stock movements, and orders with realistic data:

```bash
python manage.py seed_data
```

### 6. Create a superuser (optional)

```bash
python manage.py createsuperuser
```

The superuser gets an auto-created `Profile` with role `staff`. Promote it in the shell:

```python
python manage.py shell -c "
from django.contrib.auth.models import User
u = User.objects.get(username='your_username')
u.profile.role = 'admin'
u.profile.save()
"
```

### 7. Start the development server

```bash
python manage.py runserver
```

---

## Internal Dashboard

Accessible at **`http://localhost:8000/`**

### Login

`http://localhost:8000/login/`

Internal staff log in with their username and password. Customer accounts are rejected here.

### Roles and access

| Role | Dashboard | Inventory | Orders | Analytics | Users |
|------|-----------|-----------|--------|-----------|-------|
| **admin** | Full | Full | Full | Full | Full |
| **manager** | Full | Full | Full | Full | No |
| **analyst** | KPIs only | No | Export only | Full | No |
| **staff** | Orders only | No | View + advance status | No | No |

### Pages

#### Dashboard — `/dashboard/`

Main landing page after login. Shows role-specific KPIs:

- **admin / manager / analyst**: active product count, low-stock alert count, monthly revenue
- **admin / manager / staff**: today's order count
- **admin / manager**: low-stock product list with reorder threshold warnings
- All roles: recent orders feed

#### Inventory — `/inventory/`

*admin and manager only*

| Page | URL | Description |
|------|-----|-------------|
| Product list | `/inventory/products/` | Paginated table with search, category filter, and stock status filter (in stock / low stock / out of stock) |
| Add product | `/inventory/products/add/` | Create a product: SKU, category, price, cost price, stock quantity, reorder threshold, featured flag |
| Product detail | `/inventory/products/<id>/` | Product info, stock status badge, last 20 stock movements |
| Edit product | `/inventory/products/<id>/edit/` | Update any product field |
| Deactivate product | `/inventory/products/<id>/deactivate/` | Soft-delete — hides from storefront and list |
| CSV import | `/inventory/products/import/` | *admin only* — bulk upload products |

CSV import format:

```
name,sku,description,category,price,cost_price,stock_quantity,reorder_threshold,is_active
```

Existing SKUs are updated; new SKUs are created.

#### Orders — `/orders/`

*admin, manager, and staff*

| Page | URL | Description |
|------|-----|-------------|
| Order list | `/orders/` | Paginated orders with status, date range, and search filters. Storefront orders show a purple **Storefront** badge |
| Order detail | `/orders/<id>/` | Full order info, line items, status timeline, created-by |
| Update status | `/orders/<id>/status/` | admin/manager: set any status. staff: advance to the next step only (`pending → confirmed → processing → shipped → delivered`) |
| Export CSV | `/orders/export/` | *admin, manager, analyst* — download filtered orders as CSV |

#### Analytics — `/analytics/`

*admin, manager, analyst*

- Date-range picker (defaults to last 30 days)
- Revenue over time — line chart
- Top 10 products by units sold — bar chart
- Order status breakdown — doughnut chart
- CSV export of top products with revenue

#### User Management — `/users/`

*admin only*

| Page | URL | Description |
|------|-----|-------------|
| User list | `/users/` | All staff users with role badges |
| Create user | `/users/create/` | Create a staff account and assign a role |
| Edit user | `/users/<id>/edit/` | Update name, email, role, phone, active status |
| Deactivate user | `/users/<id>/deactivate/` | Disable login for a staff member |

#### Profile — `/profile/`

All staff can update their own name, email, phone, and avatar.

---

## Customer Storefront

Accessible at **`http://localhost:8000/store/`**

Customers use a completely separate login from internal staff. A staff account cannot log in through the customer portal, and vice versa.

### Customer authentication

| Page | URL | Description |
|------|-----|-------------|
| Register | `/store/register/` | Create a customer account (username, email, name, password) |
| Login | `/store/login/` | Customer login — staff accounts are rejected |
| Logout | `/store/logout/` | Ends the customer session |
| My Account | `/store/account/` | Update name, phone, and address |

### Storefront pages

| Page | URL | Description |
|------|-----|-------------|
| Home | `/store/` | Featured products (flagged `is_featured`) + category pills |
| Catalog | `/store/products/` | All active products with price range, in-stock, category, and sort filters |
| Category | `/store/category/<slug>/` | Catalog filtered to a single category |
| Product detail | `/store/products/<slug>/` | Description, price, add-to-cart, related products, customer reviews |
| Cart | `/store/cart/` | Session cart — no login required. Line items, quantities, subtotal |
| Checkout | `/store/checkout/` | *Requires login.* Review cart and confirm order. Stock is validated before placing |
| Order confirm | `/store/orders/confirm/<order-number>/` | Post-checkout confirmation with order number and status timeline |
| Order tracking | `/store/orders/track/` | Public — enter any order number to see its current status |
| Order history | `/store/orders/` | *Requires login.* Customer's own past orders |
| Order detail | `/store/orders/<order-number>/` | *Requires login.* Full order detail — only the placing customer can access it |

### Cart behaviour

The cart lives in the Django session — no database, no login required. HTMX updates the cart badge in the navbar on every add without a page reload. Checkout requires a customer account.

### Checkout flow

1. Add products to cart (session)
2. Log in or register at `/store/login/`
3. Review items at `/store/checkout/`
4. On submit: stock availability is validated; an `Order` is created with `source='storefront'`; stock is decremented via a `StockMovement`; cart is cleared
5. Redirected to the order confirmation page

Storefront orders appear in the internal dashboard's order list with a **Storefront** badge and follow the same status flow managed by staff.

### Reviews

Logged-in customers can leave a rating (1–5) and a comment on any product page. One review per customer per product — submitting again updates the existing review.

---

## Running Tests

```bash
cd retail_dashboard
python manage.py test apps.accounts apps.core apps.inventory apps.orders apps.customers apps.storefront
```

132 tests covering:

- Model methods and properties (slug generation, stock status, order number auto-assignment, line totals)
- Role-based access control matrix for every protected view
- Customer auth flow (register, login, staff-block, logout)
- Cart lifecycle (add, update, remove, HTMX partial responses)
- Full checkout flow (order creation, stock decrement, cart clear, insufficient-stock rejection)
- Order tracking and customer-owned order access enforcement
- Review submission and idempotent update

---

## Project Structure

```
retail_dashboard/
├── apps/
│   ├── accounts/     # Internal staff auth, Profile model, signals
│   ├── core/         # Dashboard home, role_required decorator, 403 handler
│   ├── inventory/    # Category, Product, StockMovement models and views
│   ├── orders/       # Order, OrderItem models and views
│   ├── analytics/    # Revenue, top products, order status charts + CSV export
│   ├── users/        # Staff user management (admin only)
│   ├── storefront/   # Customer store views, cart, checkout, reviews
│   └── customers/    # Customer auth, account, order history
├── templates/        # All HTML templates
├── config/           # Django settings and root URL config
└── manage.py
```

## Data Models

| Model | App | Key fields |
|-------|-----|------------|
| `Profile` | accounts | `user` (1-to-1), `role` (admin / manager / analyst / staff) |
| `Category` | inventory | `name`, `slug` (auto-generated) |
| `Product` | inventory | `sku`, `name`, `slug` (auto), `price`, `cost_price`, `stock_quantity`, `reorder_threshold`, `is_featured`, `is_active` |
| `StockMovement` | inventory | `product`, `movement_type` (restock / sale / adjustment / return), `quantity_change` (±), `created_by` |
| `Order` | orders | `order_number` (auto, e.g. `ORD-00001`), `status`, `source` (internal / storefront), `total_amount` |
| `OrderItem` | orders | `order`, `product`, `quantity`, `unit_price` |
| `Customer` | customers | `user` (1-to-1), `phone`, `address` |
| `Review` | storefront | `product`, `customer`, `rating` (1–5), `comment` |
| `ProductImage` | storefront | `product`, `image`, `is_primary` |

### Stock movement signal chain

When an `OrderItem` is saved, a `post_save` signal automatically:

1. Creates a `StockMovement` record (`movement_type='sale'`, `quantity_change=-quantity`)
2. The `StockMovement` `post_save` signal applies the change to `product.stock_quantity`

All stock adjustments flow through the movement log, maintaining a full audit trail.
