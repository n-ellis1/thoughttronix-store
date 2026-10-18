# CLAUDE.md — The ThoughtTronix Store

A server-rendered Django 6 storefront and back office. The PRD (`prd/core-platform.md`) and the plan (`plans/core-platform.md`) record how the core platform was designed and built.

## Commands

- `uv sync` — install dependencies (Python 3.13, managed by uv)
- `uv run python manage.py migrate` — apply migrations
- `uv run python manage.py seed` — reset the database to the demo world
  (destructive, idempotent)
- `uv run python manage.py tailwind runserver` — dev server + Tailwind watch
- `uv run python manage.py tailwind build` — compile production CSS
- `uv run pytest` — run the test suite
- `uv run ruff check .` and `uv run ruff format .` — lint and format

## Project layout

- `config/` — the project package (settings, root urls)
- `accounts/` — custom user model (`accounts.User`, `AbstractUser` + nullable
  `job_title`). Roles are Django's own vocabulary: customers are plain users,
  employees are `is_staff`, the admin is `is_superuser`. No role field, no Groups.
  Also the Account Security Center (`prd/account-security.md`): `email` is the
  confirmed address, with pending-email methods on `User`; email
  add/change/confirm, password change, and password reset built on Django's
  auth views; plain-text emails in `emails.py`; cache-backed rate limits in
  `ratelimit.py`.
- `products/` — catalog (`Category`, `Product`, `Tag`), its back-office CRUD,
  and the `seed` command
- `orders/` — cart, checkout, orders, and back-office order management
- `dashboard/` — the staff analytics dashboard
- `wishlist/` — the customer wishlist (`prd/wishlist.md`): one `WishlistItem`
  per saved (user, product), with `add`/`remove`/`contains` on its manager;
  idempotent HTMX add/remove endpoints, the `{% wishlist_button product %}`
  inclusion tag, and the read-only `/wishlist/` page. Depends on `products`;
  nothing depends on it.
- `reviews/` — product reviews (`prd/product-reviews.md`): one `Review` per
  (user, product), a 1–5 rating plus a required comment; `edited_at` records
  whether it was edited and `edited_by` who, with `edit_label` on the model;
  `summary_for`/`for_product` on its queryset; the `{% reviews_section
  product %}` inclusion tag on the product detail page. Depends on
  `products`, `orders`, and `accounts` (`User.public_name()`); nothing
  depends on it.
- `PROMPTS.md` — the AI-usage log; append entries, never rewrite history
- `templates/` — project-level templates (`base.html`); app templates live in
  `templates/<app>/`
- `assets/` — static sources; `assets/css/source.css` is the Tailwind input,
  `assets/css/tailwind.css` is compiled output (gitignored, never edit)

## Architecture convention

Logic lives in models and managers; cross-model workflows get a service
module; views stay thin.

Exactly two deliberate deep modules, docstrings and type hints on every
public function: `orders/services.py` (`place_order`), and `dashboard/queries.py` (the dashboard's
aggregations).

Idiomatic Django throughout: class-based views, model methods, custom
managers/querysets, forms own their validation. Settings read from `.env`
via environs with working defaults — the app must run with no `.env` present.

## Template conventions

When working on templates, styling, or HTMX, read `docs/FRONTEND.md` for
template conventions.

## URL conventions

- Every URL is named; every app has a namespace (`products:catalog`,
  `orders:checkout`).
- Public catalog URLs use slugs (`/products/seraphine-home-hub/`);
  back-office URLs use pks.
- `Product` defines `get_absolute_url`.

## Testing

When writing or changing tests, read `docs/TESTING.md` for testing conventions.