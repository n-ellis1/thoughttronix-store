# The ThoughtTronix Store

*Your Thoughts, Our Business.*

A server-rendered Django 6 storefront and back office for the world's most
beloved consumer neural technology: browse the catalog, fill a cart, check
out through a fully validated form, and — if you're staff — run the store
from the back office, analytics dashboard included.

## Getting started

Requires Python 3.13 and [uv](https://docs.astral.sh/uv/). No Node.js —
Tailwind runs as a standalone binary.

```bash
uv sync
uv run python manage.py migrate
uv run python manage.py seed
uv run python manage.py tailwind runserver
```

Then open <http://127.0.0.1:8000/>. From clone to browsing the store, this
takes about two minutes.

## Demo logins

The `seed` command creates a fixed demo world — the same one every run:

| Username      | Password         | Who they are                                                  |
| ------------- | ---------------- | ------------------------------------------------------------- |
| `admin`       | `admin123`       | Superuser: everything below, plus the Django admin at `/admin/` |
| `employee`    | `employee123`    | Staff: the back office (products, orders, dashboard)           |
| `customer`    | `customer123`    | A customer with five orders (one cancelled), a live cart, a three-item wishlist, and two product reviews |
| `newcustomer` | `newcustomer123` | A customer with no email: Account shows the "add an email" reminder; empty wishlist |

Every seeded account except `newcustomer` starts with a confirmed
`example.com` email, so password reset and password change work on them
right away. The seed's background customers have no usable password; an
admin can give one a password from the user's page in `/admin/`.

## Account security and email

Every signed-in user has an **Account** page (the Security Center) for
adding or changing their email and changing their password. Signed-out
visitors can use **Forgot password?** on the sign-in page. Sign-in stays
username-based; email is only for recovery and security notices.

### Testing emails in the terminal

With no `.env`, every email (signup and change confirmations, password
reset links, and security notices) prints in the terminal running the dev
server instead of being sent. To follow a link, copy the URL from the
printed email and open it in your browser, or in a private window to check
that the link works while signed out. Seeded addresses use the reserved
`example.com` domain, so nothing real is ever emailed.

Confirmation links expire after 24 hours, and password reset links after 1
hour. Each one works only once, and only the newest confirmation link for
an account works.

### Sending real email over SMTP

Copy `.env.example` to `.env` and uncomment the email settings:
`EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, plus
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`EMAIL_USE_TLS`, and `DEFAULT_FROM_EMAIL`. Restart the server to pick them
up. `.env` is gitignored, so keep real credentials there and never in
`.env.example`.

### Rate limits

| Action | Limit | Cooldown |
| --- | --- | --- |
| Sign-in | 5 failures per username (ignoring capitalization) in 15 minutes | 15 minutes, even for the right password |
| Password reset request | 3 per email address per hour | Rest of the hour; the page shows its usual message but sends nothing |
| Confirmation email | 3 per account per hour (signup, new requests, and resends combined) | Rest of the hour |

The counters live in Django's default in-process memory cache. That keeps
setup at zero, with two limitations: **restarting the server resets every
counter**, and **counters aren't shared between server processes**, so a
deployment running several workers would allow more attempts in total. A
production deployment should point `CACHES` at a shared store such as
Redis or Memcached. No account is ever permanently locked.

## Commands

| Command                                     | What it does                             |
| ------------------------------------------- | ---------------------------------------- |
| `uv sync`                                    | Install dependencies                     |
| `uv run python manage.py migrate`            | Apply database migrations                |
| `uv run python manage.py seed`               | Reset the database to the demo world (destructive, idempotent) |
| `uv run python manage.py tailwind runserver` | Dev server + Tailwind watch              |
| `uv run python manage.py tailwind build`     | Compile production CSS                   |
| `uv run pytest`                              | Run the test suite                       |
| `uv run ruff check .`                        | Lint                                     |
| `uv run ruff format .`                       | Format                                   |

## Product images

Staff upload product images from the back office. Each upload is checked
(JPEG, PNG, or WebP; 10 MB or smaller; 50 megapixels or fewer; at least
600 pixels on each side; no animation), resized to fit 1200 px, and saved
as WebP under `MEDIA_ROOT/products/`. `MEDIA_ROOT` defaults to `media/` in
the project and can be set in `.env`. A product with no image shows its
category's placeholder.

Django serves uploaded media only while `DEBUG` is on. A production
deployment must provide its own way to serve `MEDIA_URL` (`/media/`) —
that's out of scope here.

## Repo layout

`config/` is the project package (settings, root URLs); the four apps are
`accounts` (custom user model), `products` (the public catalog and its
back-office CRUD), `orders` (cart, checkout, orders — with the
`place_order` service in `orders/services.py`), and `dashboard` (staff
analytics, with the aggregations in `dashboard/queries.py`). Project-level
templates live in `templates/`, static sources in `assets/`. The product
requirements are in `prd/`, the phase-by-phase build plan in `plans/`, and
`PROMPTS.md` is where AI usage on this codebase gets logged.
