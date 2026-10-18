# Plan: Customer Wishlist

> Source PRD: `prd/wishlist.md`. The PRD owns the requirements; this plan owns the sequence. Where a phase says "per the PRD," the PRD's wording is authoritative.

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: A new `wishlist` app with the `wishlist` URL namespace. It depends on `products` and on `accounts` (for one mixin, from Phase 2). Nothing depends on it: the products app's Python code never imports from it, and the product detail view doesn't change. The only link from the catalog is the product detail template loading the wishlist template tag library. The seed command is the one place that imports the wishlist model. The project-layout section of CLAUDE.md gains an entry for the app in Phase 1.
- **Models**: A single `WishlistItem` model. There is no `Wishlist` container: a user's rows *are* their wishlist (the shape of `Address`, not `Cart`).
  - FK to the user (`related_name="wishlist_items"`) and FK to `Product`, both `CASCADE`. Marking a product unavailable removes nothing.
  - `created_at` uses a `timezone.now` default (not `auto_now_add`), so the seed can backdate rows.
  - A `UniqueConstraint` on (user, product).
  - Default ordering is newest first, with pk as a tiebreaker.
- **Migration**: One migration (Phase 1) creates the table. No changes to existing models.
- **Logic**: A custom queryset/manager owns `add(user, product)` (idempotent, get-or-create), `remove(user, product)` (idempotent, does nothing if absent), and `contains(user, product)` (one existence query). The views, the template tag, and the seed all use these. No service module.
- **URLs** (all in the `wishlist` namespace):

  | Path | Name | Access |
  |---|---|---|
  | `/wishlist/` | `wishlist:list` | signed in |
  | `/wishlist/add/<pk>/` | `wishlist:add` | signed in, POST only, HTMX |
  | `/wishlist/remove/<pk>/` | `wishlist:remove` | signed in, POST only, HTMX |

  The add and remove endpoints take the product's pk, as the cart's add endpoint does. They are HTMX endpoints, not public pages, so the catalog's slug convention doesn't apply. There is **no toggle endpoint**: each request says what was clicked.
- **Product lookup**: Add and remove look the product up among **all** products, not only available ones, and return 404 for an unknown pk. This deliberately differs from the cart's add view, and the view's docstring says why: saving isn't buying.
- **Authorization**: Sign-in only, open to every role (customers, staff, superusers). Every read and write is scoped to `request.user`. URLs identify only a product, never a wishlist row, so no request can address another customer's data.
- **The button**: One partial, rendered on first page load by the inclusion tag `{% wishlist_button product %}` and returned by every add/remove response, so its states are defined in one place. Responses contain only the partial, with no out-of-band swaps. CSRF comes from the site-wide HTMX header already in `base.html`. Tailwind/DaisyUI classes only, no JavaScript beyond HTMX. The button looks the same whether or not the product is available.
- **Admin**: `WishlistItem` is registered in the Django admin, listing user, product, and created date, searchable by username. Nothing goes in the custom back office.
- **Testing**: Follow `docs/TESTING.md`: pytest-django, plain fixtures in the project `conftest.py`, no factories, **tests never invoke the seed command**, and the suite is green at every phase boundary.
- **Seed restriction**: `seed` is destructive and is **not run as part of implementing this plan**. Phases 1 and 2 are checked in the browser against the current database by saving products by hand. The seed step in Phase 3 is checked by the user running it themselves when they choose.

---

## Phase 1: Add and remove products from the detail page

**Status**: Complete (2026-10-18). Automated suite green; all manual checks passed in the browser.

**User stories**: 3, 4, 5, 6, 7, 8, 9, 10, 20, 21, 22, 23

### What to build

The complete signed-in save/unsave flow on the product detail page.

The `wishlist` app, the `WishlistItem` model and its migration, and the queryset methods. The two POST-only HTMX endpoints, `wishlist:add` and `wishlist:remove`, share one base view that looks up the product, calls an add-or-remove hook scoped to `request.user`, and re-renders the button partial. This is the same structure as the cart's line-item action views. For now both endpoints require sign-in with Django's standard behavior (a signed-out request redirects to sign-in). Phase 2 replaces this with HTMX-aware handling.

The button partial has two signed-in states:

- **Not saved**: a button that POSTs to `wishlist:add` and replaces itself with the response.
- **Saved**: a button that clearly shows the product is on the wishlist and POSTs to `wishlist:remove`.

The product detail page renders `{% wishlist_button product %}`. For signed-in users it checks `contains` once and renders the matching state. For signed-out visitors it renders nothing yet; Phase 2 adds their link.

Also: register `WishlistItem` in the Django admin, and add the `wishlist` entry to CLAUDE.md's project layout.

### Acceptance criteria

- [x] `WishlistItem` exists with the fields, constraint, ordering, cascade behavior, and related name above, in one migration.
- [x] `add` is idempotent (adding twice leaves one row), `remove` of an absent item does nothing, and the unique constraint rejects a duplicate row at the database level.
- [x] Deleting a product deletes its wishlist rows. Marking it unavailable does not.
- [x] A signed-in customer's product page shows "not saved" or "saved" correctly on first load.
- [x] `wishlist:add` and `wishlist:remove` accept POST only. Each returns just the button partial (not a full page), in the state that matches the database after the request.
- [x] Adding an already-saved product leaves one row and returns "saved". Removing an unsaved product succeeds and returns "not saved". Neither ever toggles.
- [x] An unavailable product can be added and removed. An unknown pk returns 404.
- [x] A signed-out POST to either endpoint redirects to sign-in and changes no data.
- [x] One customer's add or remove never changes another customer's rows.
- [x] Staff and superuser accounts can save and remove products like customers.
- [x] `WishlistItem` appears in the Django admin with user, product, and created date listed, searchable by username.
- [x] The products app's Python code does not import from `wishlist`, and the product detail view is unchanged.

### How we'll check it

- **Automated:** queryset tests (idempotent add, no-op remove, unique constraint, cascade on product delete, no cascade on unavailable); endpoint tests (partial-only response, correct state, double add, absent remove, unavailable product, 404, GET rejected, signed-out redirect with no data change); isolation tests across two customers; detail-page tests for the saved and unsaved states.
- **Manual (current database, no seed):**
  1. Run the dev server and sign in as `customer`. Open any product and click the wishlist button. It switches to "saved" without a page reload.
  2. Reload the page. It still shows "saved." Click again; it switches back to "not saved."
  3. Open the unavailable EchoPatch and save it. That works, and its add-to-cart button still refuses.
  4. Open the same product in two tabs. Save it in tab A, then click the stale "save" button in tab B. It stays saved (and shows "saved"); it is not removed. Do the reverse with remove.
  5. Double-click the save button quickly, then check the Django admin: there is exactly one row for that user and product. Search the admin by username.
  6. Sign in as a second user (e.g. `newcustomer`) and open the same product. It shows "not saved."

---

## Phase 2: Signed-out visitors and ended sessions

**Status**: Complete (2026-10-18). Automated suite green; all manual checks passed in the browser.

**User stories**: 1, 2, 13

### What to build

The button partial gains its third state:

- **Signed out**: a plain "Save to wishlist" link (no HTMX) to the sign-in page, with `next` set to the current product page, matching the cart button for signed-out visitors.

A new `HtmxLoginRequiredMixin` in `accounts`, next to `StaffRequiredMixin`, overrides `handle_no_permission()`:

- A signed-out request carrying `HX-Request` gets a response with an `HX-Redirect` header to the sign-in page, with `next` set to the product's URL. HTMX then loads the whole sign-in page instead of swapping it into the button.
- A signed-out request without that header behaves like `LoginRequiredMixin`.

`wishlist:add` and `wishlist:remove` move onto this mixin. The cart views are unchanged; moving them is a separate follow-up (out of scope).

### Acceptance criteria

- [x] A signed-out visitor's product page shows a "Save to wishlist" link to sign-in with `next` set to that product's URL. It has no HTMX attributes.
- [x] Signing in through that link returns the visitor to the same product page. The product is **not** saved automatically.
- [x] A signed-out HTMX POST to either endpoint gets an `HX-Redirect` to sign-in with the product's URL as `next`, and changes no data.
- [x] A signed-out non-HTMX POST still redirects to sign-in and changes no data.
- [x] The cart views still use `LoginRequiredMixin`.

### How we'll check it

- **Automated:** detail-page test for the signed-out link and its `next`; endpoint tests for the HTMX `HX-Redirect` (header value includes the product's `next`) and the plain redirect, each asserting no rows changed; a mixin test for both request kinds.
- **Manual (current database, no seed):**
  1. Signed out, open a product. You see "Save to wishlist." Click it, sign in as `customer`, and land back on that product. The button shows "not saved" (or "saved" if it was already on the list).
  2. Signed in, open a product in tab A. In tab B, sign out. Back in tab A, click the wishlist button. The whole page goes to sign-in (no sign-in form appears inside the button). Sign in again and you're returned to the product.

---

## Phase 3: The wishlist page, navigation link, and demo seed data

**Status**: Complete (2026-10-18). Automated suite green; all current-database manual checks passed in the browser. The seed step's manual check is **pending**: the seed has not been run, by the agent or the user.

**User stories**: 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25

### What to build

`wishlist:list` at `/wishlist/` is a sign-in-required `ListView` over the signed-in user's own items, with products loaded in the same query (`select_related`), newest first.

- Each row shows the product's image, its name linking to `get_absolute_url`, and its price, plus an "Unavailable" badge when the product isn't available.
- A designed empty state points back to the catalog, per `docs/FRONTEND.md`.
- The page is read-only. Removal happens on the product's detail page.

A plain "Wishlist" link (no count badge) goes in the signed-in navigation with the other account links (beside "Addresses" and "Account").

The seed command gains a wishlist step. A module-level list of (product slug, days ago), following the cart seed's pattern, gives the `customer` demo login about three saved products with different backdated `created_at` values, including the unavailable EchoPatch. `newcustomer` gets none. The wipe step deletes wishlist items explicitly, as it does carts. The step uses the queryset's `add`.

### Acceptance criteria

- [x] `/wishlist/` returns 200 for signed-in customers, staff, and superusers. Signed-out visitors are redirected to sign-in with `next` set.
- [x] The page lists only the signed-in user's items, newest first.
- [x] Each row shows the image, the name linked to the product page, and the price. Unavailable products show an "Unavailable" badge.
- [x] A product that becomes unavailable stays on the list with the badge. A deleted product disappears.
- [x] A user with no items sees the designed empty state, with a link to the catalog.
- [x] The page has no remove buttons.
- [x] Signed-in users see "Wishlist" in the navbar; signed-out visitors don't.
- [x] The page loads its products without a query per row.
- [ ] The seed gives `customer` about three backdated items including EchoPatch, gives `newcustomer` none, and wipes wishlist items before rebuilding. Running it twice produces the same result. *(Implemented; pending verification: the seed has not been run.)*
- [x] No test invokes the seed command.

### How we'll check it

- **Automated:** list-view tests for the sign-in requirement, own-items-only isolation, newest-first ordering, the "Unavailable" badge, the empty state, the absence of remove controls, the navbar link for signed-in and signed-out users, and a query-count check. No seed calls, per `docs/TESTING.md`.
- **Manual, before seeding (current database):**
  1. Sign in as `customer` with the products saved in Phases 1–2. Click "Wishlist" in the navbar. The most recently saved product is at the top.
  2. Click a product name, remove it on the detail page, and go back to the wishlist page. It's gone.
  3. In the back office, mark a saved product unavailable. On the wishlist page it shows the "Unavailable" badge.
  4. Sign in as an account with nothing saved. You see the empty state, and its link goes to the catalog.
  5. Sign out and visit `/wishlist/` directly. You're sent to sign in.
- **Manual, seed (run by the user when they choose; never run as part of implementation):** after `uv run python manage.py seed`, sign in as `customer`. The wishlist page shows about three items on different dates, with EchoPatch badged "Unavailable", and EchoPatch's detail page shows the "saved" (remove) state. Sign in as `newcustomer` to see the empty state.
