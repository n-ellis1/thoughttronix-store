# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

---

## 2026-10-18 — Product reviews Phase 5: demo seed data (isolated verification only)

### Prompts

1. "/implement @prd/product-reviews.md @plans/product-reviews.md implement
   phase 5"
2. "That one behavior sounds good. Since the helper gathers purchases across
   users, make sure another user's order stays paired with that user and
   never makes someone else eligible. Also check that repeated purchases
   produce one user/product pair with the earliest qualifying date. Go ahead
   and show me the failing test, then pause at RED."
3. "The test looks good. Implement qualifying_purchases so each user/product
   pair appears once with its earliest qualifying order date. Rerun this test
   and relevant existing tests, then pause at GREEN. Don't run seed against
   my current database."
4. "Looks good. Also exclude order lines whose product is null, since deleted
   products can leave historical order lines behind. Finish the rest of
   Phase 5 and the normal tests, then run the full suite and Ruff checks.
   Verify seed only in the temporary setup, and give me the temporary
   server's browser-check steps. Wait for my confirmation before marking
   complete, committing, or pushing."
5. "All Phase 5 browser checks passed, and I stopped the temporary server.
   Clean up the temporary setup and confirm my real database and media are
   unchanged. Mark Phase 5 complete, update PROMPTS.md, commit this phase,
   and push. Leave REFLECTION.md and db.sqlite3 unstaged."

### Summary

- **Outcome:** Phase 5 of `plans/product-reviews.md` is built and marked
  complete, which finishes the product reviews feature. All changes are in
  `products/management/commands/seed.py`, the new `products/test_seed.py`,
  and the README's `customer` row.
  - **TDD, one completed RED/GREEN cycle, shown RED on an assertion and
    approved before the code was written:** `qualifying_purchases()`
    returns each (user, product) pair bought in a non-cancelled order once,
    paired with its own buyer and dated by the earliest qualifying order.
    The test covered the points the user asked for: another user's order
    never makes the customer eligible, and three orders of one product give
    one pair. It failed on `assert [] == [...]` against a stub. The fix is
    one grouped query (`Min("order__created_at")` per user and product),
    filtered by `reviews.models.QUALIFYING_STATUSES` so the seed and
    `has_purchased` share one definition of a qualifying status.
  - **The user's follow-up:** order lines whose product was deleted (null)
    are excluded. A second test failed first with a `KeyError` before the
    `product__isnull=False` filter was added.
  - **Built normally:**
    - `customer` gains a cancelled Hush order (31 days ago), the only time
      they ordered Hush, so its page shows the "purchase required" note
    - the wipe deletes reviews first, and a reviews step runs after orders
    - `customer`'s two reviews (DreamWeaver; MindSync, author-edited) are
      listed in `CUSTOMER_REVIEWS` and checked against the qualifying
      purchases, so the seed fails with `CommandError` rather than break
      the purchase rule
    - background buyers review about 60% of their qualifying purchases,
      with weighted ratings and product-neutral comments, each dated
      between the order and now
    - the lowest-rated background review is edited by `employee` ("Edited
      by ThoughtTronix staff"), and one 5-star review is edited by its
      author ("Edited")
    - one seeded RNG, created in `handle`, now drives both orders and
      reviews
    - order-count docs updated: the seed's comment (48 + 5 = 53), the
      `_create_orders` docstring, the module docstring, the summary line
      (now includes reviews), and the README demo-login table
  - **Isolated seed check:** a throwaway settings module in the session
    scratchpad pointed `DATABASES` and `MEDIA_ROOT` at a temporary folder.
    `migrate` ran, then `seed` twice. A query script showed both runs
    identical: 53 orders, 43 reviews, no purchase-rule violations, ratings
    1★ ×5 and 2★ ×1, 11 products with no reviews, two "Edited" reviews and
    one staff-edited one, and `customer` with two reviewed products, four
    bought but unreviewed products, and Hush ordered only in a cancelled
    order. The user ran the browser checks on a server at port 8001 with
    those settings, and they passed. The temporary folder was then deleted.
    The `db.sqlite3` checksum and modification time and the `media/`
    listing matched the fingerprint taken before the check, both before
    and after clean-up.
  - **Checks:** 658 tests pass. `ruff check` and `ruff format --check` are
    clean. No migration this phase. The seed never ran against
    `db.sqlite3`.
- **Deviations:**
  - The agent proposed one TDD behavior, not three, because seed data and
    docs have no good TDD candidates. The user approved it and specified
    the cross-user and repeat-purchase cases the test should cover.
  - The user added the null-product exclusion, which wasn't in the plan.
  - `customer`'s reviewed products are named in the seed rather than drawn
    at random, so the demo is predictable. Each one is validated against
    the qualifying purchases, which keeps to the plan's rule that no pair
    can break the purchase rule.
- **Sideways:**
  1. Adding the Hush order draws from the shared seeded RNG before the
     background orders, so the background orders differ from the previous
     seed's. Every run is still identical. This was flagged to the user
     before the browser check.
  2. `ruff format` reformatted `seed.py` and `test_seed.py` once before the
     checks passed.

---

## 2026-10-18 — Product reviews Phase 4: staff moderation

### Prompts

1. "/implement @prd/product-reviews.md @plans/product-reviews.md implement
   phase 4"
2. "Those two look good. Go ahead one test at a time, and pause at RED before
   implementing each behavior. For the normal tests, also verify staff can
   actually delete another customer's review and that their own slot stays
   unchanged."
3. "The test looks good. Update editable_by to allow staff to access all
   reviews while keeping customers limited to their own. Rerun this test and
   relevant regression tests, then pause at GREEN."
4. "Looks good. Move on to behavior 2 and show me the failing test for staff
   seeing Edit and Delete on every review card before changing may_change."
5. "The test looks good. Update may_change to allow staff as well as the
   author, then rerun this test and relevant regression tests. Pause at
   GREEN."
6. "Looks good. Finish the remaining Phase 4 tests, then run the full suite,
   linter, and formatter checks. Give me the browser verification steps and
   wait for my confirmation before marking complete, committing, or pushing.
   Don't start Phase 5 or run seed."
7. "All six Phase 4 browser checks passed. Mark Phase 4 complete, update
   PROMPTS.md with the actual session, commit this phase, and push. Leave
   REFLECTION.md and db.sqlite3 unstaged. Don't start Phase 5 or run seed."

### Summary

- **Outcome:** Phase 4 of `plans/product-reviews.md` is built and marked
  complete. The only production change is in `reviews/models.py`.
  - **TDD, two completed RED/GREEN cycles, each shown RED on an assertion
    and approved before the code was written:**
    1. Staff can save an edit to another customer's review, which is then
       labeled "Edited by ThoughtTronix staff". Failed on `assert 404 == 200`.
       The fix: `editable_by(user)` returns every review when
       `user.is_staff`, and only the user's own reviews otherwise.
    2. Staff see Edit and Delete on every card on the product page, both
       their own pinned review and the others. Failed on a missing
       `hx-get="/reviews/2/edit/"`. The fix: `may_change(user)` allows any
       signed-in staff member as well as the author.
  - **Built normally (tests only; the existing views and `section_context`
    already handled these):**
    - staff deleting another customer's review: the review is gone, and the
      staff member's own slot is unchanged in all three states (note, create
      form, their pinned review), as the user asked
    - staff editing their own review is labeled "Edited"
    - an author edit after a staff edit goes back to "Edited"
    - a staff edit keeps the review's `created_at` and list position
    - staff get 200 from card, edit (GET and POST), and delete on another
      customer's review
    - `editable_by` and `may_change` unit tests for staff
    - the existing tests confirming customers still get 404 and see controls
      only on their own review were unchanged and pass
  - **Checks:** 656 tests pass, including 135 in `reviews` (14 new).
    `ruff check` and `ruff format --check` are clean. No migration this
    phase. The user ran all six Phase 4 browser checks and they passed.
    Seed was not run.
- **Deviations:**
  - The agent proposed two TDD behaviors instead of three. The other
    criteria (the staff delete slot, the customer 404s) would have passed
    without new code, so they couldn't produce a real RED. The user approved
    both and asked for an explicit normal test of staff deleting another
    customer's review with their slot unchanged. That test was added for all
    three slot states.
- **Sideways:**
  1. In the first full-suite run, the new staff-delete test failed in its
     own-review case. It searched for "Staff's own words.", but the page
     escapes the apostrophe as `&#x27;`. The same escaping meant its
     `assertNotContains(response, "Dana's words.")` could never fail. Both
     comments were changed to text without apostrophes, a mechanical repair
     that didn't change what the test asserts. The behavior itself was
     correct.
  2. `ruff format` reformatted `reviews/tests.py` once before the checks
     passed.

---

## 2026-10-18 — Product reviews Phase 3: editing and deleting your own review

### Prompts

1. "/implement @prd/product-reviews.md @plans/product-reviews.md implement
   phase 3"
2. "Those three look good. Go ahead one behavior and one test at a time.
   Show me the first test failing on an assertion and pause at RED before
   implementing the behavior."
3. "The test looks good. Implement the edit POST and update the duplicate
   validation to exclude the review being edited. Rerun this test and
   relevant regression tests, then pause at GREEN. We'll handle the
   ownership restriction in behavior 2 before finishing the phase."
4. "The valid-save result looks good. Move on to behavior 2 and show me the
   failing ownership test before adding the restriction. Make sure invalid
   edits are rejected and leave the database unchanged during the remaining
   normal implementation."
5. "The test looks right. Add editable_by and use it in the shared lookup,
   then rerun this test and relevant regression tests. Pause at GREEN.
   If behavior 3 already passes when we reach it, keep it as a regression
   test and report that honestly. Don't change working code just to
   manufacture a RED."
6. "Looks good. Go ahead and run behavior 3's test. If it already passes,
   keep it as regression coverage and report that; no need to force a RED."
7. "Looks good. Record behavior 3 as regression coverage that passed
   immediately, not a completed RED/GREEN cycle. Finish the remaining
   Phase 3 requirements and normal tests, especially rejecting invalid edits
   without changing the database. Run the full suite, linter, and formatter
   checks, then give me the browser steps and wait for approval before
   marking complete, committing, or pushing. Don't start Phase 4 or run
   seed."
8. "All eight Phase 3 browser checks passed. Mark Phase 3 complete, update
   PROMPTS.md, commit this phase, and push. Record behavior 3 as regression
   coverage that passed immediately, not a RED/GREEN cycle. Leave
   REFLECTION.md and db.sqlite3 unstaged. Don't start Phase 4 or run seed."

### Summary

- **Outcome:** Phase 3 of `plans/product-reviews.md` is built and marked
  complete.
  - **TDD, two completed RED/GREEN cycles, each shown RED on an assertion
    and approved before the code was written:**
    1. Saving an edit updates the rating and comment, sets `edited_by` and
       `edited_at`, keeps `created_at`, and returns the whole section with
       the new average and "Edited". The route and edit-form GET were built
       as scaffolding, so the test failed on `assert 405 == 200`. The fix:
       `Review.record_edit(editor)`, `EditReviewView.post`, and
       `ReviewForm.clean()` excluding the instance being edited.
    2. Another customer gets 404 from card, edit (GET and POST), and delete,
       and the review is unchanged. With the card and delete routes as
       scaffolding and one shared `get_review()` lookup over all reviews,
       all four cases failed on `assert 200 == 404`. The fix:
       `ReviewQuerySet.editable_by(user)`, used in that lookup.
  - **Behavior 3 is regression coverage, not a RED/GREEN cycle.** The test
    that the post-delete slot follows the database (create form if a
    qualifying purchase remains, the note if it's cancelled) passed on its
    first run. The delete view built as behavior 2's scaffolding already
    returned the shared `section_context`, which picks the slot from the
    database. Per the user, no working code was changed to force a RED; the
    test was kept as regression coverage.
  - **Built normally:**
    - invalid edits return only the edit form, input kept, retargeted at
      `#review-<pk>`, with the database unchanged (tested for a
      whitespace-only comment, a missing rating, rating 6, and 2,001
      characters); create and edit share a module-level `form_invalid`
    - `Review.may_change(user)` and a `changeable_by` filter showing Edit
      and Delete on the viewer's own card only; Delete uses `hx-confirm`
    - the edit mode of `_form.html` (takes the card's id, Save, and a Cancel
      button that GETs `reviews:card`), with per-review `auto_id`s
    - tests for the card and edit-form endpoints, controls, `editable_by`,
      list position after an edit, editing with no qualifying purchase
      (available and unavailable product), delete updating the summary, and
      signed-out HTMX and plain requests to all four endpoints
  - **Checks:** 642 tests pass, including 121 in `reviews` (30 new).
    `ruff check` and `ruff format --check` are clean. No migration this
    phase. The user ran all eight Phase 3 browser checks and they passed.
    Seed was not run.
- **Deviations:**
  - The user approved all three TDD candidates and both RED tests as
    written.
  - The agent flagged before writing behavior 3's test that it would likely
    pass immediately; the user chose to keep it as regression coverage
    rather than replace the behavior or force a RED.
- **Sideways:**
  1. Between behavior 1's GREEN and the normal implementation,
     `EditReviewView.post` ignored `is_valid()`, so an invalid edit would
     have been saved, and every per-review endpoint looked reviews up among
     all reviews. Both were deliberate, minimal-code gaps, called out at
     each GREEN and closed (behavior 2, then the invalid-edit branch with
     its database-unchanged test) before the phase was checked.
  2. `ruff format` reformatted `reviews/tests.py` and `reviews/urls.py`
     once before the checks passed.
  3. Phase 4 follow-up: `editable_by` and `may_change` state the same rule
     separately, so both must widen to staff together.

---

## 2026-10-18 — Product reviews Phase 2: writing a review

### Prompts

1. "/implement @prd/product-reviews.md @plans/product-reviews.md implement
   phase 2"
2. "Those three look good. Go ahead one behavior and one test at a time.
   Show me the first assertion failure and pause at RED before implementing
   the behavior."
3. "The test looks good. Go ahead and implement has_purchased as a single
   exists query scoped to the user, product, and qualifying order status.
   Rerun the test and relevant existing tests, then pause at GREEN."
4. "The implementation looks right. Confirm the has_purchased test and
   relevant existing tests passed. If they're green, move on to behavior 2
   and show me the failing duplicate-review test before implementing that
   behavior."
5. "Let's keep the skill's assertion-failure requirement. Use Django's test
   client with raise_request_exception=False for this test so the current
   crash becomes a 500 response. Then the expected 200 assertion should
   fail. Show me the full test and the assertion failure before
   implementing duplicate handling. No temporary error-handling code is
   needed in the view."
6. "The test looks right. Go ahead and add the duplicate validation in
   ReviewForm.clean(). Then rerun this test and relevant existing tests,
   and pause at GREEN. Keep the race-condition handling for the remaining
   normal implementation and tests."
7. "Looks good. Confirm the duplicate-review test and relevant regression
   tests passed, then move on to behavior 3. Show me the invalid-form test
   failing on an assertion and pause before implementing the retarget
   behavior."
8. "The test looks good. Add both headers to the invalid-form response so
   only the form is replaced. Rerun this test and the relevant tests, then
   pause at GREEN."
9. "Confirm behavior 3 and the relevant regression tests are green, then
   finish the remaining Phase 2 requirements and normal tests. Run the full
   suite, linter, and formatter checks. Give me the browser verification
   steps and wait for my confirmation before marking complete, committing,
   or pushing. Don't start Phase 3 or run seed."
10. "All Phase 2 manual checks passed. Mark Phase 2 complete, update
    PROMPTS.md with the actual session, commit this phase, and push. Leave
    REFLECTION.md and db.sqlite3 unstaged. Don't start Phase 3 or run
    seed."

### Summary

- **Outcome:** Phase 2 of `plans/product-reviews.md` is built and marked
  complete.
  - **TDD, three behaviors, each shown RED on an assertion and approved
    before the code was written:**
    1. `has_purchased`, across six cases (placed, shipped, and delivered
       count; cancelled, another user's order, and no orders don't), with a
       different product's order present in every case. A stub returning
       `False` gave `assert False is True`. The fix is one `.exists()` on
       `OrderItem`, using an explicit list of qualifying statuses.
    2. A second review gets the "already reviewed" form error, keeps the
       typed text and stars, and leaves the existing review unchanged. The
       fix is `ReviewForm.clean()`.
    3. An invalid create returns only the form, keeping the input, with
       `HX-Retarget: #review-form` and `HX-Reswap: outerHTML`. The
       scaffolding already returned the form partial, so the test failed on
       the missing header (`None == '#review-form'`).
  - **Built normally:**
    - `own_review` on the queryset
    - `ReviewForm` with its custom error messages
    - `CreateReviewView` at `reviews:create`: 403 before the form, and an
      `IntegrityError` from a true race caught inside `transaction.atomic()`
      and turned into the same form error
    - a shared `section_context`, used by both the inclusion tag
      (now `takes_context`) and the endpoint
    - the "your review" slot with its four states, and the `_form.html`
      partial (DaisyUI radio stars with labels, `hx-disabled-elt`)
    - the CLAUDE.md entry update
  - **Checks:** 612 tests pass, including 91 in `reviews` (47 new).
    `ruff check` and `ruff format --check` are clean. No migration this
    phase. The user ran all ten Phase 2 browser checks and they passed.
    Seed was not run.
- **Deviations:**
  - The user approved all three TDD candidates and every test as written.
  - For behavior 2, with the scaffolding in place the duplicate POST raised
    an unhandled `IntegrityError` instead of failing an assertion. Only the
    duplicate handling itself could change that. The agent stopped and
    offered two options: accept the crash as RED (its recommendation), or
    add temporary 500-handling code to the view. The user chose neither.
    They kept the skill's assertion-failure rule and had that test use
    `Client(raise_request_exception=False)`, so the crash became a 500 that
    failed the expected-200 assertion, with no temporary code in the view.
  - The user had the race-condition handling built normally, not inside
    the behavior 2 cycle.
- **Sideways:**
  1. The first behavior 2 run with `raise_request_exception=False` still
     printed the `IntegrityError` traceback. It was Django's request
     logging, not the failure. Rerunning with `--show-capture=no` showed
     the real failure, `assert 500 == 200`.
  2. The first version of the behavior 2 test matched the checked star by
     the template's exact whitespace. The agent replaced that with a
     `checked_rating` helper before the first run.
  3. In the normal tests, the "purchase required" note constant expected an
     escaped apostrophe (`&#x27;`). Literal template text isn't escaped, so
     six slot tests failed until the constant was fixed.
  4. `ruff format` reformatted `reviews/tests.py` once before the checks
     passed.
  5. Two follow-ups for Phase 3: `ReviewForm.clean()` has to leave out the
     review being edited, and the retarget id (`review-form`) is written in
     both the view and the template. Edit forms will need their own ids.

---

## 2026-10-18 — Product reviews Phase 1: read-only Reviews section

### Prompts

1. "/implement @prd/product-reviews.md @plans/product-reviews.md implement
   phase 1"
2. "Those three look good. Go ahead one behavior and one test at a time.
   Show me the first test failing on an assertion, and pause before writing
   the code to make it pass."
3. "The cases and expected labels look right. Go ahead and implement
   edit_label, then rerun this test and the relevant existing tests. Pause
   at GREEN so I can review the result."
4. "Looks good. Move on to User.public_name(), and show me the failing test
   before implementing it."
5. "The test looks good, including the last-name-only case. Go ahead and
   implement public_name(), then rerun the test and relevant existing
   tests. Pause at GREEN."
6. "Looks good. Move on to the summary header's half-up rounding, and show
   me the failing test before implementing it."
7. "The test looks good. Go ahead and implement half-up rounding, then
   rerun this test and the relevant tests. Pause at GREEN."
8. "Looks good. Finish the remaining Phase 1 requirements and normal tests,
   then run the full suite, linter, and formatter checks. Give me the
   browser verification steps and wait for my confirmation before marking
   the phase complete, committing, or pushing. Don't start Phase 2 or run
   seed."
9. "Manual testing hit 'no such table: reviews_review' on DreamWeaver. The
   reviews migration hadn't been applied to the dev database. I'm applying
   it now; record this in the session log."
10. "All Phase 1 manual checks passed, and the automated checks are good.
    Include the missing dev-database migration issue and its resolution in
    the session log. Mark Phase 1 complete, update PROMPTS.md, commit the
    completed phase, and push. Include the product-reviews PRD and plan.
    Leave my existing REFLECTION.md and db.sqlite3 changes untouched. Don't
    start Phase 2."

### Summary

- **Outcome:** Phase 1 of `plans/product-reviews.md` is built and marked
  complete.
  - **TDD, three behaviors, each shown RED on an assertion and approved
    before any code was written:**
    1. `Review.edit_label`, across six cases (never edited, author edit,
       staff editing their own, staff editing someone else's, author again
       after staff, last editor deleted).
    2. `User.public_name()`: "Casey M.", "Casey", and "ThoughtTronix
       customer" (also used when only a last name is set).
    3. Half-up star rounding in `summary_for`. The stub used Python's
       `round()`, so the 4.5 average failed with `4 == 5`. The fix uses
       `Decimal` with `ROUND_HALF_UP`, as `orders` does.
  - **Built normally:**
    - the `reviews` app, the `Review` model, and one migration with the
      unique pair, rating-range, and `edited_by`-requires-`edited_at`
      constraints
    - `for_product` (people loaded with `select_related`)
    - the admin registration
    - the `{% reviews_section product %}` inclusion tag, with `_section`,
      `_card`, and `_stars` partials using DaisyUI's `rating` component
    - the detail-template hookup; the product detail view is unchanged
    - the CLAUDE.md layout entry
  - **Checks:** 565 tests pass, including 44 new in `reviews` (7 of them
    from the TDD cycles) and 4 new in `accounts`.
    `ruff check`, `ruff format --check`, and `makemigrations --check` are
    clean. The user ran every Phase 1 manual check in the browser and they
    passed. Seed was not run.
- **Deviations:**
  - The user approved all three TDD candidates and every test as written.
  - For the rounding behavior, the agent tested `summary_for`'s `stars`
    value, not the rendered page, because the template only draws the stars
    it's given. The page header got ordinary tests afterwards. The user
    accepted this.
  - The user confirmed that a name with only a last name falls back to
    "ThoughtTronix customer".
- **Sideways:**
  1. **Missing dev-database migration.** The agent generated
     `reviews/migrations/0001_initial.py` but never applied it to
     `db.sqlite3`. The tests passed because pytest builds its own test
     database. The handoff did say the migration was unapplied and asked the
     user to run `migrate`, but only in a paragraph above the checks, not as
     a numbered first step. During manual testing, DreamWeaver's page raised
     "no such table: reviews_review". The user ran `migrate` themselves and
     the checks then passed. From now on, a phase that adds a migration will
     list applying it as step 1 of its browser checks.
  2. While writing the regular tests, the agent left a garbled date
     assertion (a dead `if False else` expression). It was replaced with
     Django's `date` filter on the local time before the tests were run.
  3. `ruff format` rewrote `edit_label`'s docstring to `""" "", …` because
     it began with a quote. The agent reworded the docstring.
  4. Ticking the plan's checkboxes with PowerShell changed the plan's line
     endings to CRLF. The agent caught it and restored LF before
     committing.

---

## 2026-10-18 — Product reviews: PRD to phased plan

### Prompts

1. "/prd-to-plan @prd/product-reviews.md — Propose manageable phases that
   each produce working behavior I can test in the browser. Explain the
   split and include acceptance criteria and manual checks for each phase.
   Don't implement anything yet."
2. "Let's combine Phases 3 and 4 into one phase for editing and deleting
   your own review. Keep staff moderation separate, giving us five phases
   total. Keep Phase 2's error handling together with creating reviews.
   Using one edit URL for GET and POST is fine too. For the seed phase,
   verify everything using a temporary database only. Don't include a step
   requiring seed against my current database. Include browser verification
   using the temporary setup if needed. Make sure the manual checks use the
   actual current data or explain the setup needed instead of assuming
   particular purchases exist. Save the revised plan to
   plans/product-reviews.md. Don't implement anything yet."
3. "The plan looks good. Update PROMPTS.md using its required format to log
   this planning session, including the phase merge and the correction to
   keep all seed verification isolated. Don't implement anything yet."

### Summary

- **Outcome:** `plans/product-reviews.md` written with five phases:
  1. Read-only Reviews section
  2. Writing a review, with all of its error handling
  3. Editing and deleting your own review
  4. Staff moderation
  5. Demo seed data, verified in isolation only

  The header records the durable decisions: the `reviews` app and its
  dependency direction, the `Review` model and constraints, `public_name()`,
  the URL table, authorization, swap rules, admin, and testing.

  A "Current data for manual checks" section records what a read-only
  query of `db.sqlite3` actually found:
  - `customer` has orders #53–#56, none cancelled.
  - `employee` and `admin` have no orders.
  - `newcustomer` doesn't exist.
  - Three products are unavailable.
  - Several products have never been ordered.
  - Back-office status changes can be undone.

  Each manual check explains its setup and how to undo it. Phase 5 follows
  the isolated procedure from `plans/account-security.md`: a throwaway
  settings module in the scratchpad, `migrate` then `seed` twice, query
  checks, and a browser check on a separate port (8001). It ends by
  confirming `db.sqlite3` and `media/` are unchanged. Nothing was
  implemented, and seed was not run.
- **Deviations:**
  - I proposed six phases and asked whether to merge edit-own (3) and
    delete-own (4). The user merged them and kept staff moderation separate.
  - The user agreed with my recommendation to keep Phase 2's error handling
    with creation, and accepted one edit URL for GET and POST.
  - **Seed correction:** my first proposal's seed phase ended with "you run
    `seed` against your own database yourself." The user ruled that out.
    All seed verification, including the browser checks, now runs only
    against a temporary database, and no step asks anyone to seed the
    current database.
  - **Real data:** my first proposal's manual checks assumed the current
    database matched the seed's `CUSTOMER_ORDERS` and used `newcustomer`.
    The user asked for checks based on actual data. A read-only query
    showed `newcustomer` doesn't exist, so the revised checks use
    `customer` on a never-ordered product, plus `employee`, as non-buyers.
- **Sideways:**
  1. My first inspection script was piped into `manage.py shell` on stdin.
     The interactive console mangled the multi-line loop and raised a
     `SyntaxError`, so most of the output was lost. I re-ran it with
     `shell -c "exec(open(...).read())"`. Both scripts were read-only and
     lived in the session scratchpad.
  2. The first saved draft had a muddled Phase 3 manual step ("add a fresh
     DreamWeaver review … (no: `snakamura` already has one)"). I caught it
     on review and replaced it before reporting: Phase 3 now checks the
     date and `created_at` stay unchanged, and the list-position check
     moved to Phase 4, where staff edit a mid-list card. I also tightened
     the "no access to others' reviews" step.
  3. Phase 2's manual checks have `employee` complete a real checkout. That
     leaves one new order in the dev database. The plan and my report say so.

---

## 2026-10-18 — Product reviews: grill-me design session and PRD

### Prompts

1. "/grill-me ThoughtTronix wants customers to leave product reviews. A
   customer can leave one review per product, with both a rating and a
   written comment. They can only review products they have purchased.
   Customers can edit and delete only their own reviews. Staff can edit and
   delete any review. Creating, editing, and deleting reviews should update
   smoothly without reloading the full page or making the user lose their
   place. Help me work through the design decisions. Check the existing
   code for useful patterns and ask me questions before making decisions.
   Don't write code or documentation yet."
2. (Q1, what counts as purchased) "Let's go with A. A placed, shipped, or
   delivered order should count, but a cancelled one shouldn't. I'm also
   fine with keeping an existing review if the order gets cancelled later,
   so we only check purchase eligibility when the review is created."
3. (Q2, app placement) "Yeah, let's make a new reviews app. ..."
4. (Q3, rating) "Yeah, 1–5 whole stars works. Let's use the star buttons
   and validate the range in both the form and database. We don't need half
   stars."
5. (Q4, comment rules) "Let's go with B, with a 2,000-character maximum and
   no minimum beyond requiring a nonblank comment. A short review like
   'Love it!' seems fine to me. Keep it plain text with line breaks
   preserved, and reject whitespace-only comments."
6. (Q5, deletion) "Let's go with A and cascade both. ..."
7. (Q6, edit tracking) "Let's go with B. Since staff can change someone
   else's review, readers should be able to tell when that happened. Show
   'Edited' for a customer's own changes and 'Edited by ThoughtTronix
   staff' when staff edited another customer's review."
8. (Q7, layout) "Let's go with A. Put reviews below the main product
   details, show the average rating and review count, and pin the
   signed-in user's review at the top. Keep the rest newest first, with a
   'No reviews yet' empty state. We can leave pagination and catalog-card
   ratings out of scope."
9. (Q8, the "your review" slot) "Yeah, the table looks good. Let's use A
   and show the note when someone hasn't purchased the product ... Staff
   should need a qualifying purchase to write their own review too, while
   still being able to edit or delete any review."
10. (Q9, HTMX swaps) "Let's go with A. Refresh the Reviews section after
    creating, saving, or deleting ... Edit and Cancel can replace just that
    review's card. I'm fine with saving one review closing another open
    edit form, but let's verify in the browser that the swaps don't make
    the user lose their place."
11. (Q10, invalid forms) "Let's go with A. If the form is invalid, just
    update that form with the errors and keep the comment and selected
    rating. ..."
12. (Q11, delete confirmation) "Let's use A with hx-confirm. ..."
13. (Q12, permission enforcement) "Yeah, let's use A. Return 404 if a
    customer tries to edit or delete someone else's review ... Use 403 for
    creating without a qualifying purchase, and check permissions on every
    request instead of just hiding buttons. Reuse the wishlist's login
    handling for signed-out HTMX requests too."
14. (Q13, duplicate submissions) "Let's go with A and disable Submit and
    Save while a request is running. ... Make sure the duplicate check
    reaches that form error rather than getting blocked with a 403."
15. (Q14, back office) "Let's go with A and keep moderation on the product
    pages. ... Put the read-only back-office Reviews tab in the follow-up
    ideas."
16. (Q15, reviewer name) "Let's use the first name and last initial, with
    'ThoughtTronix customer' as the fallback if their name is blank. ..."
17. (Q16, average display) "Let's go with B. Show five stars rounded to the
    nearest whole star, plus the average to one decimal and the review
    count. For zero reviews, just show 'No reviews yet' instead of a
    rating."
18. (Q17, seed) "Let's go with A, including a couple of 1–2 star reviews so
    the ratings have some variety. Make sure the reviews follow the purchase
    rule and cover the different states you listed. Don't run seed against
    my current database—we can verify it in a temporary database like we
    did for the wishlist."
19. (Q18, unavailable products) "Yeah, let's go with A. If they have a
    qualifying purchase, they should still be able to review an unavailable
    product. Existing reviews should stay visible and editable too."
20. "Those details look right. Staff editing their own review should show
    'Edited'; staff editing someone else's should show 'Edited by
    ThoughtTronix staff.' Use prd/product-reviews.md as the PRD filename to
    match the assignment."
21. "Those additions are fine. The cancelled demo order helps verify that
    rule, admin registration follows the existing pattern, and the card GET
    endpoint makes sense for Cancel. Keep the seed verification isolated
    from my current database."
22. "The PRD looks good overall. Please clarify two edge cases: 1. After
    deleting a review, show the create form only if the customer still has
    a qualifying purchase. Otherwise show the purchase-required note.
    2. If the last editor's account is deleted, keep an 'Edited' indicator
    rather than treating the review as never edited. Clarify how we
    distinguish those states. Update the PRD only; don't implement anything
    yet."
23. "Those updates look good. Keep the plain 'Edited' label when the
    editor's account has been deleted. Before I clear this session, update
    PROMPTS.md using the format specified in that file. Log the actual
    grill-me and PRD conversation, including the decisions and corrections.
    Don't implement anything yet."

### Summary

- **Outcome:** a design-only session; no code was written and nothing was
  run against the database. Before asking anything, the agent read the
  order model and statuses, the wishlist app (manager, views, template tag,
  `HtmxLoginRequiredMixin`), the cart and checkout HTMX patterns, the
  ownership mixins, the product detail page, the signup form fields, and
  the seed. Eighteen grill-me questions settled the design: a new `reviews`
  app (depends on `products`, `orders`, `accounts`; nothing depends on it);
  one `Review` per (user, product) with cascading foreign keys; ratings of
  1–5 whole stars checked in the form and by a database constraint;
  required plain-text comments of at most 2,000 characters; eligibility
  meaning a placed, shipped, or delivered order, checked only at creation;
  a Reviews section below the product grid with a summary header, the
  viewer's review pinned, and the rest newest first; HTMX writes swapping
  the whole section, Edit and Cancel swapping one card, and invalid forms
  re-rendered in place through `HX-Retarget`/`HX-Reswap`; `hx-confirm`
  on Delete and `hx-disabled-elt` on Submit and Save; 404 for someone
  else's review and 403 for creating without a purchase; staff moderating
  on product pages only; `User.public_name()` ("Casey M.", "Casey", or
  "ThoughtTronix customer"); and seed reviews generated from qualifying
  seeded orders. `prd/product-reviews.md` was written with `/to-prd` and
  then revised. The PRD is uncommitted. The existing seed memory note was
  updated to record that seed is checked only against a throwaway
  database.
- **Deviations:** the user overrode one recommendation. On Q4 the agent
  recommended a 10-character minimum for comments, and the user chose no
  minimum so that "Love it!" is allowed. On Q15 the agent's own first
  recommendation was a username fallback; it then suggested "ThoughtTronix
  customer" instead (a public username would let someone trigger that
  customer's sign-in lockout), and the user took that. All other questions
  went with the recommended option, with user additions: browser checks
  that the swaps keep the reader's place (Q9), duplicate submissions must
  reach the form error and not a 403 (Q13), and seed checks only in a
  temporary database (Q17). Three PRD additions the user hadn't discussed
  were flagged and then accepted: a cancelled order added to the
  `customer` demo login's history (so the "purchase required" note can be
  shown for a cancelled-only product), Django admin registration, and a
  GET "card" endpoint for Cancel. After the edge-case update, the agent
  pointed out that a review whose editor's account was deleted must have
  been edited by staff (deleting the author deletes the review), so
  "Edited by ThoughtTronix staff" could be shown there. The user kept
  plain "Edited".
- **Sideways:**
  (1) In Q12 the agent sketched a single `can_review(user, product)` that
  combined "has purchased" and "hasn't reviewed yet". Used in the create
  view, it would have sent duplicate submissions to the 403 path. The
  user's Q13 answer insisted on the form error, and the design was split
  into a 403 purchase check followed by a duplicate check in the form.
  (2) The first PRD had two gaps the user caught on review. It said
  deleting a review shows the create form again, without considering a
  customer whose orders have since been cancelled. And it worked out the
  edit label only from `edited_by`, which becomes null when the editor's
  account is deleted, so the review would have looked never edited. The
  fix: after a delete, the slot is chosen from the current database state,
  as on a fresh page load. `updated_at` was replaced with a nullable
  `edited_at` that records *whether* a review was edited, `edited_by`
  records *who*, and a check constraint keeps the two consistent.

---

## 2026-10-18 — Wishlist Phase 3 follow-up: commit the skills and verify the seed in isolation

### Prompts

1. "The tdd and implement skills are part of this lab too. Commit both skill
   folders and push them. Leave REFLECTION.md and db.sqlite3 untouched, and
   don't run seed."
2. "Help me verify the wishlist seed data using a separate temporary
   database. Leave my current db.sqlite3 untouched. Check the seeded
   wishlist contents and ordering for customer and the empty wishlist for
   newcustomer. If it passes, update the pending plan checkbox, log this
   verification in PROMPTS.md, commit those documentation changes, and
   push."

### Summary

- **Outcome:** `.claude/skills/implement/` and `.claude/skills/tdd/` were
  committed alone (`bf81b31`) and pushed. The wishlist seed was then
  verified following the isolated-check procedure from
  `plans/account-security.md`: a throwaway settings module in the session
  scratchpad redirected `DATABASES` and `MEDIA_ROOT` to a temporary folder
  (confirmed before anything ran), then `migrate` and `seed` twice. After
  each run, `customer`'s wishlist (the page's own queryset) was Pulse Halo
  (2026-10-15), EchoPatch (2026-10-06, unavailable), MoodSet (2026-09-18),
  newest first on three distinct dates; `newcustomer` had none; three rows
  total. Rendering `/wishlist/` from that database showed the same order,
  one "Unavailable" badge, the empty state for `newcustomer`, and
  EchoPatch's detail page in the saved state. A SHA-256 checksum, size, and
  modification time of `db.sqlite3` and a listing of `media/` taken before
  and after were identical; the temporary folder was deleted. The plan's
  last Phase 3 checkbox is ticked and its status line records the isolated
  verification. `REFLECTION.md` and `db.sqlite3` were left uncommitted and
  unchanged.
- **Deviations:** none. The isolated-check procedure was reused from the
  Account Security plan rather than invented.
- **Sideways:** the check script first failed to import `config` because
  it ran from the scratchpad without the repo on `PYTHONPATH`; it failed
  before connecting to any database, and it asserts the database path is
  the throwaway one before reading. Fixed by adding the repo to
  `PYTHONPATH`, then re-run after seed run 1 and again after seed run 2.

---

## 2026-10-18 — Wishlist Phase 3: the wishlist page, navbar link, and demo seed data

### Prompts

1. "/implement @prd/wishlist.md @plans/wishlist.md implement phase 3

   Don't run seed."
2. "Those three look good. Go ahead one test at a time, and pause at RED so
   I can review the test and why it failed before you write the
   implementation."
3. "The test looks good. Go ahead and scope the list to the signed-in user,
   keeping newest-first ordering. Then rerun this test and the relevant
   existing tests, and pause at GREEN."
4. "Looks good. Go ahead with behavior 2, and show me the failing
   query-count test before adding select_related."
5. "The test looks good. Comparing one item with three checks that queries
   don't increase per row without fixing an exact total. Go ahead and add
   select_related, then rerun the test and relevant tests and pause at
   GREEN."
6. "Looks good. Move on to behavior 3 and show me the failing test for
   unavailable products staying on the list with an "Unavailable" badge."
7. "The test looks good. Go ahead and add the conditional badge for
   unavailable products, then rerun the test and relevant tests and pause
   at GREEN."
8. "Looks good. Go ahead and finish the remaining Phase 3 requirements and
   normal tests, then run the full suite and Ruff checks. Don't run seed.
   Give me the browser verification steps and wait for my confirmation
   before marking the phase complete, committing, or pushing."
9. "The current-database browser checks all passed. I haven't run seed, so
   leave its manual verification noted as pending.

   Finish the phase using /implement: update the plan and PROMPTS.md,
   commit the completed wishlist work, and push to GitHub. Preserve my
   existing REFLECTION.md changes."

### Summary

- **Outcome:** `wishlist:list` at `/wishlist/` is a sign-in-required
  `ListView` scoped to `request.user`, newest first via the model ordering,
  with `select_related("product__category")`. The template shows image,
  linked name, price, saved date, and an "Unavailable" badge, has no remove
  controls, and has a designed empty state linking to the catalog. A
  "Wishlist" navbar link sits beside "Addresses". The seed gained
  `CUSTOMER_WISHLIST` (Pulse Halo 3 days, EchoPatch 12 days, MoodSet 30 days)
  built with `WishlistItem.objects.add`, and its wipe deletes wishlist items.
  README demo-logins table and CLAUDE.md's wishlist entry updated. Three
  behaviors were built test-first (own items newest first; no query per row;
  a product that becomes unavailable stays with a badge), plus eight normal
  tests (ten with parametrization). Full suite green: 517 passed. Ruff check
  and format check clean, `manage.py check` clean, no missing migrations.
  Current-database browser checks passed. The seed was never run; its manual
  check is recorded in the plan as pending. This commit also carries the
  previously uncommitted Phase 1–2 wishlist work; this entry logs only the
  Phase 3 session.
- **Deviations:** none. The three proposed TDD behaviors were approved as
  listed. The user kept the one-item-versus-three query comparison rather
  than an exact query total.
- **Sideways:** (1) The first ordering test inserted the newer item first by
  pk too, so pk ordering would also have passed; it was tightened before
  being shown at RED. (2) Building the real template revealed that
  `Product.image_url` falls back to `category.placeholder_image`, which would
  have reintroduced a query per row; the join was widened to
  `product__category`. The query-count test was not re-run against the
  narrower join to prove it catches this. (3) A stray `git stash push
  wishlist/views.py` was run by mistake; the file is untracked, so nothing
  was stashed, and the stash list and working tree were checked afterward.
  (4) The PROMPTS.md insert script failed its own safety checks twice before
  writing anything; the file was unchanged until the third attempt.

---

## 2026-10-11 — Account Security Phase 9: seed, admin passwords, docs, and the full PRD review

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 9 only.
   Verify seed using the isolated database and media folder described in the
   plan—never my current database or media folder. Finish the docs and
   admin-password checks, then run the formatter, Ruff, and full test suite.
   Tell me how to verify this phase in the browser. Don't commit yet. We need
   to review the complete Account Security Center against every PRD user
   story before the final implementation commit. Leave db.sqlite3 out of
   commits and don't restore it."
2. "The Phase 9 browser checks all worked. Before we commit, review the
   completed feature against every user story in prd/account-security.md.
   Give me a checklist showing what implements each story and what test or
   browser check verifies it. Flag anything missing or different from the
   PRD. Also identify the exact files and Django components used for
   authentication, password change, and password reset. Don't change
   anything or commit yet."
3. "Keep the current sign-in behavior, but clarify story 14 so it says the
   cooldown message appears on attempts after the fifth failure. Update
   CLAUDE.md's accounts description to include the Security Center. Keep the
   console email and isolated seed verification as documented. Don't add
   more features or commit yet."
4. "The final browser journey worked. Run uv run ruff format, uv run ruff
   check ., and uv run pytest for the final verification. Then add the Phase
   9 session log to PROMPTS.md, including the isolated seed check, browser
   checks, full PRD review, wording updates, and final verification results.
   Don't record passwords or commit yet."

### Summary

- **Outcome:**
  - **Seed:** `products/management/commands/seed.py` adds the documented
    demo customer `newcustomer`, with a usable password and a blank email.
    It is part of `DEMO_USERS`, so the seed's list of managed usernames
    includes it and reruns stay idempotent. The module docstring lists the
    new login and says every other seeded email is a confirmed
    `example.com` address with no pending request.
  - **Seed tests removed:** the two seed tests in `products/tests.py`
    (`test_seed_builds_the_demo_world`, `test_seed_is_idempotent`) called
    `call_command("seed")`. That broke the plan's "the normal test suite
    contains no seed calls" and `docs/TESTING.md`. I removed them, and
    Ruff removed the imports they left unused. The normal suite now has no
    seed calls.
  - **Admin passwords:** a new test in `accounts/tests.py`,
    `test_admin_sets_a_usable_password_for_an_unusable_password_account`,
    sets a password through the Django admin's password form on an
    unusable-password account. It checks that the account can sign in and
    that the Security Center then offers "Change password" instead of the
    contact-support message. The Phase 2 admin email tests still pass.
  - **Isolated seed check:** run entirely outside the repository.
    - I recorded a SHA-256 checksum, modification time, and size for
      `db.sqlite3`, and a listing of `media/` (13 files with sizes and
      modification times).
    - A temporary settings module in the session scratchpad imported
      `config.settings` and pointed `DATABASES` and `MEDIA_ROOT` at a new
      temporary folder. Both paths were confirmed before anything wrote.
    - With `--settings` pointing at that module, `migrate` ran once and
      `seed` twice. Both seed runs reported 6 categories, 12 tags, 34
      products, 13 users, 52 orders, and 4 discount codes.
    - Checks against the throwaway database:
      - `newcustomer` signs in and has a blank email and no pending request
      - the other 12 users have confirmed `example.com` emails and nothing
        pending
      - `admin`, `employee`, and `customer` sign in
      - no two confirmed emails match ignoring case
    - Afterwards, `db.sqlite3` and `media/` matched the recorded baseline
      exactly, and I deleted the temporary folder and scripts.
  - **Docs:**
    - The README gained `newcustomer` in the demo-login table, a note on
      confirmed seeded emails and admin-set passwords, and a new "Account
      security and email" section. It covers testing emails by copying
      links from the terminal, SMTP setup through `.env`, and a rate-limit
      table with the in-memory cache limitation (counters reset on restart,
      aren't shared between processes, and production should use a shared
      cache).
    - `plans/core-platform.md` Phase 3 task 1 gained a short "later update"
      note: signup now requires an email, per `prd/account-security.md`.
  - **Full PRD review:** a checklist mapped all 53 user stories to the code
    and to a test or browser check. No story was missing. Three differences
    were flagged:
    - story 14's message appears from the sixth attempt
    - stories 50–51 (console email, SMTP settings) have no automated test
    - stories 52–53 (seeded logins and emails) are verified only by the
      isolated seed check

    Smaller notes:
    - unusable-password users still see the Add/Change email button, which
      leads to the contact-support message
    - email confirmation happens on GET, so mail-scanner link prefetching
      could confirm an address
    - the confirmation link lands on its own result page
    - one overlong line in the `SignupView` docstring

    The review also listed the files and Django components used for
    authentication, password change, and password reset.
  - **Wording updates after the review:**
    - Story 14 in `prd/account-security.md` now says the cooldown message
      appears on every attempt after the fifth failure, and that the fifth
      failure still shows the usual incorrect-password error.
    - `CLAUDE.md`'s `accounts/` entry now describes the Account Security
      Center.
    - The sign-in behavior was not changed.
  - **Browser checks (reported by the user):** the user reported that the
    Phase 9 browser checks worked and that the final browser journey worked.
    The Phase 9 checks were: reviewing the README and docs, the missing-email
    reminder on an account with no email, the admin's password form, and the
    admin's duplicate-email form error. These ran on the current development
    database, not seeded, because `newcustomer` exists only after a seed.
    No passwords are recorded here.
  - **Final verification:** `uv run ruff format` left all 58 files
    unchanged, `uv run ruff check .` reported no problems, and
    `uv run pytest` passed 461 tests. That is 462 after Phase 8, minus the
    two removed seed tests, plus the new admin test. No migration was needed.
  - **Not done:** nothing committed. `db.sqlite3` and `media/` were not
    modified, staged, or restored.
- **Deviations:**
  - Removing the existing seed tests was my call, made to meet the plan's
    no-seed-calls rule. I flagged it, including the lost automated coverage
    of the rest of the demo world. The user kept the isolated seed check as
    the documented verification.
  - For story 14, the user kept the current behavior (the lockout message
    from the sixth attempt) and had the story's wording clarified instead of
    changing the code.
  - The user kept console email and the isolated seed check as documented,
    and asked for no further features. The smaller review notes were left
    as they are.
  - No follow-up questions were asked.
- **Sideways:**
  - The baseline step showed that `db.sqlite3` and `media/` are tracked by
    git even though `.gitignore` lists them. They were left alone.
  - My first attempt to cut the seed tests failed because the text I gave
    to match didn't fit the file. I truncated the file at the end of the
    previous test instead, and Ruff removed the unused imports.
  - The new admin test first used the URL name
    `admin:accounts_user_password_change`, which doesn't exist. Django's
    `UserAdmin` names that route `auth_user_password_change` even for a
    custom user model. After the fix it passed.
  - The first run of the seed-verification script was piped into
    `manage.py shell`. Its interactive console broke up the multi-line loops
    and reported syntax errors, so those two checks didn't run. I re-ran the
    whole script with `shell -c "exec(...)"`, and every check passed.

---

## 2026-10-11 — Account Security Phase 8: sign-in and reset-request rate limits

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 8 only. Run
   the tests and Ruff checks, then tell me how to verify it in the browser.
   Don't run seed, commit, or start Phase 9. Leave db.sqlite3 out of commits
   and don't restore it."
2. "I checked all the browser steps and they worked. I'm okay with counting
   username capitalization together, so record that in the PRD and plan.
   Leave admin-login throttling out of scope. Add the Phase 8 session log at
   the top of PROMPTS.md under today's date. Include my prompts, the changes,
   462 passing tests, and clean Ruff checks. Note that the timed window and
   cooldown expiry were checked by automated tests. Don't record passwords,
   commit, or start Phase 9 yet."

### Summary

- **Outcome:**
  - **Rate-limit helper:** `RateLimit` in `accounts/ratelimit.py` gained an
    optional `cooldown`. The event that reaches the limit holds the key
    limited for the full cooldown from that moment, so five failures late in
    the 15-minute window still lock sign-in for 15 minutes. It also gained
    `clear(key)`. The confirmation-email limit behaves as before.
  - **Two new limits** in the same module: `failed_sign_ins` (5 failures in
    15 minutes, 15-minute cooldown) and `reset_requests` (3 per hour).
  - **Sign-in:** `SignInForm.clean()` in `accounts/forms.py` refuses a
    locked username with "Too many failed sign-in attempts. Try again in 15
    minutes." before checking the password, so the right password is also
    refused. Failures are counted per submitted username, whether or not it
    exists. A successful sign-in clears the count.
  - **Reset requests:** `ResetRequestForm.save()` counts each request per
    submitted email, lowercased, whether or not it matches an account. From
    the fourth request in an hour nothing is sent, and the page is the same
    generic "If an account exists…" page. The `ResetRequestView` docstring
    was updated to mention throttling.
  - **Tests:** `accounts/tests.py` gained 14 test functions (15 test cases)
    covering:
    - the helper's cooldown running from the event that hits the limit, and
      `clear`
    - five failures locking the username, with the right password refused
      afterward; four failures not locking
    - an unknown username throttled the same way, and capitalization
      variants sharing one count
    - a successful sign-in clearing the count
    - sign-in working again 15 minutes after the fifth failure, and failures
      more than 15 minutes apart not adding up
    - locking one username not affecting another
    - a fourth reset request (same email, and mixed capitalization) sending
      nothing with an identical response; unknown addresses being counted;
      sending again after the hour; separate limits per address
  - **PRD and plan:** the user accepted counting username capitalization
    together. `prd/account-security.md` and `plans/account-security.md` now
    say the sign-in limit counts the username ignoring capitalization. The
    PRD's Out of Scope list and the plan's Phase 8 now say the Django admin's
    own sign-in page (`/admin/login/`) isn't throttled.
  - **Automated results:** `uv run pytest` passed 462 tests (447 before
    this phase), `uv run ruff check .` reported no problems, and
    `uv run ruff format --check .` found all 58 files formatted. No
    migration was needed.
  - **Timed behavior:** the 15-minute sign-in cooldown expiry and the
    one-hour reset-request window were checked by automated tests with a
    frozen clock, not by waiting in the browser.
  - **Browser checks (reported by the user):** the user reported that all
    the verification steps worked: the sign-in lock with the right password
    refused, other usernames unaffected, an unknown username locked, a
    successful sign-in clearing the count, the silent fourth reset request,
    and the count resetting after a dev-server restart (the documented
    in-memory limitation). No passwords are recorded here.
  - **Not done:** no seed run, commit, or Phase 9 work. `db.sqlite3` was not
    touched by the code changes or restored.
- **Deviations:**
  - Counting username capitalization together was my choice during the
    build. I flagged it in the report, and the user accepted it afterward.
  - I pointed out that `/admin/login/` uses its own form and isn't
    throttled, and offered to add it. The user chose to leave it out of
    scope.
  - No follow-up questions were asked.
- **Sideways:**
  - The plain window from Phase 5 couldn't give a full 15-minute cooldown on
    its own, because the lock would end when the window closed. The helper
    gained the `cooldown` option instead.
  - `ruff format --check` flagged one test signature in `accounts/tests.py`.
    `ruff format` rewrapped it (whitespace only), and the account tests
    passed again afterward.
  - In the Phase 8 report I said "17 new tests". The real count is 14 test
    functions (15 test cases with parametrization), which matches the rise
    from 447 to 462.

---

## 2026-10-11 — Account Security Phase 7: password change and its notice

### Prompts

1. "The log looks good. Commit Phase 6 and its session log with “Complete
   Account Security Center Phase 6”, leaving db.sqlite3 out. Push and report
   git status. Don't restore the database or start Phase 7 yet."
2. "@prd/account-security.md @plans/account-security.md Do Phase 7 only. Run
   the tests and Ruff checks, then tell me how to verify it in the browser.
   Don't run seed, commit, or start Phase 8. Leave db.sqlite3 out of commits
   and don't restore it."
3. "I went through all the browser verification steps and they worked. Add
   the Phase 7 session log at the top of PROMPTS.md under today's date.
   Include my prompts, the changes, 447 passing tests, and clean Ruff
   checks. Keep the unusable-password case listed as automated-only if I
   couldn't sign in to test it. Don't record any passwords, commit, or start
   Phase 8 yet."

### Summary

- **Outcome:**
  - **Phase 6 commit:** committed as `8dd7460 Complete Account Security
    Center Phase 6` (14 files, staged by name; `db.sqlite3` is gitignored
    and was never staged) and pushed to `origin/main`. Working tree clean
    afterward.
  - **Form:** `ChangePasswordForm` in `accounts/forms.py`, Django's
    `PasswordChangeForm` with DaisyUI classes: current password, new
    password, and confirmation, checked by the existing password validators.
  - **View and URL:** `ChangePasswordView` in `accounts/views.py`, built on
    Django's `PasswordChangeView`, at `accounts:password_change`
    (`/accounts/security/password/`). Django keeps the current browser
    signed in (`update_session_auth_hash`) and signs out every other
    session. On success the user returns to the Security Center with "Your
    password has been changed. Your other browsers were signed out."
    Accounts without a usable password are redirected to the overview with
    the contact-support message, on GET or POST.
  - **Change notice:** `send_password_changed_notice` in
    `accounts/emails.py` sends a plain-text notice
    (`templates/accounts/emails/password_changed.txt`) to the confirmed
    email with an absolute link to the password reset page. No confirmed
    email (including a pending-only one) means no notice.
  - **Templates:** new `templates/accounts/password_change.html`. The
    Security Center's Password section gained a "Change password" button
    for usable-password accounts only.
  - **Tests:** `accounts/tests.py` gained 10 test functions (15 test cases)
    covering:
    - the button showing for usable-password users and hidden otherwise
    - sign-in required, and the page loading for a signed-in user
    - form errors for a wrong current password, a mismatched confirmation,
      and three weak passwords, with no password change and no email
    - staying signed in, the redirect to the overview with the message, and
      the new password taking effect
    - a second client signed in beforehand being signed out
    - the notice and its reset link, and no notice without a confirmed email
    - the unusable-password redirect with the contact-support message
    The Phase 1 test `test_security_page_has_no_change_password_control_yet`
    was removed, since this phase adds that control on purpose.
  - **Automated results:** `uv run pytest` passed 447 tests (433 before
    this phase), `uv run ruff check .` reported no problems, and
    `uv run ruff format --check .` found all 58 files formatted. No
    migration was needed.
  - **Browser checks (reported by the user):** the user reported that all
    the verification steps worked: the button, the form errors, staying
    signed in while the other browser was signed out, the notice in the
    terminal and its link opening the reset page, signing in with the new
    password, and no notice for an account without a confirmed email. No
    passwords are recorded here.
  - **Unusable-password case:** listed as covered by automated tests only.
    The browser step for it was optional, depending on whether such an
    account could be signed in to, and the user's report didn't confirm it
    separately.
  - **Not done:** no seed run, commit, or Phase 8 work. `db.sqlite3` was not
    touched by the code changes or restored. The user's browser check
    changed a development account's password in it.
- **Deviations:**
  - The session log was written only when the user asked for it, following
    the log's rules.
  - No follow-up questions were asked.
- **Sideways:**
  - The first test run failed 2 cases (GET and POST) of the new
    unusable-password test. It checked for an exact message in the flashed
    list, but the contact-support message has more text after the part the
    test constant holds. It was changed to the substring check the Phase 2
    test already uses.
  - `ruff format` reformatted `accounts/views.py` and `accounts/tests.py`
    (whitespace only) before the passing run.
  - In the Phase 7 report I said "16 new tests". The real count is 10 test
    functions (15 cases), and with one Phase 1 test removed, the suite grew
    by 14 (433 to 447).

---

## 2026-10-11 — Account Security Phase 6: forgotten-password reset

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 6 only. Run
   the tests and Ruff checks, then tell me how to verify it in the browser.
   Don't run seed, commit, or start Phase 7. Leave db.sqlite3 out of commits
   and don't restore it."
2. "All the browser checks worked: uppercase confirmed email received a
   reset link, weak passwords were rejected, resetting returned me to
   sign-in without logging me in, the notice was sent, the new password
   worked, the other session was signed out, and the used link was refused.
   Unknown and pending-only addresses showed the same generic message and
   sent no email. Add the Phase 6 session log at the top of PROMPTS.md under
   today's date. Include my prompts, the changes, 433 passing tests, and
   clean Ruff checks. Note that expiry was checked by automated tests. Don't
   record my new password, commit, or start Phase 7 yet."

### Summary

- **Outcome:**
  - **Settings:** `PASSWORD_RESET_TIMEOUT = 3600` in `config/settings.py`,
    so reset links expire after 1 hour instead of Django's 3-day default.
  - **Forms:** `ResetRequestForm` (Django's `PasswordResetForm`) and
    `ResetPasswordForm` (Django's `SetPasswordForm`) in `accounts/forms.py`,
    with DaisyUI classes added. Django's own lookup already matches only
    the confirmed `email`, ignores case, and skips inactive accounts and
    unusable passwords, so pending addresses never get a reset link and no
    custom lookup was needed. The new password still goes through the
    existing password validators.
  - **Views and URLs:** `ResetRequestView`, `ResetSentView`, and
    `ResetConfirmView` in `accounts/views.py`, built on Django's reset
    views, at `accounts:password_reset`, `accounts:password_reset_done`,
    and `accounts:password_reset_confirm`. Every request lands on the same
    "sent" page. After a reset, the user is not signed in and is sent to
    sign-in with "Your password has been reset. Please sign in with your
    new password." Changing the password signs out every existing session
    (Django ties sessions to the password hash), and the used link stops
    working.
  - **Reset notice:** `send_password_reset_notice` in `accounts/emails.py`
    sends a plain-text notice to the confirmed email, with a link to the
    reset page. No confirmed email means no notice.
  - **Templates:** request, "sent", and set-new-password pages in
    `templates/accounts/`. The "sent" page shows "If an account exists for
    that address, we've sent a reset link." plus a reminder to check spam
    and double-check the address. An expired, used, or tampered link shows
    "This password reset link is no longer valid." with a "Request another
    reset" button. Plain-text reset-link email, subject, and reset-notice
    templates in `templates/accounts/emails/`. The sign-in page gained a
    "Forgot password?" link.
  - **Tests:** `accounts/tests.py` gained 14 test functions (22 test
    cases) covering:
    - the sign-in page linking to the reset page, and both reset pages
      being public
    - one reset email to the confirmed address for three capitalizations
    - unknown, pending-only, inactive, and unusable-password addresses
      getting a page identical to the baseline (CSRF tokens removed before
      comparing) and no email
    - the spam and double-check reminder
    - setting a new password without the old one, and weak passwords being
      rejected
    - no sign-in after a reset, the redirect to sign-in with the message,
      and signing in with the new password
    - a second client signed in beforehand being signed out
    - the reset notice and its link
    - used, expired, nearly expired, and tampered links
  - **Automated results:** `uv run pytest` passed 433 tests (411 before
    this phase), `uv run ruff check .` reported no problems, and
    `uv run ruff format --check .` found all 58 files formatted.
  - **1-hour expiry:** checked by automated tests only, by patching Django's
    reset-token clock (`PasswordResetTokenGenerator._now`). A link was
    refused at 1 hour and 1 second and still worked at 59 minutes. Expiry
    was not checked in the browser.
  - **Browser checks (reported by the user):** an uppercase version of a
    confirmed email received a reset link; weak passwords were rejected;
    resetting returned to sign-in without signing in; the notice was sent;
    the new password worked; the other session was signed out; the used
    link was refused; and unknown and pending-only addresses showed the
    same generic message and sent no email. The new password is not
    recorded here.
  - **Not done:** no seed run, commit, or Phase 7 work. `db.sqlite3` was not
    touched by the code changes or restored. The user's browser check
    changed a development account's password in it.
- **Deviations:**
  - The reset notice links to the reset page, so the owner can take the
    account back if the reset wasn't theirs.
  - The session log was written only when the user asked for it, following
    the log's rules.
  - No follow-up questions were asked.
- **Sideways:**
  - A first attempt to append the tests with a shell heredoc failed with a
    quoting error and wrote nothing. The tests were then added with the
    file-edit tool.
  - The first test run failed 7 cases because the expected message used an
    HTML-escaped apostrophe (`&#x27;`), but the template writes it as a
    plain `'`. The test constant was fixed.
  - `ruff format` reformatted `accounts/views.py` and `accounts/tests.py`
    (whitespace only). The accounts tests and both Ruff checks then passed
    again.
  - The end-of-phase report to the user said "26 new tests"; the actual
    count is 14 test functions (22 cases), which matches 411 → 433.

---

## 2026-10-11 — Account Security Phase 5: confirmation-email rate limit

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 5 only. Run
   the tests and Ruff checks, then tell me how to verify it in the browser.
   Don't run seed, commit, or start Phase 6. Leave db.sqlite3 out of commits
   and don't restore it."
2. "The browser checks worked: three confirmation emails were allowed, the
   next resend was blocked, changing the pending address couldn't bypass the
   limit, and Cancel still worked. Signup counted toward the same budget,
   and the newest valid link still confirmed after the budget was used up.
   Add the Phase 5 session log to the top of PROMPTS.md under today's date.
   Include my prompts, the changes, 411 passing tests, and clean Ruff
   checks. Note that the 60-minute expiry was verified by automated tests.
   Don't commit or start Phase 6 yet."

### Summary

- **Outcome:**
  - **Helper:** new `accounts/ratelimit.py` with a frozen `RateLimit`
    dataclass (`name`, `limit`, `window`) built on Django's default cache.
    `hit(key)` counts one event, opening a window at the first counted
    event; `is_limited(key)` reports whether the key has used up its
    events. A key's window ends `window` after its first event, then the
    key starts fresh, so limits are always temporary. The module docstring
    documents that counters live in the in-process memory cache, reset on
    restart, and aren't shared between processes. The confirmation budget
    is `confirmation_emails`: 3 per account per hour.
  - **Counting:** `send_email_confirmation` in `accounts/emails.py` counts
    every confirmation email it sends, so signup, new add/change requests,
    replacement addresses, and resends share one budget per account.
  - **Refusals:** `EmailChangeForm.clean()` raises "You've requested several
    confirmation emails. Please wait before requesting another." as a
    non-field error once the budget is spent, so a refused request leaves
    the existing pending request and its link unchanged. `EmailResendView`
    flashes the same message as an error and sends nothing. Cancel is not
    limited. Signup has no separate check, because a brand-new account
    always has its full budget; its email is still counted.
  - **Tests:** `conftest.py` gained an autouse fixture that clears the cache
    before every test. `accounts/tests.py` gained 12 test functions (13 test
    cases) covering:
    - the helper: counting up to the limit, the window starting with the
      first event, a fresh window after expiry, independent keys, and no
      counters leaking between tests (one test run twice)
    - the signup email counting toward the budget
    - three new addresses spending the budget, with the fourth refused
    - Resend refused once spent, with the pending address and Cancel still
      shown
    - a refused request leaving the earlier pending address and its newest
      link working
    - Cancel still working once spent
    - the budget returning after 60 minutes
    - budgets being separate per account
  - **Automated results:** `uv run pytest` passed 411 tests (398 before
    this phase), `uv run ruff check .` reported no problems, and
    `uv run ruff format --check .` found all 58 files formatted.
  - **60-minute expiry:** verified by automated tests only, using a
    controlled clock (patched `timezone.now`), both for the helper and for
    a new request succeeding again 60 minutes after the first email. It was
    not checked in the browser.
  - **Browser checks (reported by the user):** three confirmation emails
    allowed and the next resend blocked; changing the pending address
    unable to bypass the limit; Cancel still working; signup counting
    toward the same budget; and the newest valid link still confirming
    after the budget was used up.
  - **Not done:** no seed run, commit, or Phase 6 work. `db.sqlite3` was not
    touched or restored.
- **Deviations:**
  - The refused add/change request appears as a form error on the
    change-email page rather than a redirect to the overview, so the user
    sees it where they submitted.
  - The session log was written only when the user asked for it, following
    the log's rules.
  - No follow-up questions were asked.
- **Sideways:**
  - `ruff format` reflowed one long line in `accounts/ratelimit.py` before
    the checks ran; the format check then passed.
  - The end-of-phase report to the user said "15 new tests"; the actual
    count is 12 test functions (13 cases), which matches 398 → 411.

---

## 2026-10-11 — Account Security Phase 4: signup requires an email

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 4 only. Run
   the tests and Ruff checks, then tell me how to verify it in the browser.
   Don't run seed, commit, or start Phase 5."
2. "All the browser checks worked: required and invalid email errors,
   confirmed-email duplicates ignoring capitalization, signup sending a
   confirmation email, signing in before confirmation, the pending reminder
   and buttons, and confirmation clearing the reminder without sending a
   change notice. Two accounts could also sign up with the same unconfirmed
   email. Add the Phase 4 session log at the top of PROMPTS.md under today's
   date. Record my prompts, the changes, 398 passing tests, and the clean
   Ruff checks. Don't commit or start Phase 5 yet."

### Summary

- **Outcome:**
  - **Form:** `SignupForm` gained a required **Email address** field,
    ordered between username and password. `clean_email` normalizes the
    address and rejects one that another account has already confirmed,
    ignoring case, with the shared "already registered" message. Another
    account's pending address doesn't block signup. The field isn't in
    `Meta.fields`, so it's never saved as the confirmed email. The
    docstring that said signup asks for no email was rewritten.
  - **View:** `SignupView.form_valid` saves the account (confirmed email
    blank), makes the signup address its pending address through Phase 2's
    `request_email_change()`, and sends the confirmation link right away.
    Signup still redirects to sign-in, with no auto sign-in. The success
    message now reads "Account created — you can now sign in. Check your
    inbox at <address> to confirm your email address."
  - **Template:** no change. The signup template already renders every
    field and its help text, and the Security Center already showed the
    reminder plus the pending address with Resend and Cancel after Phase 3.
  - **Core PRD:** story 6 in `prd/core-platform.md` now says signup
    requires an email, with a note pointing to `prd/account-security.md`.
  - **Tests:** the existing signup tests in `accounts/tests.py` were
    switched to a shared `signup()` helper that includes an email. New
    tests cover:
    - a blank or invalid email producing a field error, with no account
      and no email sent
    - an address another account has confirmed, in two capitalizations,
      showing "already registered"
    - an address another account has only pending being accepted
    - the new account having a blank confirmed email, the signup address
      as pending, and exactly one confirmation email to that address
    - signing in right after signup, before confirming
    - the Security Center reminder, pending address, "Link sent", Resend,
      and Cancel for an unconfirmed new account
    - the signup link confirming the address with no change notice sent
  - **Automated results:** `uv run pytest` passed 398 tests (389 before
    this phase), `uv run ruff check .` reported no problems, and
    `uv run ruff format --check .` found all 57 files formatted.
  - **Browser checks (reported by the user):** required and invalid email
    errors; confirmed-email duplicates rejected ignoring capitalization;
    signup sending a confirmation email; signing in before confirming; the
    pending reminder and buttons on the Security Center; confirmation
    clearing the reminder with no change notice; and two accounts signing
    up with the same unconfirmed email.
  - **Not done:** no seed run, commit, or Phase 5 work. The confirmation
    rate limit, including counting the signup email, is Phase 5.
- **Deviations:**
  - The success message includes the signup address so the customer can
    spot a typo. The plan only asked for a "check your inbox" message.
  - The session log was written only when the user asked for it, following
    the log's rules.
  - No follow-up questions were asked.
- **Sideways:** nothing went wrong. The suite and Ruff were green on the
  first run.

---

## 2026-10-11 — Account Security Phase 3: managing a pending request (Resend/Cancel)

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 3 only. Run
   the tests and Ruff checks, then tell me how to verify it in the browser.
   Don't run seed, commit, or start Phase 4."
2. "The browser checks all worked: pending status, Resend replacing the old
   link, confirmation clearing the pending section, Cancel keeping the
   confirmed email and invalidating the link, and both action URLs returning
   405 when opened directly. Add the Phase 3 session log at the top of
   PROMPTS.md under today's date. Include my prompts, the changes, 389
   passing tests, clean Ruff checks, and the browser results. Make clear
   that expiry and unusable-password cases were checked through automated
   tests. Don't commit or start Phase 4 yet."

### Summary

- **Outcome:**
  - **Model:** `User.resend_email_link()` issues a fresh link for the same
    pending address. Earlier links stop working, and the 24-hour clock
    restarts. Cancel reuses Phase 2's `clear_pending_email()`. No migration
    was needed.
  - **Views and URLs:** `PendingEmailActionView` is a shared base that
    requires sign-in and accepts only POST, so a GET returns 405.
    `EmailResendView` (`accounts:email_resend`) and `EmailCancelView`
    (`accounts:email_cancel`) build on it. Both return to the overview with
    a success message. With nothing pending, both redirect to the overview
    with "You have no pending email change." and send nothing. These
    actions don't need the current password, so accounts with an unusable
    password can use them; add/change stays blocked for those accounts.
  - **Template:** the overview's email section shows the pending address
    with a **Link sent** or **Link expired** badge, plus **Resend** and
    **Cancel** buttons as POST forms with CSRF tokens.
  - **Tests:** `accounts/tests.py` gained a "Managing a pending request"
    section with 11 test functions (14 runs). They cover:
    - the pending address with "Link sent", and "Link expired" after 24
      hours (time controlled by backdating `email_link_sent_at`)
    - no pending block when nothing is pending
    - Resend sending one new email, the old link refused, and the new link
      confirming
    - Resend making an expired request confirmable again
    - Cancel clearing the request, refusing its link, and keeping the
      confirmed email
    - GET returning 405 and sign-in being required, for both actions
    - the harmless no-pending case, for both actions
    - an unusable-password account resending, confirming, and canceling
  - **Automated results:** `uv run pytest` passed 389 tests (375 before
    this phase), `uv run ruff check .` reported no problems, and
    `uv run ruff format --check .` found all 57 files formatted.
  - **Browser checks (reported by the user):** the pending address and
    status showed after a request; Resend replaced the old link (the old
    link was refused and the new one worked); confirming cleared the pending
    section; Cancel kept the confirmed email and made the link invalid; and
    opening both action URLs directly returned 405.
  - **Checked by automated tests only:** the "Link expired" badge after 24
    hours, Resend on an expired request, and the unusable-password path
    (resend, cancel, and confirm). None of these was checked in the
    browser.
  - **Not done:** no seed run, commit, or Phase 4 work.
- **Deviations:**
  - Resend is allowed on an expired request and gives it a fresh 24-hour
    link. The plan didn't say either way. This matches the PRD's "get a new
    one if the first email got lost or expired."
  - The session log was written only when the user asked for it, following
    the log's rules.
  - No follow-up questions were asked.
- **Sideways:** nothing went wrong. The suite and Ruff were green on the
  first run.

---

## 2026-10-11 — Account Security Phase 2: add/change email, confirmation, admin protection

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 2 only. Run
   the tests and Ruff checks, then tell me how to verify it in the browser.
   Don't run seed, commit, or start Phase 3. Before applying the migration,
   check for duplicate emails and back up my current database. Keep my
   existing store data and uploaded images."
2. "All the browser checks worked: adding an email in a private window,
   changing email, replacing and reusing links, wrong-password and
   duplicate-email errors, and the admin override clearing a pending request
   without a notice. I'm okay with rejecting a request for your own confirmed
   email. Add that decision to the PRD and plan. Then add the Phase 2 session
   log to PROMPTS.md with my prompts, the 373 passing tests, clean Ruff
   checks, backup and migration details, and my browser results. Note the
   immediate confirmation on opening a link and the email-scanner
   limitation. Don't commit or start Phase 3 yet."
3. "The own-email browser check worked too: CUSTOMER@example.com showed the
   error and sent no email. Add that result to the Phase 2 log. Then commit
   Phase 2, including the updated PRD, plan, log, and migrated db.sqlite3,
   with "Complete Account Security Center Phase 2". Push and confirm git
   status is clean. Keep the backup outside the repo, and don't start
   Phase 3 yet."

### Summary

- **Outcome:**
  - **Before migrating:**
    - **Duplicate check:** a read-only query of `db.sqlite3` found 12 users,
      no blank emails, and no case-insensitive duplicates.
    - **Backup:** the database was copied with SQLite's backup API, and
      `media/` with all 13 product images, to
      `../thoughttronix-store-backups/before-security-phase2-20261011-153036/`
      (outside the repo). The copy passed `PRAGMA integrity_check` and had
      12 users and 35 products.
  - **Migration:** `accounts/migrations/0002_pending_email_and_unique_email.py`
    adds `pending_email`, `email_token` and `email_link_sent_at`, and a
    unique index on `LOWER(email)` that skips blank emails. Applied to the
    dev database without errors. Afterward: still 12 users and 35 products,
    all 13 images in `media/products/`, every existing email kept as the
    confirmed address, and no pending requests.
  - **Model:** `User` gains `request_email_change`, `confirm_pending_email`
    and `clear_pending_email`. The manager gains `email_taken` (confirmed
    addresses only, case-insensitive) and `for_email_token`, which returns
    the account for a signed link, or nothing if the link is tampered,
    expired (24 hours from `email_link_sent_at`), replaced, or used. Each
    request gets a fresh random token, so only the newest link works.
    Confirming checks uniqueness again. If two accounts race for the same
    address, the database constraint picks the winner, and the loser keeps
    its old email and loses its pending request.
  - **Views and URLs:** `accounts:email_change` (sign-in required, asks for
    the new address and the current password, and redirects accounts with
    unusable passwords to the overview with the contact-support message)
    and `accounts:email_confirm` (public, never signs anyone in or changes
    who is signed in).
  - **Emails:** `accounts/emails.py` sends plain-text emails from
    `templates/accounts/emails/`: the confirmation link to the pending
    address, and the email-changed notice to the old confirmed address.
    First-time additions send no notice.
  - **Templates:** the overview has an **Add email** / **Change email**
    button. New pages: the email form and the confirmation result
    (confirmed, address taken, or link no longer valid).
  - **Admin:** `AdminUserChangeForm` turns a duplicate email into a field
    error. `UserAdmin.save_model` clears any pending request when an admin
    changes the email, with no notice. The pending fields are read-only in
    the admin.
  - **Settings:** email settings are read from `.env` via environs. The
    default is the console backend, and the default sender is
    `ThoughtTronix <no-reply@example.com>`. `.env.example` has commented
    SMTP placeholders. With no `.env` present, a check confirmed the console
    backend is active.
  - **PRD and plan:** both now record the decision to reject a request for
    the account's own confirmed address, ignoring case.
  - **Tests:** `accounts/tests.py` gained 27 test functions (29 runs) in the
    first round. They cover:
    - the constraint, written straight to the database
    - button labels
    - wrong-password and duplicate errors
    - an address pending on another account not blocking a request
    - one email per request, sent to the new address
    - replaced, used, tampered and expired links (24 hours, plus a
      just-under-24-hours case)
    - confirming while anonymous and while signed in as someone else
    - the change notice vs. no notice for a first addition
    - the two-account race, plus a database-level race
    - unusable-password accounts being blocked
    - the admin clearing pending requests, keeping them on unrelated
      edits, and showing duplicates as form errors

    The Phase 1 test that checked for "no action controls" was narrowed to
    check only for Change password, since the email buttons now exist.
  - **Automated results:**
    - First round: `uv run pytest` passed 373 tests, `uv run ruff check .`
      reported no problems, and `uv run ruff format --check .` found all 57
      files formatted.
    - Second round: after adding the own-address test (see Sideways), 375
      passed with the same clean Ruff results.
  - **Browser checks (reported by the user):** adding an email and
    confirming it in a private window, changing email, a replaced link
    refused and a reused link refused, wrong-password and duplicate-email
    errors, and an admin email change clearing a pending request without
    sending a notice. In a later check, requesting `CUSTOMER@example.com`
    as `customer` showed the "That's already your confirmed email." error
    and printed no email.
  - **Commit:** committed as "Complete Account Security Center Phase 2"
    with the updated PRD, plan, this log, and the migrated `db.sqlite3`,
    then pushed to `origin/main`. The backup stays outside the repo.
  - **Not done:** no seed run or Phase 3 work.
- **Deviations:**
  - The agent added a rule the PRD didn't have: a request for your own
    current confirmed email is rejected. The user accepted it and asked for
    it to be written into the PRD and plan.
  - **Confirmation happens on opening the link.** A plain page load
    confirms the address, as the plan's manual check describes, with no
    extra button to press. **Known limitation:** an email security scanner
    or link previewer that opens links automatically could confirm a
    pending address without the person clicking. The change still needs the
    current password to request, and the link only confirms the address it
    was sent to, but a confirm-button step would close this gap if it
    matters later.
  - The overview doesn't show the pending address yet; that comes with
    Resend/Cancel in Phase 3. Until then, the success message is the only
    sign a request is in progress.
  - No follow-up questions were asked.
- **Sideways:**
  - The first attempt to append tests through a shell heredoc failed with a
    quoting error, because an apostrophe in a test string broke the
    heredoc. The tests were added with the file editor instead.
  - When the own-address rule was added to the plan's acceptance criteria,
    there turned out to be no automated test for it. The rule had been
    built but not tested in the first round. A test with two
    capitalizations was added, so the suite went from 373 to 375.

---

## 2026-10-11 — Account Security Phase 1: read-only Security Center overview

### Prompts

1. "@prd/account-security.md @plans/account-security.md Do Phase 1 only. Run
   the tests and Ruff checks, then tell me how to verify it in the browser.
   Don't start Phase 2, run seed, or commit yet."
2. "The browser checks all worked: customer, employee, and admin can open
   Account, there are no action buttons, and signing out hides the link.
   Opening the page while signed out sends me to login, then back to the
   Security Center after signing in. Add this session's log at the top of
   PROMPTS.md under today's date. Record my prompts in order, the changes,
   automated results, and browser checks. Don't commit or start Phase 2 yet."

### Summary

- **Outcome:**
  - **View and URL:** `accounts/views.py` gains `SecurityView`
    (`LoginRequiredMixin` + `TemplateView`), routed at
    `/accounts/security/` as `accounts:security`. It reads everything it
    needs from `request.user`. No migration was needed for this phase.
  - **Template:** `templates/accounts/security.html` has two cards.
    - **Email** shows the confirmed address, or the "Add an email so you
      can recover your account." warning when the email is blank.
    - **Password** shows a short description, or the "contact support"
      message when the password is unusable.
    - There are no action buttons, per the plan.
  - **Navbar:** `templates/base.html` has an "Account" link right after
    "Addresses", for signed-in users only.
  - **Tests:** `accounts/tests.py` gains 11 tests (13 test runs, because the
    role test runs once each for customer, staff and superuser). They cover:
    - access for each role
    - the anonymous redirect to sign-in with `next` set
    - the confirmed email vs. the reminder
    - the unusable-password message, both shown and hidden
    - no Add email, Change email or Change password controls
    - the navbar link showing for signed-in users, after "Addresses", and
      hidden from visitors
  - **Automated results:** `uv run pytest` passed (346 tests).
    `uv run ruff check .` reported no problems, and
    `uv run ruff format --check .` found all 56 files already formatted.
  - **Browser checks (reported by the user):**
    - `customer`, `employee` and `admin` can each open Account.
    - The page has no action buttons.
    - Signing out hides the link.
    - Opening `/accounts/security/` while signed out redirects to sign-in,
      then back to the Security Center after signing in.
  - **Not done:** no commit, seed run or Phase 2 work.
- **Deviations:** None. No follow-up questions were asked.
  - The superuser fixture is local to `accounts/tests.py` rather than in
    `conftest.py`, since only these tests use it so far.
  - The main demo accounts checked in the browser (`customer`, `employee`,
    `admin`) have emails and usable passwords, so none of them shows the
    missing-email reminder or the contact-support message. The background
    seeded customers do have unusable passwords, but they can't sign in, so
    the contact-support state was verified through automated tests, not the
    browser. The missing-email reminder was also verified only through
    automated tests. The demo user that shows it (`newcustomer`) arrives in
    Phase 9.
- **Sideways:** Nothing went wrong this session.

---

## 2026-10-11 — PRD rename, lesson navbar job title, and starting-point commit

### Prompts

1. "Before we start Phase 1, rename prd/account-security-center.md to
   prd/account-security.md and update references to it in the current plan.
   Keep the old quoted prompts in PROMPTS.md unchanged since those record
   what I actually typed. Check git status and review the current changes.
   These should be our planning files, skills, session logs, and the navbar
   job-title change from the lesson. Don't implement any Account Security
   phases or run seed. Tell me what's ready to commit so we can save and push
   this starting point before Phase 1."
2. "Let's add the lesson's job-title change first. In templates/base.html,
   right below the "Hi, {{ user.username }}" span, add: {% if user.job_title
   %} <span class="text-sm opacity-70">{{ user.job_title }}</span> {% endif
   %} Just make that change, don't start Phase 1 yet."
3. "The browser checks worked. Add a short session log to PROMPTS.md for the
   PRD rename and job-title change, including the passing accounts tests and
   my browser checks. Then commit all six files plus the updated log with
   the message "Add Account Security Center planning and lesson navbar
   update" and push to origin/main. Run git status afterward so we can
   confirm the working tree is clean. Don't start Phase 1 yet."

### Summary

- **Outcome:**
  - **PRD rename:** `prd/account-security-center.md` is now
    `prd/account-security.md`, with its content unchanged. Both references
    in `plans/account-security.md` were updated. The old name stays in
    `PROMPTS.md`, in quoted prompts and an older summary, by design.
  - **Navbar job title:** `templates/base.html` shows `user.job_title`
    right after the "Hi, username" greeting, only when it is set. The
    change is three lines, applied exactly as given.
  - **Checks:** `uv run pytest accounts` passed (9 tests). The user
    reported that their browser checks of the navbar worked.
  - **Commit:** the six files plus this log entry are committed together
    and pushed to `origin/main`:
    - `templates/base.html`
    - `PROMPTS.md`
    - `prd/account-security.md`
    - `plans/account-security.md`
    - `.claude/skills/prd-to-plan/SKILL.md`
    - `.claude/skills/to-prd/SKILL.md`
  - **Not done:** no Account Security phase was implemented, no migration
    or seed was run.
- **Deviations:** None. The user chose to add the navbar change before
  committing, and to commit it together with the planning files rather than
  separately.
- **Sideways:**
  - The user expected the lesson's navbar job-title change to be among the
    uncommitted changes. It wasn't: not in the working tree, a stash, any
    branch, or any commit. I reported that instead of guessing, and the
    user supplied the exact snippet.
  - No test covers the job-title display yet; only the existing accounts
    tests were run.

---

## 2026-10-11 — Account Security Center: approved tracer-bullet plan (no build)

### Prompts

1. `/prd-to-plan @prd/account-security-center.md` "Start fresh from the PRD
   and current codebase. Propose the phases for my review before writing the
   plan. The final approved plan should be saved as
   plans/account-security.md. Do not implement anything or run seed."
2. "Keep nine phases and keep signup after pending-request management.
   Please adjust these points:
   1. Put forgotten-password reset before password change, so the
      password-change notice links to a working reset page.
   2. Phase 1 must be a usable read-only overview. Don't show Add/Change
      email buttons until their forms work.
   3. In the first email-confirmation phase, ensure only the newest request
      can be confirmed and a successfully used link cannot be reused.
      Resend, Cancel, and the pending-status display can arrive in the next
      phase.
   4. Include admin handling when the pending-email fields and uniqueness
      constraint arrive: confirmed-email edits must clear pending requests,
      and duplicates must produce form errors. Don't leave an admin path
      that can overwrite these rules until the final phase.
   5. My seed restriction applies to the current development database.
      Verify seed changes in an isolated throwaway database without touching
      my current database or adding seed calls to the normal test suite.

   Show me the revised breakdown before writing the plan. Don't implement
   anything yet."
3. "Yeah this breakdown looks good. Go ahead and save it to
   plans/account-security.md. Make sure each phase says how we'll check that
   it works, and include the rate limits and cooldowns we agreed on. Keep
   the seed check separate from my current database and media folder. Just
   write the plan for now, don't start building anything or run migrations
   or seed yet."
4. "I clicked yes on an edit approval but forgot to check which file it was.
   Can you check git status and the diffs and tell me what changed during
   this session? Don't change or undo anything. I know there were already
   uncommitted changes, so keep those separate from what you just did."
5. "The plan looks good. Just add updating the old "no email at signup"
   wording in plans/core-platform.md to the docs phase, with a reference to
   the new PRD. Also include a final full test suite and Ruff check. Don't
   start implementing yet."
6. "Add this session to the top of PROMPTS.md under today's date, keeping
   the older entries. Record all my prompts in order, including the changes
   I requested and the edit-approval check. Summarize how the tracer-bullet
   plan differs from the naive draft, what we changed before approving it,
   and that we haven't implemented anything or run migrations or seed."

### Summary

- **Outcome:**
  - **Approved plan:** written to `plans/account-security.md` using the
    `prd-to-plan` skill, starting fresh from the PRD and a reread of the
    codebase. It covers the `accounts` app, settings, URLs, the seed command,
    `conftest.py`, `docs/TESTING.md`, and `plans/core-platform.md`. The
    header records the durable decisions:
    - `accounts` owns everything, with no new models
    - `User.email` is the confirmed address, plus pending-email fields
    - a conditional case-insensitive uniqueness constraint
    - the URL table
    - 24-hour confirmation links and 1-hour reset links
    - email settings via environs
    - the agreed rate limits: sign-in 5 failures in 15 minutes then a
      15-minute cooldown; reset requests 3 per lowercased email per hour,
      refused silently; confirmation emails 3 per account per hour. The two
      email limits use 60-minute windows from the first request; sign-in
      uses a 15-minute window and a 15-minute cooldown. No limit ever locks
      an account permanently.
  - **Its nine phases**, each with stories, what to build, acceptance
    criteria, and "How we'll check it" (automated plus manual):
    1. read-only overview and Account nav link, no action buttons
    2. add/change email and confirmation, with admin protection
    3. managing a pending request (status, Resend, Cancel)
    4. email at signup
    5. confirmation-email rate limit (introduces the throttle helper)
    6. forgotten-password reset
    7. password change and its notice
    8. sign-in and reset-request rate limits
    9. seed, admin passwords, and docs, ending with a full `pytest`,
       `ruff check .`, and `ruff format --check .`
  - **How it differs from the naive draft** (the draft is described in the
    entry below; `plans/account-security-draft.md` was no longer in the
    working tree this session, so this comparison relies on that entry):
    - The draft started with a horizontal foundation phase (settings,
      fields, constraint, migration, admin) that couldn't be demoed. Its
      read-only overview phase came second and could be demoed. In the
      approved plan every phase is a vertical slice, from model to view to
      template to tests, that can be demoed and checked on its own.
    - The migration, constraint, and admin handling arrive together with
      the first feature that needs them (Phase 2), not as a standalone
      phase.
    - The draft put all rate limits in one late phase. The approved plan
      introduces the helper with the first limit that uses it (Phase 5)
      and adds the sign-in and reset limits later (Phase 8).
    - Reset comes before password change, so the change notice's reset
      link works when it ships.
    - The draft's seed check already used a throwaway database. The
      approved plan also points the media folder at a throwaway directory
      and checks that `db.sqlite3` and `media/` are unchanged afterwards.
  - **Edit-approval check (prompt 4):** read-only `git status` and diffs.
    The only file this session had written at that point was
    `plans/account-security.md`. `PROMPTS.md`, the PRD, and both skill
    files were uncommitted changes from before the session. `db.sqlite3`
    was last modified 2026-10-04.
  - **Files changed this session:** `plans/account-security.md` (new) and
    this entry in `PROMPTS.md`. **Nothing was implemented, no migration or
    seed was run, and nothing was committed.**
- **Deviations:**
  - The user kept my nine phases and kept signup after pending-request
    management, as I recommended.
  - The user overrode my first proposal on five points (prompt 2). That
    proposal had password change before reset; Add/Change and Change
    password buttons in Phase 1; newest-only and single-use links not
    stated in the first email phase; admin handling deferred to the final
    phase; and seed changes checked by code review only.
  - After approval, the user added the `plans/core-platform.md` wording
    update and the final full test and Ruff check to Phase 9 (prompt 5).
    The core PRD's story 6 and the `SignupForm` docstring stay in Phase 4.
  - Questions I asked: phase granularity and possible merges, signup
    order, and how to verify the seed without running it.
- **Sideways:**
  - My first proposal had three gaps the user caught before approval:
    - the password-change notice would have linked to a reset page that
      didn't exist yet
    - Phase 1 would have shown buttons with no working forms
    - for seven phases, the admin could have bypassed the email rules
  - While planning the isolated seed check, I found that
    `products/signals.py` deletes image files when products are deleted.
    Redirecting only the database could still have removed files from the
    real `media/` folder, so the plan redirects `MEDIA_ROOT` too and
    compares `db.sqlite3` and `media/` before and after.
  - The user approved an edit without checking which file it was. The
    read-only check confirmed it was `plans/account-security.md`, and
    nothing else was touched.

---

## 2026-10-11 — Account Security Center: draft plan and /prd-to-plan breakdown (no build)

### Prompts

1. "clear" — I explained that `/clear` is a built-in CLI command the user
   types themselves and listed what was already saved to files. No files
   touched.
2. "@prd/account-security-center.md Turn this PRD into a multi-phase
   implementation plan and save it to plans/account-security-draft.md.
   Decide how to divide and sequence the work. For each phase, explain what
   it builds, how it can be tested or checked independently, and what should
   work when it is finished. Only create the draft plan. Do not implement
   anything or run seed."
3. "clear" — same answer as before. I noted that the planning step wasn't
   logged yet and that the newly opened `prd-to-plan` skill would write its
   own plan into `plans/`.
4. `/prd-to-plan @prd/account-security-center.md`
5. "Before I clear, append a planning-session entry under today's date at
   the top of PROMPTS.md, preserving existing entries. Record my prompts in
   order, the naive plan outcome, and that I invoked /prd-to-plan before
   clearing or moving the draft. Its proposed breakdown has not been
   approved and no final plan has been written."

### Summary

- **Outcome:**
  - **Naive draft plan:** written to `plans/account-security-draft.md`
    without a planning skill. I read `plans/core-platform.md` and copied its
    shape (Goal / Tasks / Verification / Out of bounds), plus a "When
    finished" line for each phase. Before writing, I read `docs/TESTING.md`,
    the accounts admin, mixins, and tests, `conftest.py`, the URLs, the
    README, `.gitignore`, and `pyproject.toml`.
  - **Its eight phases:**
    1. foundation: settings, user fields, constraint, migration, admin
    2. read-only overview
    3. add/change/confirm an email
    4. email at signup
    5. change password
    6. reset
    7. rate limits
    8. seed and docs
  - **What else the draft records:**
    - ground rules: never run seed; Git tracks `db.sqlite3`, so
      `migrate` shows the database as modified; no new dependencies; no
      agent commits
    - four open points: case-sensitivity of the sign-in throttle key,
      re-requesting your own confirmed address, re-requesting your own
      pending address, and `/accounts/security/` versus the interview's
      `/account/security/`
  - **`/prd-to-plan`:** invoked before clearing and before moving or
    replacing the draft. Following the skill, I proposed a nine-phase
    vertical-slice breakdown:
    1. overview plus change password as the tracer bullet
    2. reset
    3. add/change confirmed by link
    4. managing a pending request
    5. admin override
    6. email at signup
    7. sign-in throttling
    8. reset and confirmation-email throttling
    9. seed and docs

    It also lists the durable decisions for the plan header, and I asked
    four questions: granularity, merging or splitting phases, URLs, and
    whether to keep or replace the draft.
  - **Where it stands:** the user has **not** approved the breakdown, and
    **no final plan has been written**. The draft is unchanged. Nothing was
    implemented, no migration or seed was run, and nothing was committed.
- **Deviations:** None. The user gave no answers that could override a
  recommendation. The draft's four open points and the `/prd-to-plan`
  questions are all still unanswered.
- **Sideways:** No failures. Two things are worth flagging:
  (1) The naive draft's first two phases are horizontal: model only, then a
  read-only page. Neither is a demoable slice. `/prd-to-plan` exposed this,
  and its breakdown starts instead with a tracer bullet that needs no
  migration.
  (2) The first version of the draft had an awkward line, "sending is
  unlimited for one more phase-set". I reworded it to "until Phase 7"
  right away.

---

## 2026-10-11 — Account Security Center: grill-me design and PRD (no build)

### Prompts

1. `/grill-me` "I want to design an Account Security Center for ThoughtTronix.
   Customers need to provide an email address when signing up, change their
   password, and reset a forgotten password through email. Help me decide how
   these features should behave from the customer's perspective. You can
   recommend one or two other useful account security features, and we can
   discuss whether to include them. Interview me until we have a shared
   understanding of the feature. Do not write a PRD, implementation plan, or
   other documentation yet—we will use /to-prd afterward."
2. (Q1, sign-in identifier) "Let's use A. Keep username-based sign-in and
   require an email address at signup for account recovery."
3. (Q2, email uniqueness) "Let's use C. Each email address should belong to
   only one account, regardless of capitalization."
4. (Q3, accounts without email) "Let's use B. Require email for new signups,
   and prompt existing users without an email to add one in the Security
   Center. Keep email uniqueness case-insensitive for non-blank addresses,
   while allowing existing accounts to have a blank email."
5. (Q4, changing email) "Let's use C, and require the current password when
   adding or changing an email. Confirm the new address through an emailed
   link before it takes effect. Keep the existing email active until
   confirmation, then notify the old address after the change succeeds."
6. (Q5, link lifetime and replacement) "Let's use A with a 24-hour expiry. The
   newest request replaces the previous one. Show the pending address in the
   Security Center with resend and cancel options. Resending should issue a
   fresh link and invalidate the previous link. Canceling or successfully
   confirming should also invalidate it. Check case-insensitive email
   uniqueness both when requesting the change and when confirming it."
7. (Q6, sign-in to confirm) "Let's use C. The valid confirmation link is
   enough to confirm the exact pending email address, without requiring
   sign-in. Confirming must never sign anyone in or switch the account
   currently signed in."
8. (Q7, after password change) "Let's use A. Keep the current browser signed
   in, sign out other sessions, and return to the Security Center with a
   success message. Send a password-change notification to the account's
   current email with a link to the password reset page. If no email is set,
   skip the notification."
9. (Q8, reset-page response) "Let's use A. Always show "If an account exists
   for that address, we've sent a reset link." Keep the same message for
   unknown addresses, inactive accounts, and accounts with unusable passwords,
   and send no email for those cases. Also remind customers to check spam and
   double-check the address they entered if no email arrives."
10. (Q9, after reset) "A, with a 1-hour expiration. After resetting, ask the
    customer to sign in with their new password, invalidate existing
    sessions, and send a notification email. Expired or used links should
    show a clear message with an option to request another reset."
11. (Q10, extra features) "Let's add A only: limit repeated failed sign-in
    attempts and repeated password-reset requests. Also limit
    email-confirmation resends to prevent inbox flooding. Keep cooldowns
    temporary, preserve the generic password-reset response, and explain the
    limits clearly during the interview. Leave device sign-out, recent
    sign-in activity, and two-factor authentication out of scope."
12. (Q11, limits and counter storage) "I accept the proposed limits and
    messages, and choose A, Django's cache. Document that counters reset on
    restart and aren't shared between server processes. Apply the
    3-per-hour confirmation limit to all confirmation emails for the
    signed-in account, including initial requests, replacement addresses, and
    resends, so changing the pending address can't bypass it. Treat "per
    hour" as a 60-minute window starting with the first counted request, and
    normalize email capitalization before counting reset requests."
13. (Q12, verifying the signup email) "Let's use B. Require an email at
    signup, but keep it pending until confirmed. Customers can sign in
    immediately; password resets and security notices only use a confirmed
    address. Show a reminder in the Security Center until confirmation.
    Please clarify the pending-address uniqueness rule before we finalize it:
    an unconfirmed signup shouldn't reserve someone else's email indefinitely
    and prevent its owner from registering."
14. (Q13, what counts toward uniqueness) "I agree with A. Only confirmed
    email addresses count toward case-insensitive uniqueness. Pending
    addresses reserve nothing. Recheck uniqueness during confirmation. If
    another account has already confirmed that address, refuse the change,
    clear the conflicting pending request, and direct the customer to add a
    different address in the Security Center. Preserve their existing
    confirmed email, if they have one."
15. (Q14, access and layout) "Let's use A: one Security Center overview with
    separate email and password form pages. I agree that all signed-in users,
    including staff and superusers, can access it, while password reset stays
    public. Add an "Account" link beside Addresses in the signed-in
    navigation. Label the email action "Add email" when none is confirmed and
    "Change email" otherwise. Show pending status with resend and cancel
    options, and return completed actions to the overview with clear
    messages."
16. (Q15, email delivery) "Let's use B with plain-text emails. Read email
    configuration from .env, keeping the console backend as the default so
    the app works without any setup. Document how to test emails through
    terminal output and how to configure SMTP. Include placeholder settings in
    .env.example, and keep real credentials out of Git."
17. (Q16, seed state) "Let's use B. Treat existing seeded emails as confirmed
    and add one demo customer with a usable password and no email. Document
    that account so the missing-email flow is easy to test. Update the seed
    command, but don't run it against my current database—it would erase the
    product and uploaded images we created for the previous homework."
18. (Q17, admin edits, plus correction) "Let's use A. Authorized admins can
    edit the confirmed email directly without confirmation or notices. Keep
    case-insensitive uniqueness enforced and clear any pending email request
    when the confirmed email changes. The other defaults match, except the
    unusable-password case. We agreed that those accounts receive no
    password-reset email, so don't present reset as a way for them to set a
    password. Show that password management is unavailable and direct them to
    support; an authorized admin can set a usable password through the
    existing admin tools. Please confirm that correction. Don't create
    documentation or implement anything yet—I'll invoke /to-prd next."
19. (Correction — resolving my contradictory reply) "I Agree, accounts with
    unusable passwords cannot add or change an email because those actions
    require the current password. Show the contact-support message instead.
    They can still confirm, resend, or cancel an existing pending request
    under the agreed rules. Please describe that clearly in the PRD."
20. `/to-prd`
21. (Correction — PRD) "Please make two corrections to the PRD: 1. In
    Further Notes, say: "Only confirmed addresses receive password-reset
    emails and security notices. Pending addresses receive confirmation
    emails only. Confirmation and reset flows never automatically sign anyone
    in. Customer security changes trigger notices as specified; admin email
    overrides are exempt." 2. In the confirmation-email rate-limit row,
    replace "Signed-in account" with "Account, including the newly created
    account at signup." The initial signup confirmation counts toward the
    same 3-per-hour budget as subsequent requests and resends. Do not
    implement anything yet."
22. "Append a session log to PROMPTS.md at the repo root, under today's date,
    newest entry at the top. ..." (the standard log prompt above)

### Summary

- **Outcome:** A seventeen-question grill-me session settled the Account
  Security Center design. The PRD was written to
  `prd/account-security-center.md`. No application code, migration, or seed
  change was made, and nothing was committed. Settled points:
  - **Identity:** sign-in stays username-based. The email field holds the
    *confirmed* address, and a separate *pending* address waits for
    confirmation. Uniqueness is case-insensitive and covers confirmed,
    non-blank addresses only. Pending addresses reserve nothing, and the
    first account to confirm wins.
  - **Email flows:** signup requires an email, which starts pending, and the
    customer can sign in right away. Adding or changing an email requires the
    current password and a 24-hour confirmation link. There is one pending
    request at a time, and a new request, resend, cancel, or confirmation
    invalidates older links. The link works without sign-in but never signs
    anyone in. The old address is notified after a change.
  - **Password flows:** changing the password uses Django's stock view; other
    sessions are signed out and a notice is sent. Reset always shows the same
    generic message plus a spam hint. Links last 1 hour, there's no
    auto sign-in, and a notice is sent.
  - **Rate limits:** 5 failed sign-ins in 15 minutes per username, 3 reset
    requests per hour per lowercased email (throttled silently), and 3
    confirmation emails per hour per account (signup included). Counters are
    kept in Django's in-memory cache.
  - **Page and operations:** an overview page with separate email and
    password form pages, plus an "Account" nav link. Email settings come from
    `.env` and default to the console backend; all emails are plain text.
    Seed gets a no-email demo customer `newcustomer`. Admins can edit emails
    directly. Accounts with unusable passwords are directed to support.

  To ground the questions, I read `accounts/`, `settings.py`, the seed users,
  `base.html`, `.env.example`, and `.gitignore`. Before Q17 I ran a read-only
  `manage.py shell` query against the dev database. It showed 12 users, no
  blank emails, and no case-insensitive duplicates, so the uniqueness
  constraint will migrate cleanly. Seed was not run.
- **Deviations:** The user overrode one recommendation. On Q4 they chose C
  (confirm the new address by emailed link) over my B (change immediately
  after a password check, then notify the old address). That choice led to
  Q5, Q6, Q12, and Q13. Every other answer took my recommendation and added
  specifics:
  - the spam/double-check hint on the reset page (Q8)
  - clear expired-link messages (Q9)
  - a third limit on confirmation emails (Q10)
  - one budget covering every confirmation email, a 60-minute window from
    the first request, and lowercasing before counting resets (Q11)
  - documenting the cache limitation, SMTP setup, and the demo account
    (Q11, Q15, Q16)
  - the "Add email"/"Change email" labels (Q14)
  - clearing pending requests on admin edits (Q17)

  Follow-up question: on Q12 the user asked me to clarify how uniqueness
  applies to pending addresses before finalizing, which became Q13.
- **Sideways:** Four of my statements were wrong or overstated. The user
  caught all four:
  (1) My Q12 recommendation said the signup uniqueness check should apply
  to *pending* addresses too. That would let an unconfirmed signup block an
  address's real owner indefinitely. The user flagged it, and Q13 changed
  the rule so pending addresses reserve nothing.
  (2) In the defaults listed with Q17, I said accounts with unusable
  passwords would use reset to set a password. That contradicts Q8, where
  those accounts never get a reset email. The user corrected it to "contact
  support; an admin sets a password."
  (3) My reply confirming that correction contradicted itself. One bullet
  said email management "still works normally" for those accounts, and the
  next said adding or changing an email is blocked. The user settled it:
  add/change is blocked, while confirm/resend/cancel of an existing pending
  request is allowed.
  (4) The PRD's summary rule said "only confirmed addresses receive mail,"
  which ignores confirmation emails sent to pending addresses, and it didn't
  exempt admin overrides from notices. Its rate-limit row also said
  "Signed-in account," which doesn't fit the confirmation sent at signup.
  The user supplied replacement wording for both, and I applied it verbatim.

---

## 2026-10-04 — Product images: build from handoff, browser check, ThinkVision

### Prompts

1. "@HANDOFF.md Implement this feature. Delete HANDOFF.md after reading it,
   and don't commit anything yet."
2. "Give me a step-by-step browser checklist to verify the product image
   feature, including uploading, replacing, clearing, invalid uploads, and
   placeholder fallback. Use my existing products and don't run seed or
   commit anything."
3. "Append a session log to PROMPTS.md at the repo root, under today's date,
   newest entry at the top. ..." (the standard log prompt above), followed by:
   "Add the second session's log without duplicating the first. Include the
   product-image work, browser verification, feature commit and push, and
   ThinkVision being added through the back office. I generated
   ThinkVision's image using ChatGPT image generation. Ask me for any details
   you cannot verify."
4. (Answering my questions about what I couldn't verify) "I did the commits
   myself. I ran through all the steps you gave me and everything worked
   well. I uploaded the images by hand to each matching product and all of
   them behaved normally. I created thinkvision by myself besides the AI
   generated photo and everything for the product worked just fine."

### Summary

- **Outcome:** The handoff design was built as specified, and `HANDOFF.md`
  was deleted after reading.
  - **Model and storage:** `Product.image` (migration
    `0004_product_image`), Pillow 12.3, `MEDIA_ROOT`/`MEDIA_URL` (media
    served only in `DEBUG`), `media/` gitignored, and a README note that
    production must serve `MEDIA_URL` itself.
  - **Validation and processing:** `ProductImageField` in
    `products/forms.py` checks bytes, then the header, then decodes. It
    overrides `to_python` so nothing fully decodes before the limits pass.
  - **Display:** `Product.image_url` returns the uploaded image or the
    category placeholder, shown in a 4:5 `object-contain` frame on the
    catalog, category, detail, back-office form and list.
  - **File lifecycle:** deletion runs from `Product.save()` and a
    `post_delete` signal (`products/signals.py`). It waits for
    `on_commit` and skips files another product still uses.
  - **Back office and admin:** a multipart form with preview, help text,
    the "Remove image and use the category placeholder" checkbox and a
    re-select note. The admin shows a read-only preview.
  - **Tests and measurement:** 69 new tests in `products/test_images.py`;
    full suite 335 passed; `ruff check` and `ruff format --check` clean.
    Run through the real field, the 13 provided images averaged 1,965 KB →
    90 KB, so a 12-card page went from 23.0 MB to 1.06 MB.
  - **Checklist:** for prompt 2, I generated 10 invalid and edge-case test
    files in the scratchpad (outside the repo) and wrote a 13-section
    checklist.

  After the session, the user carried out the rest by hand:
  - **Browser check:** ran every checklist step; all passed.
  - **Provided images:** uploaded each one to its matching product through
    the back office; all behaved normally.
  - **Commit and push:** made and pushed the feature commit `f4c4011`
    ("Add product image uploads and catalog display"), which also carried
    the first 2026-10-04 log entry.
  - **ThinkVision:** created by hand in the back office (pk 70, Accessories,
    $349.99) and uploaded an image generated with ChatGPT. It was processed
    to a 22 KB WebP and worked normally. The ChatGPT prompt wasn't recorded.

  At logging time, 13 of 35 products had images and `media/products/` held
  exactly 13 files.
- **Deviations:** No recommendation was overridden; the user accepted the
  build as delivered. Where the spec left room, I made these calls and
  flagged them:
  - **Animated GIFs:** they get the format message, because the spec's
    order checks format before animation.
  - **Extremely large images:** above Pillow's ~179 MP limit the message
    says "over 178 megapixels", since Pillow refuses before reporting a size.
  - **Damaged files:** a file with a JPEG/PNG/WebP signature that won't open
    gets "couldn't be read" rather than the format message.
  - **MPO JPEGs:** treated as stills, not as animated.
  - **Colour profiles:** only RGB ICC profiles are kept.
  - **Form rendering:** `FORM_RENDERER = TemplatesSetting` and
    `django.forms` in `INSTALLED_APPS`, so the restyled widget template
    lives in `templates/products/widgets/`.

  Follow-ups: the browser checklist, and this log, for which the user asked
  me to include the work they did outside the session. I asked about
  anything I couldn't verify from git or the database rather than guessing.
- **Sideways:** Nothing broke the build; these small slips were each caught
  immediately:
  (1) Ruff's DJ012 flagged `save()` placed after `get_absolute_url()`; I
  moved it.
  (2) The size-measurement script first failed with `No module named
  'config'`. Piping it into `manage.py shell` then broke on the multi-line
  loop. Running it with `PYTHONPATH=.` worked.
  (3) `tailwind build` reported the stylesheet "up to date" and skipped the
  new classes until rerun with `--force`.
  (4) My first check for the `aspect-[4/5]` class used a mis-escaped
  pattern and falsely reported it missing. Reading the compiled CSS showed
  it was there.
  I didn't run the dev server during the build, to avoid uploading into the
  user's database; the user's browser pass covered that.

---

## 2026-10-04 — Product images: grill-me design and handoff (no build)

### Prompts

1. `/grill-me` "ThoughtTronix needs real product images. The provided images
   are in product-images/ at the repository root. Employees should upload
   images through the back-office product forms. Every product must show its
   uploaded image when available or the existing category placeholder,
   including when an uploaded file is missing. Unusable uploads must be
   rejected before saving with a clear explanation. Images should look
   consistent across the catalog and detail pages, and pages should stay
   fast. Help me decide the design before implementing anything."
2. (Q1, how many images) "A. Use one optional image field on Product. Each
   product has one uploaded image, and products without a usable image show
   the existing category placeholder. We don't need galleries for this
   feature."
3. (Q2, processing) "B. Resize and re-encode images once during upload, and
   store only the processed image. Preserve the aspect ratio and avoid
   enlarging smaller images. If the file cannot be validated or processed,
   reject it with a plain-language error before saving the product or image."
4. (Q3, stored sizes) "A. Store one processed image with its longest edge
   capped at 1200px, preserving the aspect ratio and never enlarging smaller
   images. Use it on both catalog and detail pages, with lazy loading on
   catalog images. Check the actual processed file sizes using the provided
   images to confirm the reduction."
5. (Q4, output format) "A. Save processed images as WebP at quality 80 and
   preserve transparency when present. For animated uploads, I'd prefer
   rejecting them with a clear explanation rather than silently saving only
   the first frame. We can settle accepted input formats in the next
   question."
6. (Q5, input formats) "A. Accept JPEG, PNG, and WebP, checking the actual
   file contents rather than trusting the filename extension. Reject other
   formats with "Upload a JPEG, PNG, or WebP image." Reject animated images
   with "Animated images aren't supported. Upload a still image.""
7. (Q6, size limits) "A. Allow files up to 10 MB, up to 50 megapixels, and at
   least 600 pixels on each side. Check file size first and pixel dimensions
   before fully decoding or processing the image. Show plain-language errors
   explaining the limit and the uploaded image's size. Make the messages
   match the inclusive limits: "10 MB or smaller" and "50 megapixels or
   fewer.""
8. (Q7, framing) "B. Use a fixed 4:5 frame with object-contain on both catalog
   and detail pages, without cropping. Reserve the frame space before images
   load to prevent layout shifts. Use a theme-compatible semantic background
   class for the frame, and apply the same framing to category placeholders."
9. (Q8, missing-file fallback) "A. Add one Product method or property that
   returns the uploaded image URL only when the field is set and the file
   exists in Django storage. Otherwise, return the static URL for the
   existing Category.placeholder_image. Both catalog and detail templates
   should use it. Test all three cases: no image, an existing image, and a
   missing uploaded file."
10. (Q9, old files) "B sounds good. Delete the old image only after the
    database change successfully commits when an image is replaced, cleared,
    or its product is deleted. Keep the Clear checkbox so employees can switch
    back to the placeholder, and make sure another product isn't using the
    file before deleting it. Include tests for replacing, clearing, deleting,
    and rolling back a change. Also, describe this as reducing unused files
    rather than guaranteeing the media folder always matches the database
    exactly."
11. (Q10, file naming) "B sounds good. Give each uploaded image a new UUID
    filename ending in .webp and store it under products/ in the media
    folder. That way, replacing an image gives it a new URL, avoids filename
    conflicts, and keeps the old and new files separate until the old one can
    be deleted after the save commits."
12. (Q11, media location and serving) "A sounds good. Let's put the media
    folder at the project root, allow the location to be changed through
    .env, and only have Django serve uploads when DEBUG=True. Keep uploads
    separate from assets/ and ignored by Git. Also, if the files exist but the
    media URL isn't working, the fallback won't catch that, so just note that
    production needs its own way to serve images instead of saying it will
    automatically show placeholders."
13. (Q12, seed) "I'd go with B. Let's keep seed unchanged and upload the
    provided images through the back office. Keep product-images/ as a
    temporary folder that isn't committed, and don't have seed clear out
    media/products/. I understand that seeding removes the image links and
    I'd need to upload them again, so don't run seed against my current
    database during the build."
14. (Q13, back-office UX) "C sounds good. Show the current image or
    placeholder on the edit form, add a small thumbnail to the products list,
    and put the upload requirements beside the file picker. Include the
    50-megapixel limit and mention that animated images aren't supported too.
    Keep the Clear checkbox labeled "Remove image and use the category
    placeholder." If a form fails after I've selected an image, show a note
    telling me to choose it again. We don't need temporary storage for failed
    uploads."
15. (Q14, orientation and metadata) "A sounds good. Apply the photo's
    orientation before resizing so it doesn't end up sideways, then remove the
    location, camera, and other metadata while keeping the color profile. Add
    tests to make sure rotated photos come out upright and the saved image no
    longer contains EXIF data."
16. (Q15, code location and admin) "A sounds good. Keep the upload checks and
    image processing together in a custom ProductImageField in
    products/forms.py, and have ProductForm use it. Make the image read-only
    in Django admin with a preview, so uploads go through the back office and
    follow the same rules. Just make sure the file-size and dimension checks
    happen before anything fully decodes the image, including Django's
    built-in validation."
17. (Q16, delete wiring) "A sounds good. Use a post_delete signal for product
    deletions and handle replaced or cleared images in the model's save path,
    with cleanup happening only after the database change commits. I'm okay
    with seed deleting the images attached to the products it removes, as
    long as seed.py stays unchanged and it doesn't clear the whole media
    folder. Check whether another product still uses the file before deleting
    it, and don't run seed against my current database during the build."
18. (Q17, which pages) "A sounds good. Show images on the catalog and category
    pages, the product detail page, and the back-office form preview and
    products list. Use the same image-or-placeholder logic in all of those
    places, and leave the cart, checkout, and order pages as they are for
    now."
19. "No need to create a separate plan file. The design looks good, but leave
    product-images/ out of commits without adding it to .gitignore, and make
    sure corrupt or unreadable images also get a plain-language error before
    anything is saved. Don't build anything yet; I'll use /handoff to carry
    these decisions into the next session."
20. `/handoff` "the next session implements the design we just agreed"
21. "Read the standard session-log prompt in the PROMPTS.md header and follow
    it to record this interview session."

### Summary

- **Outcome:** A seventeen-question grill-me session settled the
  product-image design. No application code was written. Settled points:
  - **Model and storage:** one optional `Product.image`. Pillow processes
    each upload once: rotate upright from EXIF, cap the longest edge at
    1200px without enlarging, strip EXIF but keep the ICC profile, and save
    as WebP q80 named `products/<uuid>.webp`.
  - **Validation:** all checks and processing live in a `ProductImageField`
    in `products/forms.py`. It accepts JPEG, PNG and WebP only and rejects
    animated images. Limits are 10 MB, 50 MP and at least 600px per side.
    Checks run cheapest first, before any full decode.
  - **Display:** a `Product` property returns the upload URL only if the
    file exists, otherwise the category placeholder. Every surface uses a
    fixed 4:5 `object-contain` frame.
  - **File cleanup:** deletion waits for `on_commit`, runs from the save
    path and a `post_delete` signal, and skips files another product still
    uses.
  - **Back office and admin:** a back-office preview, help text and list
    thumbnails. Admin shows the image read-only.
  - **Media serving:** `media/` is gitignored and served only in `DEBUG`.

  To answer Q3, I measured the 13 provided images in a throwaway `uv`
  environment. The originals averaged 1,965 KB, about 23 MB for a 12-card
  page. As WebP q80 they averaged 95 KB, about 1.1 MB per page. I also
  built a contact sheet in the scratchpad to inform the framing question.
  The decisions were written to `HANDOFF.md`, which is untracked and not
  committed.
- **Deviations:** The user overrode one recommendation. On Q12 they chose B
  (keep `seed` unchanged and upload by hand) over my A (commit
  `product-images/` and have seed attach images, clearing `media/products/`).
  On Q16 I left the choice to the user because A changes `seed`'s file
  behavior; they took A on the condition that `seed.py` stays unchanged.
  Every other answer took my recommendation and added specifics:
  - rejecting animated uploads instead of keeping the first frame
  - inclusive wording ("10 MB or smaller", "50 megapixels or fewer")
  - the exact error messages and the Clear label
  - a semantic frame background
  - the shared-file check before deletion
  - a rollback test
  - the 50 MP and animation rules in the help text

  The final follow-ups declined a plan file and declined adding
  `product-images/` to `.gitignore` (leave it out of commits instead). They
  also added a plain-language error for corrupt or unreadable images.
- **Sideways:** Several of my statements were too strong or incomplete, and
  most were caught by the user:
  (1) Q9 said cleanup keeps `media/` "always" matching the database. The
  user had it reworded as "reducing unused files."
  (2) Q11 said a broken production media setup would fall back to
  placeholders. The user pointed out that the fallback checks file
  existence, not URL reachability, so it would not.
  (3) Q12 claimed `seed` would skip the cleanup hooks. After reading
  `seed.py:555` (a queryset delete), I corrected this myself in Q15/Q16,
  because it depends on whether a signal or a `delete()` override is used.
  (4) The Q6 sample messages said "under 10 MB", which contradicts the
  inclusive limit. The user fixed the wording.
  (5) The user flagged that Django's built-in `ImageField.to_python` decodes
  before custom checks. The design now overrides `to_python` so size and
  dimension checks come first.
  (6) The design summary had no error for corrupt or unreadable files until
  the user asked for one. Two messages were added: unrecognized files get the
  format message, and recognized but damaged files get a "couldn't be read"
  message.

---

## 2026-09-25 — Discount codes: grill-me design, build, and Remove code control

### Prompts

1. `/grill-me` "ThoughtTronix needs discount codes that customers can enter at
   checkout and see reflected in the order total. Marketing must be able to
   create, expire, and retire codes. An expired code should show a clear
   message at checkout. Retiring a code must not change orders already placed
   with it. Support both discounts on the whole order and discounts limited to
   specific products."
2. (Q1, expire vs. retire) "A. Give codes an optional expiration date and a
   separate active/retired flag. Expired and retired codes should both be
   rejected at checkout with clear messages. Keep past orders' discount
   amounts unchanged."
3. (Q2, what an order records) "A. Store the applied code text and final
   discount amount on each order, plus an optional link to the DiscountCode.
   Past order totals and discount amounts must come from those saved values,
   never be recalculated from the current code."
4. (Q3, meaning of `Order.total`) "A. Keep Order.total as the final amount
   paid, and add subtotal for the pre-discount amount. Existing orders should
   migrate with subtotal = total and no discount. Show the subtotal, discount,
   and final total on order pages."
5. (Q4, discount kinds) "B. Support percentage and fixed-amount codes. Cap a
   fixed discount at the amount it applies to, and round money to cents. Leave
   minimum-spend rules out for now."
6. (Q5, product scope) "A. Give each code an explicit whole-order or
   specific-products scope. For a product-specific code, require at least one
   selected product and calculate the discount only from eligible cart items.
   If none are in the cart, show "This code doesn't apply to anything in your
   cart.""
7. (Q6, checkout interaction) "A. Add an Apply button and HTMX order-summary
   preview on checkout. Show the subtotal, discount, and final total or a
   clear error. Revalidate and recalculate the code in place_order when the
   customer submits; if it is no longer valid, keep them on checkout with
   their form data and show the reason."
8. (Q7, matching and uniqueness) "A. Trim spaces and match codes without
   regard to case. Store them uppercase, allow letters, digits, and hyphens,
   and keep each code unique even after retirement. "We don't recognize that
   code" works for a code that doesn't exist."
9. (Q8, editing and deleting) "A. After the first order uses a code, lock its
   discount kind, value, scope, and eligible products. Allow changes to its
   expiration date and active status. Permit deletion only before it has been
   used; used codes should be retired instead. Past orders must retain their
   saved discount and total regardless."
10. (Q9, other limits) "A. No start date or usage limits for now. A valid code
    can be used by any customer on multiple orders until it expires or
    Marketing retires it. Keep one code per order."
11. (Q10, expiry precision) "A. Use an optional expires_on date and treat the
    code as valid through that entire date in America/Chicago. Make the store
    time zone configurable with that default. The expired message should name
    the date. This replaces the earlier expires_at idea; the separate retire
    flag stays."
12. (Q11, message precedence) "A. Check unknown code, then retired, then
    expired, then whether it applies to the cart. Show one clear message, and
    use the same validation and wording for the Apply preview and final
    checkout."
13. (Q12, back-office screens) "A. Add a Discount codes tab with a list,
    create/edit form, POST-only Retire/Reactivate controls, and confirmation
    before deleting an unused code. Show status and usage count on the list.
    Also show the saved discount on the back-office order detail page."
14. "The decisions and defaults look good. Skip the PRD and plan for this
    homework. Implement this feature, including tests for expired and retired
    codes, product-specific discounts, saved order amounts, and
    customer-facing errors. Run the full test suite and Ruff. Stop before
    committing so I can review it in the browser first."
15. (Correction — rejected my seed edit) "The proposed seed edit contains an
    incomplete DISCOUNT_CODES entry. Please rewrite it as a complete file
    edit, show me the full diff, and verify the seed command parses and runs
    before continuing."
16. (Correction — rejected the rewritten seed edits) "I noticed
    Order.objects.create() has two total= keyword arguments in _build_order.
    Fix that duplicate, then show the complete seed.py diff and check that the
    demo coupon creation method is called."
17. "Go ahead with the two seed-code edits we agreed on, then show me the full
    diff and check that seed.py compiles. Please don't run manage.py seed
    against my current development database, since it wipes the demo data.
    Verify the new seed behavior in an isolated test database as part of the
    tests instead. Then continue building the coupon feature."
18. "How do I verify this feature manually in the browser? Give me the exact
    pages, accounts, codes to create, and expected results without running
    seed."
19. "Let's improve the checkout coupon controls: add a clear Remove code
    action after a coupon has been applied. After reviewing checkout, I want customers to be able to
    remove an applied discount code. Add a clearly visible "Remove code"
    action next to the applied code. Clicking it should restore the
    undiscounted subtotal and Place order amount, clear the code that would be
    submitted with the order, and let the customer apply another code. Keep
    their address and other checkout entries intact. Add a test for removing a
    code, run the tests and Ruff, and stop before committing so I can verify
    it in the browser."
20. "Append a session log to PROMPTS.md at the repo root, under today's date,
    newest entry at the top. ..." (the standard log prompt above)

### Summary

- **Outcome:** A twelve-question grill-me session settled the design, then
  the feature was built. `DiscountCode` (in `orders/models.py`) has percent or
  fixed `kind`, `value`, whole-order or specific-products `scope`, a
  `products` M2M, an optional inclusive `expires_on`, and an `is_active`
  retire flag. Codes are stored uppercase and unique forever. One
  `DiscountCode.objects.quote()` path serves both the HTMX checkout preview
  (`CheckoutSummaryView`, `_order_summary.html`) and `place_order`, which
  re-validates inside its transaction and snapshots `subtotal`,
  `discount_amount`, `total`, `coupon_code` text and a `SET_NULL`
  `discount_code` link onto the order. Migration `0004_discount_codes`
  backfills `subtotal = total`. Order pages show Subtotal / Discount / Total
  from saved values (`_order_totals.html`). The back office gained a Discount
  codes tab (list with status and usage count, create/edit form that locks a
  used code's terms, POST-only Retire/Reactivate, delete only for unused
  codes). `TIME_ZONE` now defaults to `America/Chicago` via `.env`. Seed adds
  four demo codes. A final follow-up turned the small "Remove" link into a
  clearly visible "Remove code" button. Final state: 266 passed; `ruff check`
  and `ruff format --check` clean; nothing committed by the agent.
- **Deviations:** The user chose my recommended option on all twelve design
  questions, each time adding specifics of their own (e.g. the exact
  not-applicable message, POST-only retire controls). Q10 renamed the
  expiry field from `expires_at` (Q1) to `expires_on`. Follow-ups: skip
  the PRD and plan; don't run `seed` against the dev database; a manual
  browser test script; the Remove code control. I added a few defaults
  without asking, and flagged each one: locking the code text itself on a
  used code (beyond the four fields the user listed), showing the Discount
  row only when there is a discount, round-half-up, and the full month name
  in the expired message.
- **Sideways:**
  (1) `makemigrations` couldn't add non-null `subtotal` non-interactively.
  I generated the migration with `subtotal` briefly nullable, then
  hand-added a `RunPython` backfill and an `AlterField` back to non-null.
  (2) I first wrote the seed changes as one long inline Python script. The
  user rejected it, reading one `DISCOUNT_CODES` entry as incomplete; a
  single-line script was hard to review. My follow-up `Edit` calls were
  rejected too. The user then reported a duplicate `total=` in
  `_build_order`. I checked instead of editing: there was only
  `subtotal=total` and `total=total` (a search for `total=` matches both),
  and the file compiled. I reported that the demo-code method didn't exist
  yet because every edit adding it had been rejected. It was then applied as
  two reviewed edits with the full diff shown.
  (3) The user asked to verify seed "as part of the tests," which conflicts
  with CLAUDE.md's "Tests never invoke the seed command." I verified it with
  a one-off pytest file in the scratchpad instead: pytest's throwaway
  database, two seed runs, and the dev DB confirmed untouched. I offered to
  make it permanent; it was not added to the suite.
  (4) Smaller slips caught by the suite or Ruff: a test used
  `reverse("login")` instead of `accounts:login`; the new test file needed
  `ruff format` twice; one assertion was updated when the applied-code
  markup changed.
  (5) Between turns the earlier discount work appeared as committed. That
  was the user, not the agent.

---

## 2026-09-20 — Featured products: model field, migration, and badge

### Prompts

1. `/context` — inspected the session's context usage. No code touched.
2. "clear" — I explained that `/clear` is a built-in CLI command the user
   types themselves; I can't trigger it. No code touched.
3. "Add an is_featured field to the Product model. It should be a
   BooleanField that defaults to False so existing products remain
   unfeatured. Only change the model for now—do not create the migration or
   add the badge yet. Show me exactly what you changed."
4. "Generate and apply the migration for the new Product is_featured field.
   Before running the commands, tell me what commands you plan to use and
   what each one does. After the migration is applied, show me the new
   migration file and confirm it completed successfully."
5. "Add a 'Featured' badge for products whose is_featured value is True. It
   must appear on both the catalog listing and the product detail page, and
   it must not appear for unfeatured products. Follow the existing template
   styling and project patterns. Add or update tests for both pages, then
   run the relevant tests and explain exactly what you changed."
6. "Append a session log to PROMPTS.md at the repo root, under today's date,
   newest entry at the top. ..." (the standard log prompt above)

### Summary

- **Outcome:** `Product.is_featured` (`BooleanField(default=False)`) added in
  `products/models.py`, with migration `products/migrations/0003_product_is_featured.py`
  generated and applied. A `Featured` badge (`badge badge-primary badge-outline`,
  matching the existing outline-badge convention) now renders on the catalog
  card badge row and the detail page status block; the detail wrapper gained
  `flex flex-wrap gap-2` now that it holds more than one badge. Added a
  `featured_product` fixture to `conftest.py` and five tests to
  `products/tests.py` covering both pages positive and negative, plus the
  `default=False` contract. Full suite green: 169 passed. `ruff check` and
  `ruff format --check` clean.
- **Deviations:** none — the work was delivered in three deliberately scoped
  steps (model only, then migration, then template + tests), each specified by
  the user up front. No recommendation was overridden and no clarifying
  questions were needed.
- **Sideways:** nothing broke. Two things worth flagging: (1) after step 3 the
  model and migration history were briefly out of sync by design, so Django
  would have warned about an unapplied change until step 4 — noted at the time;
  (2) the generated migration uses Django's own quoting rather than the repo's
  ruff style, so a `ruff format .` pass was recommended, and the format check
  at the end of step 5 reported all 52 files already formatted. The negative
  badge tests assert the bare string `"Featured"` is absent from the page,
  which is consistent with how existing tests check for `"Unavailable"` but
  would misfire if unrelated copy ever used the word; called out rather than
  silently tightened.
