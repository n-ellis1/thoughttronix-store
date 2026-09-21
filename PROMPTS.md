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
