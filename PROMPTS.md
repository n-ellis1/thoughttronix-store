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
