# PRD: The ThoughtTronix Store — Customer Wishlist

---

## Problem Statement

ThoughtTronix customers can browse the catalog and buy, but they have no way to set a product aside for later. A customer who is interested in something they aren't ready to buy has to remember its name or keep it in their cart. A cart is the wrong place for that: it's meant for things they're about to buy, and it refuses products that aren't for sale. So a customer who wants a currently unavailable product, waiting for it to come back, has nowhere to record that at all.

## Solution

A **personal wishlist** for every signed-in customer.

- **One wishlist per customer.** No names, no settings, and nothing to create. A customer's wishlist is the set of products they've saved.
- **A wishlist button on every product detail page.** It shows whether the product is on the customer's wishlist, and it adds or removes the product without a full-page reload. After each click, the button shows what's actually saved.
- **Unavailable products can be saved.** Saving a product is about wanting it, not buying it. A product that is (or becomes) unavailable stays on the wishlist with an "Unavailable" badge until the customer removes it or the product is deleted from the catalog. The cart still refuses to sell it.
- **A "Wishlist" page**, linked from the navigation, listing everything the customer has saved, newest first, with a designed empty state.
- **Private to each customer.** Customers can only ever see and change their own wishlist. Store operators can view wishlists in the Django admin, as they already can with carts and addresses.

## User Stories

**Visitor (not signed in)**

1. As a visitor, I want to see a "Save to wishlist" link on a product's page, so that I know the store offers wishlists.
2. As a visitor, I want "Save to wishlist" to take me to the sign-in page and bring me back to the same product afterward, so that I can save it once I've signed in.

**Customer (signed in)**

3. As a customer, I want a wishlist button on every product's detail page, so that I can save a product to look at later.
4. As a customer, I want the button to show whether this product is already on my wishlist when the page loads, so that I don't have to remember.
5. As a customer, I want to add a product to my wishlist without the page reloading, so that I don't lose my place.
6. As a customer, I want to remove a product from my wishlist from its detail page without the page reloading, so that I can change my mind quickly.
7. As a customer, I want the button to update after every click to show what's actually saved, so that I can trust what it says.
8. As a customer, I want a double-click, or a click in an old tab, to leave the product in the state I asked for (an extra "add" never removes it, and an extra "remove" never adds it), so that I never accidentally undo my own action.
9. As a customer, I want a product to appear on my wishlist only once, however many times I add it, so that my list doesn't fill with duplicates.
10. As a customer, I want to be able to save a product that's currently unavailable, so that I remember it in case it comes back.
11. As a customer, I want a saved product that becomes unavailable to stay on my wishlist, so that the store doesn't delete something I chose to keep.
12. As a customer, I want a product that the store deletes from the catalog to disappear from my wishlist, so that my list never links to a product page that doesn't exist.
13. As a customer whose session has ended while a product page was open (for example, because I signed out in another tab), I want clicking the wishlist button to take me to the full sign-in page and then back to that product, so that I'm never shown a broken page.
14. As a customer, I want a "Wishlist" link in the navigation alongside my other account links, so that I can find my saved products from any page.
15. As a customer, I want my wishlist page to list every product I've saved, most recently added first, so that the things I just saved are at the top.
16. As a customer, I want each item on the wishlist page to show the product's image, name, and price, with the name linking to its product page, so that I can tell what I saved and go back to it.
17. As a customer, I want saved products that are unavailable to show an "Unavailable" badge on my wishlist page, so that I know I can't buy them right now.
18. As a customer with nothing saved, I want the wishlist page to show a designed empty state that points me back to the catalog, so that I'm not looking at a blank page.
19. As a customer, I want to remove an item by opening its product page from the wishlist page and using the button there, so that there's one consistent way to remove things.
20. As a customer, I want only my own saved products ever shown to me, and I want no request I can make to change any other customer's wishlist, so that wishlists stay private.
21. As a customer, I want other customers to be unable to see or change my wishlist, so that what I save stays private.

**Employee and admin**

22. As an employee, I want my own wishlist when I shop the store with my staff account, so that staff accounts work like customer accounts in the storefront.
23. As an admin or permitted staff member, I want to view wishlist entries in the Django admin, searchable by username, so that I can help a customer who has a question about their wishlist.

**Demo**

24. As someone demonstrating the store, I want the `customer` demo login to start with about three saved products added on different dates, including the unavailable EchoPatch, so that the ordering, the "Unavailable" badge, and the "remove" state of the button can all be shown right away.
25. As someone demonstrating the store, I want the `newcustomer` demo login to start with an empty wishlist, so that the empty state can be shown.

## Implementation Decisions

**A new `wishlist` app.** The wishlist gets its own Django app with the `wishlist` URL namespace. It depends on `products` (and on `accounts`, for one mixin). Nothing depends on it: the products app's Python code never imports from it. The only link from the catalog is the product detail template loading the wishlist template tag library. The project-layout section of CLAUDE.md gains an entry for the new app.

**Data model: one table, no container.**

- A single `WishlistItem` model with a foreign key to the user, a foreign key to the product, and `created_at`. There is no `Wishlist` model: the wishlist has no fields of its own (no name, no settings), so the set of a user's rows *is* their wishlist. This follows the shape of `Address`, not `Cart`.
- A unique constraint on (user, product) makes duplicates impossible at the database level.
- `created_at` uses a `timezone.now` default (not `auto_now_add`), matching the rest of the codebase, so the seed can backdate rows.
- Default ordering is newest first, with pk as a tiebreaker.
- Both foreign keys cascade. Deleting a user removes their wishlist, and deleting a product removes it from every wishlist. Marking a product unavailable removes nothing.
- The user foreign key's related name gives the customer's items as `user.wishlist_items`.

**Logic lives in a custom queryset/manager**, per the architecture convention: an idempotent `add(user, product)` built on get-or-create, an idempotent `remove(user, product)` that does nothing if the row is absent, and `contains(user, product)` for the button state. The views, the template tag, and the seed all use these methods rather than writing their own queries. No service module is needed, because the wishlist workflow involves no other model.

**Endpoints: separate add and remove, both idempotent.**

- `wishlist:add` and `wishlist:remove` are POST-only and take the product's pk, the same way the cart's add endpoint does. They are HTMX endpoints, not public pages, so the slug convention for public catalog URLs doesn't apply.
- There is no toggle endpoint. Each request says what the customer clicked, so a double-click or a click in an old tab still ends in the intended state, and the response then shows what's actually saved.
- Both look up the product among *all* products, not only available ones, and return 404 for a product that doesn't exist. This differs from the cart's add view on purpose, and the view's docstring says why: saving isn't buying, and the cart and checkout already enforce "unavailable products can't be bought."
- Every read and write is scoped to the signed-in user. The URL identifies only a product, never a wishlist row, so no URL can address another customer's data.
- The two views share one base view that looks up the product, calls a hook method to add or remove, and re-renders the button partial. This is the same structure as the cart's line-item action views.
- Responses contain only the button partial: no out-of-band swaps, because no navbar count needs updating. CSRF is handled by the site-wide HTMX header that's already in the base template.

**The button: one partial with three states**, rendered both on the first page load and in every HTMX response, so the states are defined in exactly one place:

- **Signed out:** a plain "Save to wishlist" link to the sign-in page with `next` set to the current product page. No HTMX, the same as the cart button for signed-out visitors.
- **Signed in, not saved:** a button that POSTs to `wishlist:add` and replaces itself with the response.
- **Signed in, saved:** a button that clearly shows the product is on the wishlist and POSTs to `wishlist:remove`.

The button looks the same whether the product is available or not. Styling uses Tailwind and DaisyUI classes only, with no JavaScript beyond HTMX, per the frontend conventions.

**Initial state comes from an inclusion template tag**, `{% wishlist_button product %}`, in the wishlist app. It reads the user from the template context, checks `contains` with a single existence query, and renders the button partial. The query runs only where the button appears. There is no wishlist context processor, and the product detail view doesn't change. This is the first inclusion tag in the codebase. It costs one query per button, which is fine on a detail page but would need revisiting if buttons were ever added to catalog grids.

**Ended sessions over HTMX.** A new `HtmxLoginRequiredMixin` in the `accounts` app, next to `StaffRequiredMixin`, overrides `handle_no_permission()`.

- For a signed-out request carrying HTMX's `HX-Request` header, it responds with an `HX-Redirect` header to the sign-in page, with `next` set to the product's URL. HTMX then loads the whole page instead of swapping the sign-in page into the button.
- For a signed-out request without that header, it behaves like `LoginRequiredMixin` and redirects to sign-in.
- Only the add and remove views use this mixin. The cart views are unchanged.

**The wishlist page.** `wishlist:list` at `/wishlist/` is a sign-in-required `ListView` over the customer's own items. Products are loaded in the same query (`select_related`), and items are ordered newest first.

- Each row shows the product's image, name (linking to the product's absolute URL), and price, plus an "Unavailable" badge where the product isn't available.
- The page has a designed empty state, as the frontend conventions require for every list view.
- The page is read-only. Items are removed from the product's detail page.
- A plain "Wishlist" link, with no count badge, goes in the signed-in navigation with the other account links.

**Staff and admin.**

- Staff accounts get a wishlist like any other signed-in user. The views require sign-in only, as the cart's do.
- `WishlistItem` is registered in the Django admin with user, product, and created date listed and searchable by username, as `Cart` and `Address` are. Access follows Django's model permissions.
- Nothing is added to the custom back office.

**Seed.** The seed command gains a step that gives the `customer` demo login about three saved products with different backdated `created_at` values, including the unavailable EchoPatch. The products come from a module-level list of (product slug, days ago), following the cart seed's pattern. `newcustomer` gets none. The wipe step deletes wishlist items explicitly, as it does carts. The seed command is the one place where apps are put together, so it importing the wishlist model doesn't break the app dependency rule.

**Testing.** pytest with plain fixtures in the project `conftest.py`, per the testing conventions; tests never run the seed command. Coverage includes:

- The queryset methods: add is idempotent, remove of an absent item does nothing, and the unique constraint holds.
- Both endpoints: each returns the partial (not a full page) with the correct button state. Adding twice leaves one row. Removing an absent product succeeds without error. Unavailable products can be added. An unknown product returns 404.
- Sign-in handling: a plain signed-out POST redirects to sign-in; a signed-out HTMX POST gets an `HX-Redirect` to sign-in with the product as `next`. Neither changes any data.
- Isolation: one customer adding or removing never changes another customer's rows, and the list page shows only the signed-in customer's items.
- The detail page: the signed-out link with `next`, and the correct saved or unsaved button for a signed-in customer.
- The list page: newest-first ordering, the "Unavailable" badge, the empty state, and the sign-in requirement.
- Cascade: deleting a product removes it from wishlists.

## Out of Scope

- Multiple wishlists per customer, wishlist names or settings, and sharing a wishlist with anyone.
- Wishlists for signed-out visitors, and automatically saving the product after a visitor signs in from the "Save to wishlist" link (they click again).
- Remove buttons on the wishlist page; removal happens on the product's detail page.
- A wishlist count badge in the navigation.
- Wishlist buttons anywhere other than the product detail page (for example, catalog grids).
- Moving items from the wishlist to the cart, and "back in stock" notifications for saved unavailable products.
- Wishlist views, reports, or dashboard numbers in the custom back office (such as "most-wishlisted products").
- Fixing the cart's own HTMX buttons, which still swap the sign-in page into place when a session has ended. That fix (moving the cart views onto the new mixin) is a separate follow-up.

## Further Notes

- **Why there's no `Wishlist` container model:** the cart needs one because a cart has behavior (totals, the checkout summary, item count). A wishlist in this scope is only a set of (user, product) pairs. If named or multiple wishlists ever come into scope, a container model can be added later with a migration.
- **The new mixin is reusable.** The cart has the same ended-session problem. Moving its views from `LoginRequiredMixin` to `HtmxLoginRequiredMixin` is the intended follow-up and would be a one-line change per view.
- **Seeding is destructive.** The seed command wipes and rebuilds the database, so it's run by hand when wanted, never automatically as part of implementing this feature.
