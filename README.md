# Cosmos Custom Shirts

Cosmos Custom Shirts is a Django portfolio project that demonstrates the core
workflows behind a customizable apparel storefront. Visitors can browse a
catalog, select shirt options, manage a session-backed cart, and explore account
features without placing a real order or submitting payment information.

> **Portfolio demo:** This is not a functioning ecommerce business. Products,
> prices, inventory, carts, and accounts exist only to demonstrate application
> behavior. No payments or orders are processed.

## What this project demonstrates

- Django models, migrations, administration, views, templates, and forms
- A custom email-based user model
- Registration, authentication, account activation, and profile management
- Demo-safe registration that does not require a real email inbox
- Product categories and availability controls
- Database-backed product variants with size, fabric, color, stock, and optional pricing
- A customized, permission-aware Django administration workflow
- A session-backed cart whose totals are recalculated from current database prices
- Asynchronous cart updates using `fetch`, JSON responses, and CSRF protection
- Environment-based development and production configuration
- Automated tests for catalog, cart, and account workflows

## Technology

- Python 3.14
- Django 6.0
- SQLite for local development
- Bootstrap 5 and custom CSS
- Pillow for product images
- Gunicorn and Nginx are intended for the EC2 production deployment

## Project structure

```text
account/      Custom user model, registration, authentication, and profiles
basket/       Session cart domain logic, endpoints, and tests
core/         Project settings and root URL configuration
shop/         Catalog models, views, administration, and tests
static/       Project-owned CSS and static assets
templates/    Shared and app-specific Django templates
media/        Local development product images
```

The cart deliberately remains separate from the catalog. The `shop` app owns
product data, while `basket` stores temporary selections in the visitor's Django
session. Account functionality is isolated in `account` and uses
`AUTH_USER_MODEL` from the beginning of the project.

## Local setup

### Windows PowerShell

```powershell
# From the cloned repository:
cd custom-shirts
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### macOS or Linux

```bash
# From the cloned repository:
cd custom-shirts
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Use `/admin/` to create categories and designs
for a fresh database.

To load the bundled portfolio catalog instead, run this against a fresh database:

```powershell
python manage.py loaddata shop_fixture.utf8.json
python manage.py seed_demo_variants
python manage.py install_demo_media
```

The management command copies the bundled seed images into the configured
`MEDIA_ROOT` without overwriting existing files. The product photographs are
third-party demo assets; see
[THIRD_PARTY_ASSETS.md](THIRD_PARTY_ASSETS.md) for their licensing context.

## Catalog administration

The Django admin is treated as a genuine content-management surface rather than
an unmodified framework screen. Administrators can:

- Create categories and designs with automatically populated slugs
- Upload validated JPEG, PNG, or WebP images with previews
- Edit size, fabric, color, price, status, and inventory variants inline
- Generate missing standard variant combinations in one bulk action
- Activate or deactivate designs and variants in bulk
- Set selected variants out of stock without deleting catalog data
- Search and filter the catalog, including low-stock variants
- View calculated availability, variant counts, and inventory totals

To add a design, sign in at `/admin/`, open **Designs**, and choose
**Add design**. The current administrator is recorded automatically as its
creator. Add at least one active variant with positive inventory for the design
to appear publicly. Generated variants intentionally start with zero stock so
availability always requires an explicit administrator decision.

## Configuration

Development defaults are intentionally convenient. Production values must be
provided as environment variables; [.env.example](.env.example) documents all
currently supported settings.

| Variable | Purpose |
| --- | --- |
| `DJANGO_SECRET_KEY` | Required secret value when debug mode is disabled |
| `DJANGO_DEBUG` | Enables development error pages; set to `False` publicly |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames accepted by Django |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated HTTPS origins |
| `DJANGO_SECURE_SSL` | Enables secure cookies, HTTPS redirect, and HSTS |
| `DJANGO_DEMO_MODE` | Enables immediate, email-free demo registration |
| `DJANGO_EMAIL_*` | SMTP configuration used outside demo mode |

Do not commit a populated `.env` file, server credentials, production databases,
or secret keys.

## Demo mode and email mode

`DJANGO_DEMO_MODE=True` is recommended for the public portfolio deployment.
Accounts activate immediately, no email is sent, and password reset explains
that mail delivery is unavailable. Visitors are repeatedly instructed to use
fictional information.

With `DJANGO_DEMO_MODE=False`, registration uses an emailed activation link.
Activation links expire after 24 hours, and SMTP delivery is configured through
environment variables. This path is retained to demonstrate a conventional
account lifecycle without making it mandatory for portfolio visitors.

## Tests

Run the complete suite with:

```powershell
python manage.py test
```

The current suite covers product visibility, unavailable products, cart input
validation and mutations, registration in both modes, account activation,
protected pages, CSRF enforcement, POST-only account deactivation, admin access,
secure admin-created passwords, protected relationships, validated uploads,
variant generation, and creator attribution.

Useful release checks are:

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py check --deploy
```

Run the deployment check using the same environment variables as the production
service.

## Production outline

The intended EC2 topology is:

```text
Browser -> HTTPS -> Nginx -> Gunicorn -> Django
                              |
                              +-> database
```

Nginx should serve collected static files and proxy application requests to a
Gunicorn service managed by systemd. Only ports 80 and 443 should be public;
Gunicorn and the database should not be exposed directly. Production deployment
also requires backups, log rotation, health monitoring, and a deliberate media
storage strategy.

The included Nginx configuration rate-limits POST requests to the Django admin
login endpoint. It does not expose Gunicorn or the SQLite database.

This repository does not use Django's development server as its intended public
web server.

## Security and demo boundaries

- Account deactivation requires authentication, CSRF validation, confirmation,
  and a POST request.
- Cart option values are validated on the server rather than trusted from the UI.
- Active variant inventory is the source of truth for storefront availability.
- Inactive designs and unavailable variants cannot be added to the cart.
- Admin-created passwords use Django's validation and password hashing.
- Categories containing designs are protected from cascading deletion.
- Removing a former creator preserves their designs and clears attribution.
- Product uploads are restricted by format, file size, and dimensions.
- Bulk deletion is disabled for categories and accounts.
- Production startup fails when `DJANGO_SECRET_KEY` is missing.
- HTTPS and secure-cookie behavior can be enabled consistently through one
  production environment setting.
- The application never requests or processes payment card information.

This is a learning and portfolio application, not a claim of PCI compliance or
production ecommerce readiness.

## Design decisions and tradeoffs

- **Session cart:** appropriate for a compact demonstration and anonymous users,
  but it does not synchronize carts across devices.
- **SQLite locally:** makes setup fast; a managed relational database is a better
  choice for a multi-user production deployment.
- **Database-backed variants:** inventory combinations are explicit and validated
  server-side; the demo intentionally stops short of reservation and fulfillment logic.
- **Variant-owned availability:** the original design-level stock field remains
  as a non-editable fixture-compatibility field; active variant inventory controls
  what visitors can view and add to the cart.
- **Protected relationships:** category deletion cannot silently remove products,
  and deleting a former creator preserves their catalog work.
- **Conservative media lifecycle:** replacing an image does not automatically
  delete the old storage object. Orphan cleanup remains an explicit maintenance
  operation so shared or backed-up assets are not removed unexpectedly.
- **Demo registration:** removes dependence on real email and protects the demo's
  intent; normal activation remains available behind configuration.
- **No checkout:** deliberately prevents the site from being mistaken for a real
  store. A future checkout should remain simulated and clearly labeled.

## Planned improvements

- Quantity selection and inventory reservation behavior
- Search, sorting, and pagination
- A clearly labeled simulated checkout and sample order history
- Two-factor authentication for production administrator accounts
- Continuous integration, linting, and coverage reporting
- Production database and media-storage configuration

## Engineering highlights for reviewers

This project began as a conventional Django storefront exercise and was revised
around production boundaries and maintainability. Notable decisions include:

- Replaced client-supplied cart prices and options with database-authoritative
  variants and server-side validation.
- Modeled unique product combinations with database constraints and deterministic
  display ordering.
- Derived storefront availability from active variant inventory instead of a
  manually synchronized product flag.
- Reworked custom-user administration around hashed-password creation, Django
  password validation, permission controls, and safer deletion behavior.
- Added image previews, creator attribution, inventory summaries, low-stock
  filtering, bulk status controls, and idempotent variant generation.
- Added environment-owned production secrets, HTTPS security controls, isolated
  data paths, Gunicorn/systemd, Nginx asset serving, and admin-login throttling.
- Added regression coverage for privileged administration workflows as well as
  public catalog, account, and cart behavior.

These choices are visible in the repository so reviewers can assess engineering
reasoning, security boundaries, schema evolution, and tests—not only the UI.

## Author

Created by Tiffany Morgan-Hill as a Django portfolio project.
