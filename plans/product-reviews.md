# Plan: Product Reviews

> Source PRD: `prd/product-reviews.md`. The PRD owns the requirements; this plan owns the sequence. Where a phase says "per the PRD," the PRD's wording is authoritative.

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: A new `reviews` app with the `reviews` URL namespace. It depends on `products` (the thing reviewed), `orders` (the purchase check), and `accounts` (`HtmxLoginRequiredMixin` and `public_name()`). Nothing depends on it: no other app's Python code imports from it, and the product detail view doesn't change. The only link from the catalog is the product detail template loading the reviews template tag library, as it does for the wishlist button. The seed command is the one place that imports the reviews model. The project-layout section of CLAUDE.md gains an entry for the app in Phase 1.
- **Models**: A single `Review` model.
  - FK to the user and FK to `Product`, both `CASCADE`.
  - `rating`: small positive integer with 1–5 choices, plus a database check constraint on the range (the `DiscountCode` approach).
  - `comment`: required text, at most 2,000 characters, no minimum. The form strips whitespace.
  - `created_at` uses a `timezone.now` default (not `auto_now_add`), so the seed can backdate rows.
  - `edited_at`: nullable, set explicitly by each edit (never `auto_now`). It records *whether* the review was edited.
  - `edited_by`: nullable FK to the user, `SET_NULL`. It records *who* made the last edit.
  - Constraints: `UniqueConstraint` on (user, product); a check constraint that `edited_by` may be set only when `edited_at` is set.
  - Default ordering is newest first by `created_at`, with pk as a tiebreaker. Editing never changes position.
  - The edit label ("", "Edited", "Edited by ThoughtTronix staff") is a model method or property implementing the PRD's rules, so templates never repeat them.
- **Accounts**: `User.public_name()` returns "Casey M.", "Casey", or "ThoughtTronix customer" per the PRD. Added in Phase 1.
- **Migration**: One migration (Phase 1) creates the table. No changes to existing models' schemas.
- **Logic**: A custom manager/queryset owns `summary_for(product)` (average and count in one aggregate query), `has_purchased(user, product)` (one existence query over non-cancelled orders), the lookup of a user's own review of a product, and `editable_by(user)`. A per-review method says whether a given user may change it. No service module.
- **URLs** (all in the `reviews` namespace; HTMX endpoints, not public pages, so they use pks):

  | Path | Name | Methods | Returns |
  |---|---|---|---|
  | `/reviews/create/<product_pk>/` | `reviews:create` | POST | whole section (or the form, retargeted, on errors) |
  | `/reviews/<pk>/` | `reviews:card` | GET | that review's card (Cancel) |
  | `/reviews/<pk>/edit/` | `reviews:edit` | GET, POST | GET: the card in edit mode. POST: whole section (or the form, retargeted, on errors) |
  | `/reviews/<pk>/delete/` | `reviews:delete` | POST | whole section |

- **Authorization**:
  - Every endpoint uses `HtmxLoginRequiredMixin`, with the product's URL as `next`.
  - Create looks the product up among **all** products, and a user with no qualifying purchase gets 403 before the form is involved.
  - Card, edit and delete look the review up only within `editable_by(request.user)`, so any review the user may not change returns 404.
  - Hiding buttons is never the only protection.
  - CSRF comes from the site-wide HTMX header in `base.html`.
- **The section**: One section partial, rendered on first load by an inclusion tag on the product detail page and returned by every create, save, and delete response, so its states are defined in one place. It is rebuilt from the database every time; there are no out-of-band swaps. Edit and Cancel swap only the card. Invalid forms return 200 with only the form, using `HX-Retarget`/`HX-Reswap`. Submit and Save use `hx-disabled-elt`. Partials follow `docs/FRONTEND.md`: Tailwind and DaisyUI classes only (the DaisyUI `rating` component for stars), semantic classes for errors and notes, and no JavaScript beyond HTMX.
- **Admin**: `Review` is registered in the Django admin, listing product, user, rating, and created date, searchable by username and product name. Nothing goes in the custom back office.
- **Testing**: Follow `docs/TESTING.md`: pytest-django, plain fixtures in the project `conftest.py`, no factories, **tests never invoke the seed command**, and the suite is green at every phase boundary.
- **Seed restriction**: `seed` is **never** run against the current database (`db.sqlite3`) or the current `media/` folder, by anyone, as part of this plan. Phase 5 is verified entirely in an isolated throwaway setup, including its browser checks.

## Current data for manual checks

Phases 1–4 are checked in the browser against the current database. As of 2026-10-18 it contains:

- **`customer`** (Casey Monroe, not staff) has four orders, none cancelled:
  - #53 Delivered: MindSync and SyncRest
  - #54 Delivered: DreamWeaver
  - #55 Shipped: Seraphine Mini and Seraphine Wall Mount
  - #56 Placed: Veil
- **`employee`** (Emory Klein, staff) and **`admin`** (staff, superuser) have **no orders**.
- **`newcustomer` does not exist** in the current database. User `123` exists: not staff, blank first and last name, no orders.
- **Other buyers** are background customers with no documented password. They can't sign in, but they can be picked as a review's user in the Django admin:
  - DreamWeaver: `dcole`, `snakamura`, `tokafor`
  - SyncRest: `dcole`, `mwren`
  - Veil: `gfinch`, `mwren`, `snakamura`, `tokafor`
- **Unavailable products**: EchoPatch, MindSync Gen 1, SoulSear Mark I.
- **Nobody has ordered** ThinkVision, CrowdCalm Array, Longview Orbital Relay, SoulSear Mark II, or SoulSear Tactical Core (among others). Those products work for "not a buyer" checks.
- The back office's order status dropdown allows any status at any time, so a cancelled order can be put back to Placed afterwards.

**Before each phase's manual checks**, re-confirm the facts a check depends on: open `customer`'s order history at `/orders/`, and the back office order list for the order numbers. Data may have changed since this was written. Each check that changes data says how to undo it.

---

## Phase 1: Read-only Reviews section

**User stories**: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 33 (display only)

### What to build

The `reviews` app, the `Review` model and its migration, the admin registration, `summary_for`, the edit-label method, and `User.public_name()`.

An inclusion tag renders the Reviews section below the product grid on every product detail page:

- **Summary header**:
  - five read-only stars for the average, rounded to the nearest whole star, halves up
  - the average to one decimal
  - the review count, pluralized ("1 review", "12 reviews")
- **"No reviews yet"**: a designed empty state that replaces the header when there are no reviews.
- **The list**: every review, newest first. Each card shows:
  - read-only stars
  - the comment, autoescaped, with line breaks kept
  - the reviewer's public name
  - the date written
  - any edit label

Reviews and their users and `edited_by` users load in one query. There is no "your review" slot and no write controls yet; reviews are created in the Django admin for now.

Also add the `reviews` entry to CLAUDE.md's project layout.

### Acceptance criteria

- [x] `Review` exists with the fields, both constraints, the rating check constraint, cascades, and ordering above, in one migration.
- [x] A second review for the same (user, product), a rating of 0 or 6, and `edited_by` without `edited_at` are each rejected at the database level.
- [x] Deleting a product or a user deletes their reviews. Deleting the last editor clears `edited_by`, keeps the review and its `edited_at`, and the label is still "Edited".
- [x] The edit label is correct in every case:
  - never edited
  - author edit
  - staff editing their own review
  - staff editing someone else's review
  - author editing again after staff
  - last editor deleted
- [x] `public_name()` returns "Casey M.", "Casey", or "ThoughtTronix customer" as appropriate, and no page shows a username.
- [x] `summary_for` returns the average and count in one query, and handles no reviews.
- [x] The header shows stars rounded half-up (4.5 shows five stars), the average to one decimal, and a correctly pluralized count.
- [x] A product with no reviews shows "No reviews yet", not a zero rating.
- [x] Reviews are newest first, comments keep line breaks and are escaped, and each card shows stars, name, date, and label.
- [x] Reviews of an unavailable product are shown.
- [x] The section's query count doesn't grow with the number of reviews.
- [x] `Review` appears in the Django admin with product, user, rating, and created date listed, searchable by username and product name.
- [x] No other app's Python code imports from `reviews`, and the product detail view is unchanged.

### How we'll check it

- **Automated:** model tests (each constraint, the cascades, `SET_NULL` on the editor, every edit-label case, every `public_name` case, `summary_for`); detail-page tests (header and pluralization, half-up stars, empty state, newest-first order, kept line breaks, escaping, public name and never the username, unavailable product, query count).
- **Manual (current database, no seed).** Sign in to the Django admin as `admin`. The reviews below use users who actually bought each product, so they won't conflict with the purchase rule later.
  1. Open DreamWeaver's product page. The section shows "No reviews yet".
  2. In the admin, add three DreamWeaver reviews:
     - `dcole`: 5 stars, a two-line comment, created a week ago
     - `snakamura`: 4 stars, created three days ago
     - `tokafor`: 2 stars, created today, with `edited_at` set to now and `edited_by` set to `employee`
  3. Reload DreamWeaver. Check the summary first: the average is 3.7 with four stars and "3 reviews".
  4. Check the list: Tobi O.'s review comes first, labeled "Edited by ThoughtTronix staff"; then Sora N.; then Dana C., with the two lines of the comment shown separately. No usernames appear.
  5. In the admin, change Tobi's `edited_by` to `tokafor` and reload. The label reads "Edited". Clear `edited_by` (leave `edited_at`) and reload. It still reads "Edited". Clear `edited_at` too. The label disappears.
  6. On SyncRest, add reviews from `dcole` (5 stars) and `mwren` (4 stars). The header shows five stars, 4.5, and "2 reviews". Delete `mwren`'s review and the count reads "1 review".
  7. In the back office, mark DreamWeaver unavailable and reload. The reviews are still shown. Mark it available again.
  8. *(Fallback-name check, optional.)* In the admin, add a review on any product from user `123`, which has no first name. It shows "ThoughtTronix customer". Delete that review afterwards, because `123` hasn't bought anything.

  Keep the DreamWeaver and SyncRest reviews: later phases use them.

---

## Phase 2: Writing a review

**User stories**: 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 28, 29, 30, 31, 32 (create side), 35, 36 (create), 41

### What to build

`has_purchased` and the lookup for the user's own review, plus the "your review" slot at the top of the section, with the PRD's four states:

| Viewer | Slot shows |
|---|---|
| Signed out | "Sign in to write a review" link, with `next` set to this product |
| Signed in, no qualifying purchase | The "only customers who purchased it can review it" note |
| Signed in, qualifying purchase, no review yet | The create form |
| Signed in, has a review | Their own review, pinned first (no controls yet) |

Staff fall into the same rows. Availability doesn't matter. The list below the slot shows every *other* review.

The create form uses the DaisyUI rating component (radio stars, each with an accessible label) and a comment textarea. The form owns its validation: it strips whitespace, requires a rating of 1–5, and caps the comment at 2,000 characters.

`reviews:create` applies the PRD's checks in order:

1. No qualifying purchase: 403.
2. The user already has a review of this product: the form error "You've already reviewed this product. Edit your review instead.", with input kept. An `IntegrityError` from a true race becomes the same error.
3. Valid: the review is saved and the whole section is returned.

Invalid forms return 200 with only the form, keeping the stars and text, with `HX-Retarget`/`HX-Reswap` pointing at the form. Submit uses `hx-disabled-elt`. Signed-out requests go through `HtmxLoginRequiredMixin` with the product's URL as `next`.

### Acceptance criteria

- [x] Each slot state renders for the right viewer, including staff, and on an unavailable product.
- [x] The signed-out link goes to sign-in with `next` set to the product, and signing in returns there.
- [x] `has_purchased` is true for placed, shipped, and delivered orders, and false for cancelled orders, another user's orders, and no orders.
- [x] A buyer's valid POST saves the review and returns the whole section, with the summary updated and their review pinned first.
- [x] A non-buyer and a cancelled-only buyer each get 403, and nothing is saved.
- [x] A whitespace-only comment, a missing rating, an out-of-range rating, and a 2,001-character comment are each rejected. The form is re-rendered with errors and the input kept, the retarget headers are set, and nothing is saved.
- [x] A second review gets the "already reviewed" form error with the text kept (not a 403), and the existing review is unchanged. A simulated `IntegrityError` gives the same result.
- [x] A buyer can review an unavailable product.
- [x] A review survives a later cancellation of its order.
- [x] A signed-out HTMX POST gets an `HX-Redirect` to sign-in with the product as `next`. A plain signed-out POST redirects to sign-in. Neither saves anything.
- [x] Submit is disabled while its request is in flight (`hx-disabled-elt` present).

### How we'll check it

- **Automated:** manager tests for `has_purchased` across every status and another user's order; create-endpoint tests for each case above; detail-page tests for each slot state, including staff and an unavailable product; sign-in handling tests asserting no rows change.
- **Manual (current database, no seed).** The order numbers come from "Current data" above, so confirm them first.
  1. **Signed out:** open DreamWeaver. You see "Sign in to write a review". Click it, sign in as `customer`, and land back on DreamWeaver.
  2. **Create form and errors:** on DreamWeaver, as `customer`, the create form shows above the three Phase 1 reviews.
     - Scroll so the form is mid-screen. Submit with no stars: the error appears on the form, the page doesn't jump, and nothing else changes.
     - Pick 4 stars and type only spaces, then submit. You get the comment error, and your 4 stars stay selected.
     - Type "Love it!" and submit. The section updates in place: "4 reviews", a new average, and your review pinned at the top as "Casey M.".
  3. **Stale tab:** open SyncRest in two tabs. Submit a review in tab A. In tab B, which still shows the form, type a different comment and submit. You get "You've already reviewed this product…", with tab B's text still in the box. Reload tab A: the original review is unchanged.
  4. **Not a buyer:** as `customer`, open ThinkVision (nobody has ordered it). You see the "purchase required" note and no form.
  5. **Cancelled-only:** as `employee`, open order #56 (`customer`'s Veil order) in the back office and set it to Cancelled. As `customer`, open Veil. You see the note.
  6. **A review survives cancellation:** set order #56 back to Placed. As `customer`, review Veil. Set #56 to Cancelled again. Veil still shows your pinned review. Set #56 back to Placed. Keep the Veil review for Phase 3.
  7. **Unavailable product:** in the back office, mark Seraphine Mini unavailable (`customer` bought it in #55). As `customer`, its page shows the create form. Submit a review and it saves. Mark Seraphine Mini available again.
  8. **Staff follow the same rule:** as `employee`, who has no orders, open DreamWeaver. You see the note. Add MindSync to the cart and complete checkout as `employee`. Then open MindSync: the create form appears. Write a review. (This leaves one new order for `employee`, which Phase 4 uses.)
  9. **Ended session:** as `customer`, open MindSync in tab A. Sign out in tab B. Back in tab A, submit the form. The whole page goes to sign-in, not a form inside the section. Sign in and you return to MindSync.
  10. **Double-click:** on MindSync, double-click Submit quickly. Exactly one review exists (check the admin), and the button greyed out while the request was in flight.

---

## Phase 3: Editing and deleting your own review

**User stories**: 22, 23, 24, 25, 26, 27, 32 (edit side), 34, 36 (edit and delete)

### What to build

`editable_by(user)` (only the user's own reviews for now) and the per-review "may change" method. The pinned own review gains Edit and Delete buttons.

- **Edit** (`reviews:edit`, GET) swaps that card for the edit form, with the current stars and text filled in.
- **Cancel** (`reviews:card`, GET) swaps the normal card back.
- **Save** (`reviews:edit`, POST):
  - updates the rating and comment, sets `edited_by` to the requesting user and `edited_at` to now, and returns the whole section
  - doesn't re-check the purchase
  - an invalid save returns only the form, retargeted, with input kept
  - uses `hx-disabled-elt`
- **Delete** (`reviews:delete`, POST):
  - uses `hx-confirm` ("Delete this review? This can't be undone.")
  - deletes the review and returns the whole section, with the slot chosen from the current database: the create form if a qualifying purchase remains, otherwise the note

All four look the review up within `editable_by(request.user)`, so another user's review returns 404. Signed-out requests go through `HtmxLoginRequiredMixin` with the review's product URL as `next`.

### Acceptance criteria

- [ ] Edit and Delete appear on the viewer's own review only. Other customers' cards show no controls.
- [ ] The edit and card endpoints return just the card, in edit and normal mode respectively.
- [ ] Saving updates the rating and comment, sets `edited_by` and `edited_at`, leaves `created_at` and list position unchanged, updates the summary, and shows "Edited".
- [ ] Saving works with no qualifying purchase left (no purchase re-check), including on an unavailable product.
- [ ] An invalid save re-renders only the form with errors, input kept, and retarget headers set. Nothing changes.
- [ ] Deleting removes the review and returns the section. The slot then shows the create form if a qualifying purchase remains, and the note if it doesn't. The summary and empty state update.
- [ ] Another customer gets 404 from card, edit (GET and POST), and delete, and nothing changes.
- [ ] Signed out: an HTMX request gets an `HX-Redirect` with the product as `next`, a plain request is redirected, and neither changes data.

### How we'll check it

- **Automated:** `editable_by` tests for customers; endpoint tests for each criterion above, including another customer's 404s, ordering and `created_at` preserved after edit, and both post-delete slot states.
- **Manual (current database, no seed).** This uses the reviews `customer` wrote in Phase 2. If any are missing, write them again first.
  1. **Edit and Cancel:** as `customer`, open DreamWeaver and scroll so the section is mid-screen. Only your pinned review has Edit and Delete. Click Edit: the card becomes a form with your stars and text. Change both, then click Cancel. The card returns as it was, and the page doesn't move.
  2. **Save:** note your review's date, and its `created_at` in the admin. Click Edit, change the rating, and save. The average changes and the card shows "Edited". The date shown and the admin's `created_at` are both unchanged. (The pinned review is always first, so list position is checked in Phase 4, where staff edit a card in the middle of the list.)
  3. **Invalid save:** Edit, clear the comment to spaces, and save. The error appears on the form only, and the stars stay as chosen. Cancel.
  4. **Edit with no qualifying purchase:** as `employee`, set order #56 (Veil) to Cancelled. As `customer`, edit your Veil review and save. It works and shows "Edited".
  5. **Delete, purchase gone:** still with #56 cancelled, delete the Veil review. First dismiss the browser dialog: nothing changes. Then confirm. The review disappears and the slot shows the "purchase required" note. Set #56 back to Placed and reload. The create form is back.
  6. **Delete, purchase kept:** delete your SyncRest review and confirm. The create form appears in its place, and the count drops.
  7. **No access to others' reviews:** as `employee` (staff powers arrive in Phase 4), open DreamWeaver. None of the cards has Edit or Delete. On MindSync, only the employee's own pinned review has them.
  8. **Ended session:** as `customer`, open DreamWeaver in tab A, sign out in tab B, then click Edit in tab A. The whole page goes to sign-in and returns to DreamWeaver.

---

## Phase 4: Staff moderation

**User stories**: 37, 38, 39, 40

### What to build

`editable_by(user)` returns every review for staff, and the per-review method allows any staff member. This gives staff Edit and Delete on every review card on every product page, using the same endpoints and in-place controls as customers. The edit-label rules from Phase 1 already distinguish a staff member editing someone else's review from one editing their own. A staff member deleting someone else's review gets back a section whose slot reflects the staff member's own state, which is unaffected.

### Acceptance criteria

- [ ] Staff see Edit and Delete on every review on every product page. Customers still see them only on their own review.
- [ ] Staff can edit and delete any review through the same endpoints. Non-staff still get 404 for others' reviews.
- [ ] A staff edit of another user's review is labeled "Edited by ThoughtTronix staff". A staff edit of their own review is labeled "Edited". An author edit after a staff edit returns the label to "Edited".
- [ ] After staff delete someone else's review, the staff member's own slot is unchanged.

### How we'll check it

- **Automated:** `editable_by` and the per-review method for staff; endpoint tests for staff editing and deleting another user's review, the resulting labels, and the staff member's slot after deleting; a regression test that customers still get 404.
- **Manual (current database, no seed).** This uses `customer`'s DreamWeaver review and `employee`'s MindSync review and order from Phase 2.
  1. **Controls everywhere:** as `employee`, open DreamWeaver. Every card (Casey M., Tobi O., Sora N., Dana C.) has Edit and Delete. The employee's own slot still shows the "purchase required" note.
  2. **Staff edit:** edit Casey M.'s review in place and save. It shows "Edited by ThoughtTronix staff". Then edit Sora N.'s review, which is in the middle of the list. After saving, it stays in the same place and its date is unchanged.
  3. **Author edits again:** as `customer`, edit the same review and save. The label returns to "Edited".
  4. **Staff editing their own:** as `employee`, open MindSync and edit the employee's own pinned review. It shows "Edited" only.
  5. **Staff delete:** as `employee`, on DreamWeaver, delete Sora N.'s review and confirm. It disappears, the count drops, and the employee's slot still shows the note.
  6. **Customers unchanged:** as `customer`, DreamWeaver shows Edit and Delete only on Casey's own review.

---

## Phase 5: Demo seed data (isolated verification only)

**User stories**: 42, 43, 44, 45

### What to build

The seed command's wipe step deletes reviews explicitly. A new reviews step runs after orders are created:

- **The `customer` demo login's order history** gains one cancelled order containing a product that appears in none of their other orders.
- **Every review comes from the seeded orders**: a customer and a product from a non-cancelled order of theirs, with `created_at` backdated to after that order's date. There are no hard-coded pairs that could break the rule. Choices use the existing seeded random-number generator, so the seed stays deterministic and idempotent.
- **Demo variety:**
  - ratings vary, including a couple of 1–2 star reviews
  - at least one product has no reviews
  - at least one review is edited by its author ("Edited")
  - at least one is edited by `employee` ("Edited by ThoughtTronix staff")
- **`customer` gets** a review of at least one product they bought, at least one bought product they haven't reviewed, and the cancelled-only product (which shows the "purchase required" note).

Anything that documents the seeded order counts (the seed's own "48 here + 4 above = 52 total" comment, the closing summary line, and any README or plan text describing `customer`'s order history) is updated to match.

### Acceptance criteria

- [ ] Every seeded review satisfies the purchase rule (a non-cancelled order of that product by that user, dated before the review).
- [ ] Ratings include at least two 1–2 star reviews, and at least one product has none.
- [ ] At least one review is labeled "Edited" and at least one "Edited by ThoughtTronix staff" (edited by `employee`).
- [ ] `customer` has a review, an unreviewed bought product, and a product ordered only in a cancelled order.
- [ ] The wipe deletes reviews, and running the seed twice gives identical reviews, orders, and counts.
- [ ] Documentation of order counts matches the new seed.
- [ ] No test invokes the seed command, and the full suite, `ruff check`, and `ruff format --check` pass.

### How we'll check it

- **Automated (normal suite):** no seed calls, per `docs/TESTING.md`. Any helper that picks qualifying (user, product) pairs is pure logic and can be unit-tested with fixtures.
- **Isolated seed check. It never touches `db.sqlite3` or `media/`; it follows the procedure in `plans/account-security.md`, Phase 9:**
  1. Before starting, record a checksum and modification time for `db.sqlite3`, and a listing (names, sizes, modification times) of `media/`.
  2. Create a temporary settings module **outside the repository** (in the session scratchpad). It imports `config.settings` and overrides `DATABASES` to a new SQLite file and `MEDIA_ROOT` to a new empty folder, both in a temporary directory.
  3. Using only that settings module (`--settings`), run `migrate`, then `seed` **twice**.
  4. Against the throwaway database, check by query:
     - every review obeys the purchase rule and postdates its order
     - the rating spread includes 1–2 star reviews
     - at least one product has no reviews
     - both edit labels are present
     - `customer`'s three states are present
     - the review and order counts are identical after both runs
- **Browser check (on the throwaway setup only):**
  1. Start the dev server with the temporary settings module on a separate port (for example `runserver 8001 --settings=…`), so it can't be confused with the normal server.
  2. Signed out, open a reviewed product. You see the summary and the "Sign in to write a review" link. Open the unreviewed product and you see "No reviews yet".
  3. As `customer`:
     - the reviewed product shows the pinned review with Edit and Delete
     - the bought-but-unreviewed product shows the create form
     - the cancelled-only product shows the "purchase required" note
     - `/orders/` shows the new cancelled order
  4. Find the "Edited" and "Edited by ThoughtTronix staff" reviews. As `employee`, Edit and Delete appear on every card.
  5. Stop the server.
- **Clean-up:** re-check the `db.sqlite3` checksum and modification time and the `media/` listing, and confirm both are unchanged. Delete the temporary directory.
- **Final check (last step of the feature):** run `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check .`. All three must pass with no failures or changes needed. Report any failure with its output instead of marking the phase done.
