# PRD: The ThoughtTronix Store — Product Reviews

---

## Problem Statement

ThoughtTronix shoppers have nothing to go on but the store's own description of a product. There is no way to see what people who actually bought a product thought of it, and customers who have bought something have no way to share their experience. The store has no way to show social proof, and when feedback does exist, staff have nowhere to correct or remove a review that is abusive or wrong.

## Solution

**Product reviews** on every product detail page, written by verified buyers.

- **One review per customer per product.** A review is a rating of 1 to 5 whole stars plus a required written comment.
- **Only buyers can review.** A customer can review a product if they have a placed, shipped, or delivered order containing it. Cancelled orders don't count. Eligibility is checked only when the review is written. If the order is cancelled later, the review stays.
- **A Reviews section below the product details.** It shows the average rating (as stars and a number) and the review count. The signed-in customer's own review is pinned at the top, and everyone else's reviews follow, newest first. A product with no reviews shows a designed "No reviews yet" state.
- **Everything happens in place.** Writing, editing, and deleting a review updates only the Reviews section, with no full-page reload, so the reader keeps their place.
- **Customers manage their own reviews; staff can manage any review.** Staff moderate directly on the product page, using the same controls. When staff change someone else's review, readers can see that: the review is marked "Edited by ThoughtTronix staff".
- **Reviewer privacy.** Reviews show the reviewer's first name and last initial, never a username or full name.

## User Stories

**Shopper (anyone, signed in or not)**

1. As a shopper, I want a Reviews section on every product's detail page, below the main product details, so that I can read what buyers thought before I decide.
2. As a shopper, I want to see the average rating as five stars (rounded to the nearest whole star) plus the exact average to one decimal, so that I can judge a product at a glance.
3. As a shopper, I want to see how many reviews a product has ("1 review", "12 reviews"), so that I know how much weight to give the average.
4. As a shopper, I want a product with no reviews to show "No reviews yet" instead of a zero rating, so that a new product doesn't look badly rated.
5. As a shopper, I want reviews listed newest first, so that I see current opinions first.
6. As a shopper, I want each review to show its star rating, its comment, the reviewer's name, and the date it was written, so that I can understand who said what and when.
7. As a shopper, I want line breaks in a comment to be kept, so that longer reviews stay readable.
8. As a shopper, I want to see "Edited" on a review its author changed, so that I know it isn't the original wording.
9. As a shopper, I want to see "Edited by ThoughtTronix staff" on a review that staff changed, so that I know when the store has altered a customer's words.
10. As a shopper, I want reviews of unavailable products to stay visible, so that I can still read feedback on a product that's out of stock.

**Visitor (not signed in)**

11. As a visitor, I want a "Sign in to write a review" link in the Reviews section, so that I know how to leave one.
12. As a visitor, I want that link to bring me back to the same product after I sign in, so that I don't have to find it again.

**Customer (signed in)**

13. As a customer who hasn't bought a product, I want a short note explaining that only customers who purchased it can review it, so that I understand why there's no review form.
14. As a customer whose only order of a product was cancelled, I want to see that same note, so that the rule is applied consistently.
15. As a customer who bought a product (placed, shipped, or delivered order), I want a review form at the top of the Reviews section, so that I can share my experience.
16. As a customer, I want to pick my rating by clicking one of five stars, so that rating is quick and familiar.
17. As a customer, I want to be able to write a short comment like "Love it!", so that I'm not forced to write more than I want.
18. As a customer, I want a comment that is empty or only spaces to be rejected with a clear message, so that every review has real text.
19. As a customer, I want a comment longer than 2,000 characters to be rejected with a clear message, so that I know the limit.
20. As a customer, I want my new review to appear without a full-page reload, with the average and count updated, so that I don't lose my place.
21. As a customer, I want my own review pinned at the top of the Reviews section, so that I can always find it.
22. As a customer, I want an Edit button on my review that turns the review into a form in place, so that I can change my rating and comment without leaving the page.
23. As a customer, I want a Cancel button while editing that puts my review back as it was, so that I can back out without saving.
24. As a customer, I want saving an edit to update my review, the average, and the count without a full-page reload, so that I keep my place.
25. As a customer, I want editing my review to keep its original date and position, so that editing doesn't push it to the top of the list.
26. As a customer, I want a Delete button on my review that asks me to confirm first, so that a misclick doesn't destroy what I wrote.
27. As a customer, I want deleting my review to remove it without a full-page reload, and then to see the review form again if I still have a qualifying purchase (or the "purchase required" note if I don't), so that I can write a new one if I change my mind and am never offered a form I'm not allowed to submit.
28. As a customer, I want a form with errors to show the errors right on that form, keeping the stars and text I entered, so that I can fix the mistake without retyping.
29. As a customer, I want the Submit and Save buttons to be disabled while my request is being sent, so that a double-click doesn't send it twice.
30. As a customer who submits a review from an old tab after already reviewing the product, I want an error saying I've already reviewed it, with my text kept, so that I can copy it into my existing review instead of losing it or overwriting the review I have.
31. As a customer, I want my review to stay up if one of my orders for that product is cancelled later, so that a review I wrote in good faith isn't removed without warning.
32. As a customer, I want to be able to review a product I bought even if it's now unavailable, and to keep editing that review, so that a catalog change doesn't silence me.
33. As a customer, I want my review to show my first name and last initial (or "ThoughtTronix customer" if I haven't given a first name), so that I'm not identified by my username or my full name.
34. As a customer, I want no request I can make to change or delete another customer's review, so that reviews can't be tampered with.
35. As a customer, I want no request I can make to create a review for a product I haven't bought, so that the "verified buyer" rule can't be bypassed.
36. As a customer whose session ended while a product page was open, I want any review action to take me to the full sign-in page and back to that product, so that I'm never shown a broken page.

**Employee (staff)**

37. As an employee, I want Edit and Delete buttons on every review on every product page, so that I can moderate reviews where they appear.
38. As an employee, I want to edit and delete reviews using the same in-place controls customers use, so that there's one way to do it.
39. As an employee, when I edit another customer's review, I want it to be marked "Edited by ThoughtTronix staff", so that the change is transparent to readers.
40. As an employee, when I edit my own review, I want it marked only "Edited", so that my own edits look like any customer's.
41. As an employee, I want to be able to write my own review only if I've bought the product, like any customer, so that staff reviews meet the same standard.

**Demo**

42. As someone demonstrating the store, I want the seeded store to have reviews that obey the purchase rule, with varied ratings including a couple of 1–2 star reviews, so that the averages look realistic.
43. As someone demonstrating the store, I want at least one product with no reviews, so that the empty state can be shown.
44. As someone demonstrating the store, I want seeded examples of an "Edited" review and an "Edited by ThoughtTronix staff" review, so that both labels can be shown.
45. As someone demonstrating the store, I want the `customer` demo login to have a purchased product they haven't reviewed, a review of their own, and a product they ordered only in a cancelled order, so that the review form, the pinned review with its controls, and the "purchase required" note can all be shown right away.

## Implementation Decisions

**A new `reviews` app.** Reviews get their own Django app with the `reviews` URL namespace. It depends on `products` (the thing being reviewed), on `orders` (the purchase check), and on `accounts` (mixins and the display-name method). Nothing depends on it: no other app's Python code imports from it. The only link from the catalog is the product detail template loading the reviews template tag library, as it already does for the wishlist button. The project-layout section of CLAUDE.md gains an entry for the new app. Putting reviews in `products` was rejected because `products` would then have to import from `orders`, which already imports from `products`.

**Data model: one `Review` model.**

- A foreign key to the user and a foreign key to the product. Both cascade: deleting a user or a product deletes their reviews, as with wishlist items. Reviews aren't financial records, so they don't need to survive deletion the way order lines do.
- A unique constraint on (user, product) makes a second review impossible at the database level.
- `rating`: a small positive integer, 1 to 5 whole stars, with choices for the form and a database check constraint enforcing the range (the same approach `DiscountCode` uses for its value rules).
- `comment`: a required text field, at most 2,000 characters, with no minimum length. The form strips whitespace, so an empty or whitespace-only comment is rejected.
- `created_at` uses a `timezone.now` default (not `auto_now_add`), matching the rest of the codebase, so the seed can backdate rows.
- `edited_at`: a nullable timestamp, empty until the review is first edited and set to now on every edit. It is set explicitly by the edit, not with `auto_now`, so it never changes for any other reason, and it is the field that records *whether* a review has been edited.
- `edited_by`: a nullable foreign key to the user who made the most recent edit, set to null if that user is deleted. It records *who* made the last edit, not whether there was one.
- A database check constraint keeps the two consistent: `edited_by` may be set only when `edited_at` is set.

Together these give three distinguishable states:

| `edited_at` | `edited_by` | Meaning |
|---|---|---|
| empty | empty | Never edited |
| set | set | Edited; the last editor's account still exists |
| set | empty | Edited; the last editor's account has since been deleted |
- Default ordering is newest first by `created_at`, with pk as a tiebreaker. Editing never changes a review's position.

**The edit label** is worked out from `edited_at` and `edited_by`, as a model method or property, so templates never repeat the rule:

- Never edited (`edited_at` empty): no label.
- Last edited by the author (including a staff member editing their own review): "Edited".
- Last edited by someone else (staff editing another customer's review): "Edited by ThoughtTronix staff".
- Edited, but the last editor's account has since been deleted (`edited_at` set, `edited_by` empty): "Edited". The review is never shown as unedited.

If the author edits again after a staff edit, `edited_by` goes back to the author and the label returns to "Edited", because the words are theirs again.

**Logic lives in a custom manager/queryset and the model**, per the architecture convention. No service module is needed; the purchase check reads `orders` data but is a single query.

- `editable_by(user)`: every review for staff, only the user's own reviews for everyone else. The edit and delete views look reviews up only within this queryset.
- `has_purchased(user, product)`: whether the user has an order line for this product in an order whose status isn't cancelled (placed, shipped, or delivered). One existence query.
- A lookup for the user's existing review of a product, if any.
- `summary_for(product)`: the average rating and the review count, in one aggregate query. The average is never stored on `Product`, so it can never drift out of sync with edits and deletes.
- A per-review method saying whether a given user may change it (the author, or any staff member), used to decide whether to show Edit and Delete.

**Reviewer display name.** A `public_name()` method on `accounts.User` returns the first name and last initial ("Casey M."), the first name alone if there is no last name ("Casey"), or "ThoughtTronix customer" if there is no first name. Usernames and full names are never shown publicly. (Signup collects only username, email, and password, so many real customers will show the fallback.) Hiding usernames also matters for security: the sign-in lockout counts failures per username, so a public username would let someone lock that customer out on purpose.

**The Reviews section** sits below the product grid on the product detail page. The product detail view doesn't change. An inclusion template tag in the reviews app renders the section from the product and the user in the template context. The same section partial is rendered on the first page load and in every write response, so its states are defined in one place.

- **Summary header:** five read-only stars for the average rounded to the nearest whole star, with halves rounding up (4.5 shows five stars, matching the half-up rounding used in `orders`), then the average to one decimal (half-up via the `floatformat` filter) and the count, pluralized. With zero reviews, the header is replaced by the "No reviews yet" empty state.
- **The "your review" slot** at the top depends on the viewer:

  | Viewer | Slot shows |
  |---|---|
  | Signed out | "Sign in to write a review" link, with `next` set to this product |
  | Signed in, no qualifying purchase | A short note: only customers who've purchased this product can review it |
  | Signed in, qualifying purchase, no review yet | The create form |
  | Signed in, has a review | Their own review, pinned, with Edit and Delete |

  Staff fall into the same rows. Availability doesn't matter: a buyer can review an unavailable product.
- **The list:** every other review, newest first. Each card shows the read-only stars, the comment (autoescaped, with line breaks kept), the reviewer's public name, the date written, and any edit label. Edit and Delete appear on the viewer's own review and, for staff, on every review.
- Reviews are loaded with their users and `edited_by` users in the same query, so displaying them doesn't run one query per review.
- **The rating input** uses DaisyUI's `rating` component (radio-button stars), with an accessible label for each star. Styling is Tailwind and DaisyUI classes only, using semantic classes for errors and notes, with no JavaScript beyond HTMX, per the frontend conventions.

**Endpoints.** All are HTMX endpoints, not public pages, so they use pks, as the wishlist and cart endpoints do. All are named in the `reviews` namespace. Every endpoint re-checks permissions; hiding buttons is never the only protection.

- **Create** (POST, by product pk): looks the product up among all products, not only available ones. Checks are applied in a fixed order:
  1. No qualifying purchase: 403, before the form is involved.
  2. The user already has a review of this product: a form validation error ("You've already reviewed this product. Edit your review instead."), returned the same way as other form errors below, so the typed text is kept. An integrity error from a true race (two simultaneous submissions) is caught and turned into the same error. A duplicate is never ignored silently and never overwrites the existing review.
  3. Valid: the review is saved and the whole section is returned.
- **Edit form** (GET, by review pk): returns just that review's card in edit mode, swapped in place of the card.
- **Card** (GET, by review pk): returns that review's normal card, used by Cancel.
- **Save edit** (POST, by review pk): updates the rating and comment, sets `edited_by` to the requesting user and `edited_at` to now, and returns the whole section. Editing doesn't re-check the purchase, because eligibility applies only at creation.
- **Delete** (POST, by review pk): deletes the review and returns the whole section. The slot in that response is chosen from the table above using the current database state, exactly as on a fresh page load. A customer who still has a qualifying purchase sees the create form again. A customer whose qualifying orders have since been cancelled sees the "purchase required" note, so for them deleting a review is final. A staff member deleting someone else's review sees their own slot, which is unaffected. The Delete button uses `hx-confirm` ("Delete this review? This can't be undone."), which shows the browser's own confirm dialog. There is no separate confirmation endpoint or page.
- **Edit, card, save, and delete** look the review up only within `editable_by(user)`. A review the user isn't allowed to change returns 404, the same ownership pattern the order and address views use.
- **Signed-out requests** use `HtmxLoginRequiredMixin`. An HTMX request gets an `HX-Redirect` to the sign-in page with `next` set to the product's URL, as the wishlist endpoints do.
- CSRF is handled by the site-wide HTMX header already in the base template.

**HTMX swaps.**

- Create, save, and delete each re-render and swap the **whole Reviews section**. The server rebuilds the summary, the slot, the list, and the empty state from the database every time, so they can't fall out of sync. This is the cart's pattern (every cart action swaps the cart contents). Only the Reviews section changes, so the reader's scroll position is kept.
- Edit and Cancel swap **only that review's card**.
- Saving one review re-renders the section, which closes any other edit form that was open. This is accepted.
- **Invalid forms** (create or edit) return status 200 with only that form re-rendered with its errors, keeping the selected stars and the comment text. Response headers (`HX-Retarget` and `HX-Reswap`) point the swap at the form itself instead of the section, so nothing else on the page changes and other open edit forms stay open. This needs no global HTMX configuration change and no new dependency. (htmx 2 doesn't swap 4xx responses by default, which is why errors return 200, as Django's own form views do.)
- Submit and Save use `hx-disabled-elt` so the button is disabled while its request is in flight.

**Staff moderation** happens only on product pages, using the same endpoints and controls as customers. Nothing is added to the custom back office. `Review` is registered in the Django admin with product, user, rating, and created date listed, and searchable by username and product name, as other models are. Access follows Django's model permissions.

**Seed.** The seed command gains a reviews step, run after orders are created. The wipe step deletes reviews explicitly. The seed command is the one place where apps are put together, so importing the reviews model there doesn't break the app dependency rule.

- Every seeded review comes from a customer whose seeded orders qualify (a non-cancelled order containing that product). Each review's `created_at` is backdated to after that order's date. Reviews come from the seeded orders rather than hard-coded pairs that could break the rule.
- Ratings vary, including a couple of 1–2 star reviews.
- At least one product has no reviews, to show the empty state.
- At least one review is marked "Edited" (edited by its author) and at least one is marked "Edited by ThoughtTronix staff" (edited by the `employee` demo login).
- The `customer` demo login has: a review of at least one product they bought; at least one bought product they haven't reviewed, to show the create form; and a product they ordered only in a cancelled order, to show the "purchase required" note. The customer's order history gains one cancelled order to make that last state possible.
- The seed stays deterministic and idempotent. It uses the existing seeded random-number generator so every run gives the same result.

**Testing.** pytest with plain fixtures in the project `conftest.py`, per the testing conventions; tests never run the seed command. Coverage includes:

- Model and manager: the unique constraint, the rating check constraint, `has_purchased` for each order status (placed, shipped, and delivered count; cancelled doesn't; another user's order doesn't), `editable_by` for customers and staff, `summary_for` (average, count, no reviews), the `edited_by`-requires-`edited_at` check constraint, the edit label in every case (never edited, author edit, staff editing their own review, staff editing someone else's, author editing again after staff, last editor's account deleted), and `public_name` in every case.
- Create: a buyer's review is saved and the section is returned; a non-buyer gets 403 and nothing is saved; a cancelled-only buyer gets 403; a second review gets the "already reviewed" form error with input kept, not a 403; a whitespace-only comment, a missing rating, an out-of-range rating, and a 2,001-character comment are each rejected with the form re-rendered and the retarget headers set; a buyer can review an unavailable product; a review survives a later cancellation of its order.
- Edit and delete: the author can edit and delete; staff can edit and delete any review; another customer gets 404 and nothing changes; saving sets `edited_by` and `edited_at`; edit doesn't change ordering or `created_at`; after deleting their review, a customer with a qualifying purchase gets the create form back, and a customer whose only orders are now cancelled gets the "purchase required" note; the edit-form and card endpoints return just the card.
- Sign-in handling: a plain signed-out POST redirects to sign-in; a signed-out HTMX POST gets an `HX-Redirect` with the product as `next`. Neither changes any data.
- The product page: each slot state from the table; Edit and Delete appear only where allowed; the summary header and its pluralization; the empty state; the viewer's own review pinned first, the rest newest first; the reviewer's public name, never the username.
- Cascade: deleting a product or a user deletes their reviews; deleting the staff member who last edited a review clears `edited_by`, keeps the review and its `edited_at`, and the review still shows "Edited".

**Verification beyond tests.**

- In a browser, create, edit, cancel, save, delete, and an invalid submission each keep the reader's scroll position and swap only what they should.
- The seed is checked against a temporary throwaway database, never the developer's own `db.sqlite3`.

## Out of Scope

- Pagination or "load more" for reviews.
- Average ratings on catalog cards or anywhere other than the product detail page.
- A back-office Reviews tab or moderation queue (a read-only list of recent reviews linking to each product page is the natural follow-up).
- Half-star ratings, review titles, photos, "helpful" votes, replies, and reporting or flagging reviews.
- Staff closing a product (for example, a retired one) to new reviews.
- Re-checking purchase eligibility after a review exists, or removing reviews when orders are cancelled.
- A history of earlier versions of an edited review; only the most recent editor is recorded.
- An inline, DaisyUI-styled delete confirmation in place of the browser's dialog.

## Further Notes

- **Why eligibility is checked only at creation:** re-checking later would make reviews disappear without the customer doing anything, and would make the model depend on order changes. A review written by a real buyer stays a real buyer's review.
- **Why "Edited by ThoughtTronix staff" is shown:** letting staff change customers' words is the unusual part of this feature. Showing it protects the store's credibility and the customer's voice, at the cost of two nullable fields (`edited_at` for whether, `edited_by` for who).
- **Why the whole section is swapped:** every write changes more than one review (the summary, the slot's state, possibly the empty state). Rebuilding the section from the database on every write makes it correct by construction. Swapping single cards plus out-of-band updates was rejected as easy to get wrong.
- **The seed change touches order history.** Adding one cancelled order to the `customer` demo login changes that login's visible order history and the seeded order total by one, so anything that documents those counts needs updating with it.
- **Seeding is destructive.** The seed command wipes and rebuilds the database, so it's run by hand when wanted, never automatically as part of implementing this feature.
