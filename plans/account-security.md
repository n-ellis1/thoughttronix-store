# Plan: Account Security Center

> Source PRD: `prd/account-security.md`. The PRD owns the requirements; this plan owns the sequence. Where a phase says "per the PRD," the PRD's wording is authoritative.

## Architectural decisions

Durable decisions that apply across all phases:

- **Owning app**: `accounts`, for everything: models, forms, views, the rate-limit helper, email templates. Email-confirmation state changes (request, resend, cancel, confirm) are methods on `User`; forms own validation (current password, uniqueness); views stay thin.
- **Identity**: Sign-in stays username-based. Email is for recovery and security notices only.
- **Models**: No new models. `accounts.User` gains:
  - the existing `email` field as the **confirmed** address (blank = none confirmed);
  - a pending address, a per-request token that makes only the newest link valid, and the time the current link was sent (drives the "link sent" / "link expired" status).
  - A conditional `UniqueConstraint` on `Lower("email")`, applied only when the email is not blank. Pending addresses reserve nothing.
- **Migration**: One migration (Phase 2) adds the pending fields and the constraint. Existing emails become confirmed addresses with no data change.
- **URLs** (all in the `accounts` namespace):

  | Path | Name | Access |
  |---|---|---|
  | `/accounts/security/` | `accounts:security` | signed in |
  | `/accounts/security/email/` | `accounts:email_change` | signed in |
  | `/accounts/security/email/resend/` | `accounts:email_resend` | signed in, POST only |
  | `/accounts/security/email/cancel/` | `accounts:email_cancel` | signed in, POST only |
  | `/accounts/security/email/confirm/<token>/` | `accounts:email_confirm` | public |
  | `/accounts/security/password/` | `accounts:password_change` | signed in |
  | `/accounts/password-reset/` | `accounts:password_reset` | public |
  | `/accounts/password-reset/sent/` | `accounts:password_reset_done` | public |
  | `/accounts/password-reset/<uidb64>/<token>/` | `accounts:password_reset_confirm` | public |

- **Authorization**: Security Center views use `LoginRequiredMixin` and are open to every role (customers, staff, superusers). Confirmation and reset views are public and **never sign anyone in or switch the signed-in account**.
- **Link lifetimes**: Email-confirmation links are signed and expire after **24 hours**. Password-reset links expire after **1 hour** (`PASSWORD_RESET_TIMEOUT = 3600`). Both stop working once used.
- **Email**: Plain-text templates only. Settings are read from `.env` via environs (backend, host, port, username, password, TLS, default sender); the default is the console backend, and the default sender is a ThoughtTronix no-reply address on `example.com`. Confirmation emails go to the pending address; reset links and security notices go to the **confirmed** address only.
- **Rate limits** (agreed values; counters live in Django's default in-process memory cache, no new tables):

  | Action | Counted per | Limit | Cooldown | What the user sees |
  |---|---|---|---|---|
  | Sign-in | Submitted username, whether or not it exists | 5 failures in 15 minutes | 15 minutes | "Too many failed sign-in attempts. Try again in 15 minutes." A correct password is also refused during the cooldown. A successful sign-in clears the count. |
  | Password-reset request | Submitted email, lowercased, whether or not it matches an account | 3 per hour | Remainder of the hour | The normal generic message; no email is sent. |
  | Confirmation email | Account (including a just-created account at signup); covers signup, new add/change requests, replacement addresses, and resends | 3 per hour | Remainder of the hour | "You've requested several confirmation emails. Please wait before requesting another." Pending address and Cancel stay available; a refused new request leaves the existing pending request unchanged. |

  - "Per hour" is a 60-minute window that starts with the first counted request.
  - Cooldowns are always temporary; no account is ever permanently locked.
  - Counters reset on server restart and are not shared between processes; this is documented (Phase 9).
- **Admin**: From Phase 2 on, there is no admin path around the email rules. Changing a confirmed email in the admin clears any pending request and sends no notice; duplicates show as form errors, not crashes.
- **Testing**: Follow `docs/TESTING.md`: pytest-django, plain fixtures in `conftest.py`, no factories, **tests never invoke the seed command**, and the suite is green at every phase boundary. Sent mail is checked through Django's test outbox. From Phase 5 on, the cache is cleared before every test so counters never leak between tests.
- **Seed restriction**: `seed` is never run against the current development database (`db.sqlite3`) or the current `media/` folder. Phase 9 verifies it in an isolated throwaway setup.

---

## Phase 1: Read-only Security Center overview

**User stories**: 15, 16, 37, 40, 41, 45

### What to build

An "Account" link beside "Addresses" in the signed-in navigation leads to `accounts:security`. The overview has two sections:

- **Email**: the confirmed address, or the reminder "Add an email so you can recover your account."
- **Password**: for accounts with an unusable password, the "password management unavailable, contact support" message. Otherwise, a short description only.

There are **no action buttons yet**. Add/Change email arrives in Phase 2, and Change password in Phase 7. Signed-out visitors are redirected to sign in.

### Acceptance criteria

- [ ] Signed-in customer, staff, and superuser each get 200 at `accounts:security`.
- [ ] Anonymous visitors are redirected to the sign-in page with `next` set.
- [ ] The navbar shows "Account" beside "Addresses" for signed-in users only.
- [ ] A user with a confirmed email sees it; a user with a blank email sees the reminder.
- [ ] An unusable-password user sees the contact-support message in the password section.
- [ ] The page has no Add email, Change email, or Change password controls.

### How we'll check it

- **Automated:** view tests for access by each role, anonymous redirect, confirmed-email vs. reminder rendering, unusable-password message, absence of action controls, and the navbar link.
- **Manual:** run the dev server against the current database (no seed). Sign in as `customer`, click "Account," and see the confirmed email. Sign out and visit `/accounts/security/` directly; you should be sent to sign in.

---

## Phase 2: Add/change email and confirmation, with admin protection

**User stories**: 17, 18, 19, 24, 25, 26, 27, 28, 38, 43, 46, 47, 48, 50, 51

### What to build

- **Email delivery:** email settings come from `.env` via environs with the console backend as default. `.env.example` gains commented placeholders for SMTP.
- **Data:** the migration adds the pending-email fields and the case-insensitive conditional uniqueness constraint.
- **Request:** the overview gains an **"Add email"** button (no confirmed email) or a **"Change email"** button (otherwise), leading to `accounts:email_change`. The form takes the new address and the current password. It rejects a wrong password, an address another account has already confirmed (ignoring case), and the account's own current confirmed address (ignoring case). A valid request:
  - sets the pending address,
  - replaces any earlier request, so earlier links stop working,
  - sends a confirmation link to the new address,
  - leaves the confirmed address unchanged,
  - returns to the overview with a message.

  Unusable-password accounts opening this page are redirected to the overview with the contact-support message.
- **Confirmation:** `accounts:email_confirm` is public. A valid link (newest request, under 24 hours old, issued for the current pending address):
  - makes the pending address the confirmed address and clears the pending request, so **the same link can't be used again**,
  - sends a change notice to the old confirmed address, if there was one,
  - never signs anyone in or changes who is signed in.

  If another account confirmed the address first, the request is refused and cleared, the existing confirmed email is kept, and the user is told to add a different address in the Security Center. Expired, replaced, or already-used links show "this link is no longer valid" and point to the Security Center.
- **Admin:** editing a user's confirmed email clears any pending request and sends no notices. A case-insensitive duplicate shows a form error, not an `IntegrityError`.

### Acceptance criteria

- [ ] Migration applies cleanly to an empty test database. The constraint rejects case-insensitive duplicates and allows any number of blank emails.
- [ ] The button label is "Add email" or "Change email" depending on whether an email is confirmed.
- [ ] Wrong current password, an address another account has confirmed (any capitalization), or the account's own confirmed address (any capitalization) produces a form error. No pending change and no email.
- [ ] Another account's *pending* address does not block a request.
- [ ] A valid request sends exactly one email, to the new address, with a working link. The confirmed address is unchanged until the link is clicked.
- [ ] A second request makes the first link stop working. Only the newest link confirms.
- [ ] A successfully used link is refused the second time.
- [ ] A link older than 24 hours is refused.
- [ ] Confirmation works while anonymous and while signed in as a different user, and the signed-in state is unchanged in both cases.
- [ ] A change notice goes to the old address. A first-time addition sends no notice.
- [ ] Two accounts pending the same address: the first to confirm wins. The second is refused with the "add a different address" message, its pending request is cleared, and its existing confirmed email is kept.
- [ ] An unusable-password user is redirected from the request page with the contact-support message.
- [ ] The admin change form clears the pending request when the confirmed email changes, sends no email, and shows a form error on a duplicate.
- [ ] With no `.env`, emails print to the console.

### How we'll check it

- **Automated:** model-method tests for request/confirm state changes. Form tests for password and uniqueness validation. View tests covering every acceptance criterion above, using the test outbox to read links and controlling time for the 24-hour expiry. A race test with two pending accounts. Admin form tests for clearing the pending request and for duplicate errors. A constraint test that writes directly to the database.
- **Manual:** this phase needs a migration. It is applied only when this phase is being built, not during planning. Then, in the dev server: sign in as a user with no email, add one, copy the link from the terminal, open it in a private window, and see the email confirmed. Request a change, request another, and check that the first link is refused. Reuse a used link and check that it's refused. In the admin, try saving a duplicate email and see the form error.

---

## Phase 3: Managing a pending request

**User stories**: 20, 21, 22, 23, 35 (email actions), 44

### What to build

The overview's email section shows any pending address with its status ("link sent" or "link expired") and **Resend** and **Cancel** buttons, both POST-only.

- **Resend** sends a fresh link for the same pending address. Earlier links stop working.
- **Cancel** clears the pending request. Any outstanding link stops working.

Both return to the overview with a clear message. Accounts with an unusable password can still confirm, resend, and cancel an existing request; only add/change stays blocked.

### Acceptance criteria

- [ ] The pending address and "link sent" status show while the link is valid, and "link expired" after 24 hours.
- [ ] Resend sends one new email. The new link works and the previous link is refused.
- [ ] Cancel clears the pending request, the outstanding link is refused, and the confirmed email is untouched.
- [ ] Resend and Cancel reject GET and require sign-in.
- [ ] Resend/Cancel with no pending request redirect to the overview with a harmless message.
- [ ] An unusable-password account with a pending request can resend, cancel, and confirm.
- [ ] Each action returns to the overview with a success message.

### How we'll check it

- **Automated:** view tests for status display (with controlled time), links replaced after resend and cancel, POST-only and sign-in enforcement, the no-pending case, and the unusable-password path.
- **Manual:** start a change, check the pending address shows. Resend, and confirm that the older link in the terminal is refused while the newer one works. Start another change and cancel it; check the link is refused.

---

## Phase 4: Signup requires an email

**User stories**: 1, 2, 3, 4, 5, 6, 39

### What to build

The signup form gains a required email field. It is checked case-insensitively against other accounts' **confirmed** emails ("already registered" on conflict). Another account's pending address does not block it. The new account is created with:

- a blank confirmed email,
- the signup address as its pending address,
- a confirmation link sent immediately.

Signup still redirects to the sign-in page (no auto sign-in). The success message tells the customer to check their inbox to confirm their email. Signed in before confirming, the Security Center shows the reminder plus the pending address with Resend and Cancel. Update the `SignupForm` docstring and core PRD story 6, which previously said signup asks for no email.

### Acceptance criteria

- [ ] Signup without an email shows a field error.
- [ ] Signup with an address another account has confirmed, in any capitalization, shows "already registered."
- [ ] Signup with an address another account has only pending succeeds.
- [ ] A new account has a blank confirmed email, the signup address as pending, and exactly one confirmation email in the outbox.
- [ ] The customer is redirected to sign in, sees the "check your inbox" message, and can sign in immediately.
- [ ] Clicking the signup link confirms the address. No change notice is sent.
- [ ] Existing signup tests are updated to include an email and still pass.

### How we'll check it

- **Automated:** form and view tests for each criterion. The existing tests in `accounts/tests.py` are updated.
- **Manual:** sign up a fresh account, sign in right away, visit Account to see the reminder and pending address, click the terminal link, and see it confirmed.

---

## Phase 5: Confirmation-email rate limit

**User stories**: 36, 44 (rate-limit rule)

### What to build

A small rate-limit helper in `accounts`, built on Django's cache. It counts events per key in a 60-minute window that starts with the first counted event, and reports whether the key is over the limit. The first limit to use it is the **confirmation-email budget: 3 per account per hour**, shared by signup, new add/change requests, replacement addresses, and resends.

When the budget is spent:

- the user sees "You've requested several confirmation emails. Please wait before requesting another.",
- no email is sent,
- a refused new request leaves the existing pending request (and its link) unchanged,
- the pending address and Cancel stay available.

At signup, a confirmation email refused by the limit doesn't block account creation. (With a fresh account this can't actually happen, but the count is recorded.) A project-wide test fixture clears the cache before every test.

### Acceptance criteria

- [ ] The signup email counts as one of the account's 3.
- [ ] Three confirmation emails in an hour succeed; the fourth (request, replacement address, or resend) is refused with the message above and sends nothing.
- [ ] A refused new request leaves the earlier pending address in place, and its newest link still works.
- [ ] Cancel still works while the budget is spent.
- [ ] After the 60-minute window passes, requests are allowed again.
- [ ] Counters for one account don't affect another.
- [ ] Tests don't leak counters into each other.

### How we'll check it

- **Automated:** unit tests for the helper (counting, window start, expiry under controlled time). View tests for the shared budget across signup, replacement addresses, and resends. Tests that a refused request leaves state unchanged and that Cancel still works.
- **Manual:** in the dev server, resend the confirmation repeatedly and check that the fourth attempt shows the wait message and prints no email.

---

## Phase 6: Forgotten-password reset

**User stories**: 7, 8, 9, 10, 11, 12, 13, 34, 40

### What to build

Django's built-in password reset flow, at the `accounts` URLs above, with styled templates:

- **Sign-in page:** gains a "Forgot password?" link.
- **Request page:** takes an email address. Accounts are looked up by **confirmed** email only, ignoring case. The page always answers "If an account exists for that address, we've sent a reset link," plus a reminder to check spam and double-check the address. Only an active account with a usable password whose confirmed email matches gets an email. Unknown addresses, pending-only addresses, inactive accounts, and unusable passwords all get the same message and no email.
- **Reset link:** expires after **1 hour** and works once. Setting a new password doesn't require the old one and runs the existing password validators.
- **After a reset:** the user is **not** signed in. They're sent to sign in with a message asking them to use the new password. All existing sessions are signed out, and a reset notice goes to the confirmed email.
- **Invalid link:** an expired or used link shows a clear message with a link to request another reset.

### Acceptance criteria

- [ ] The sign-in page links to `accounts:password_reset`.
- [ ] Known confirmed email (any capitalization): one reset email, sent to the confirmed address.
- [ ] Unknown addresses, pending-only addresses, inactive accounts, and unusable passwords: identical response, no email.
- [ ] The reset link sets a new password without the old one. Weak passwords are rejected by the validators.
- [ ] After a reset: the user is not signed in, lands on sign-in with the message, sessions signed in before the reset are signed out, and the reset notice is sent.
- [ ] A link older than 1 hour, or already used, shows the invalid-link page with a "request another" link.

### How we'll check it

- **Automated:** view tests for each criterion. Compare response bodies to prove the reset page reveals nothing. Read links from the test outbox. Control time for the 1-hour expiry. Test signing out existing sessions with a second client signed in before the reset.
- **Manual:** click "Forgot password?", enter a confirmed address, copy the link from the terminal, set a new password, and sign in with it. Reuse the link and see the invalid-link page. Enter an unknown address and see the same message with nothing printed.

---

## Phase 7: Password change and its notice

**User stories**: 29, 30, 31, 32, 33, 35, 42

### What to build

The overview's password section gains a **"Change password"** button (usable-password accounts only) leading to `accounts:password_change`. It uses Django's built-in password-change form: current password, new password, and confirmation, checked by the existing validators.

On success:

- this browser stays signed in and every other session is signed out,
- the user returns to the overview with a success message,
- a notice goes to the confirmed email with a link to the password reset page, which works since Phase 6. No confirmed email means no notice.

Accounts with an unusable password don't see the button. If they open the page directly, they're redirected to the overview with the contact-support message.

### Acceptance criteria

- [ ] The Change password button appears for usable-password users only.
- [ ] A wrong current password, mismatched confirmation, or weak new password produces form errors.
- [ ] On success: the current client stays signed in, a second client signed in beforehand is signed out, and the user lands on the overview with a message.
- [ ] A notice with an absolute link to `accounts:password_reset` is sent to the confirmed email. No email is sent when no email is confirmed.
- [ ] An unusable-password user opening the page directly is redirected with the contact-support message.

### How we'll check it

- **Automated:** view tests for each criterion. Two test clients to verify other sessions are signed out. Outbox checks for the notice and its reset link.
- **Manual:** sign in in two browsers, change the password in one, and check that the other is signed out. Check that the terminal shows the notice and that its link opens the reset page.

---

## Phase 8: Sign-in and reset-request rate limits

**User stories**: 14, 9 (throttled case)

### What to build

Two more uses of the Phase 5 helper:

- **Sign-in:** per submitted username, counted whether or not the username exists. After **5 failures in 15 minutes**, sign-in is refused for **15 minutes** with "Too many failed sign-in attempts. Try again in 15 minutes." The right password is also refused during the cooldown. A successful sign-in clears the count.
- **Password-reset requests:** per submitted email, lowercased first, counted whether or not it matches an account. After **3 requests in an hour**, more requests show the normal generic message and send **no email** until the window ends.

### Acceptance criteria

- [ ] Five failed sign-ins lock that username. The sixth attempt, even with the right password, shows the cooldown message.
- [ ] A username that doesn't exist is throttled the same way.
- [ ] A successful sign-in before the limit clears the count.
- [ ] After 15 minutes, sign-in works again.
- [ ] Locking one username doesn't affect another.
- [ ] A fourth reset request for the same email (any capitalization) within the hour shows the identical generic message and sends no email. After the window it sends again.
- [ ] No account is ever permanently locked.

### How we'll check it

- **Automated:** view tests for each criterion, with controlled time for the cooldown and window. Capitalization variants for the reset key. A test with a nonexistent username.
- **Manual:** enter a wrong password five times for `customer` and see the cooldown message, then the right password still refused. Restart the dev server and see the count reset, which is the documented limitation.

---

## Phase 9: Seed, admin passwords, and documentation

**User stories**: 49, 52, 53

### What to build

- **Seed:** existing demo and background emails remain confirmed (no pending state). Add the documented demo customer `newcustomer` / `newcustomer123`: a usable password and no email, with the seed's managed usernames updated so reruns stay idempotent.
- **Admin:** confirm that the existing admin password tools set a usable password for an unusable-password account, and that the Phase 2 email rules still hold.
- **Docs:** in the README and/or `docs/`:
  - add `newcustomer` to the demo logins,
  - how to test emails by copying links from the terminal,
  - how to configure SMTP through `.env`,
  - the in-memory rate-limit limitation (resets on restart, not shared between processes; production would use a shared cache).
- **Core plan wording:** update the "no email" signup wording in `plans/core-platform.md` (Phase 3, task 1) to say that signup now requires an email, with a reference to `prd/account-security.md`. Add a short note rather than rewriting the core plan's history.

### Acceptance criteria

- [ ] Seed code creates `newcustomer` with a usable password and a blank email. Every other seeded user keeps a confirmed `example.com` email with no pending request.
- [ ] Running the seed twice in a row succeeds and produces the same users.
- [ ] An admin can set a usable password for a background customer through the admin's password form.
- [ ] Docs cover the new demo login, testing emails in the terminal, SMTP setup, and the rate-limit limitation.
- [ ] `plans/core-platform.md` no longer describes signup as having no email, and points to `prd/account-security.md`.
- [ ] The normal test suite contains no seed calls.
- [ ] The full test suite passes and Ruff reports no lint or formatting problems.

### How we'll check it

- **Automated (normal suite):** an admin test for setting a usable password. No seed calls, per `docs/TESTING.md`.
- **Isolated seed check (never touches the current database or `media/`):**
  1. Before starting, record a checksum and modification time for `db.sqlite3`, and a file listing (names, sizes, modification times) of `media/`.
  2. Create a temporary settings module **outside the repository** (in the session scratchpad). It imports `config.settings` and overrides `DATABASES` to a new SQLite file and `MEDIA_ROOT` to a new empty folder, both inside a temporary directory. Redirecting media matters because `products/signals.py` deletes image files when products are deleted.
  3. Using only that settings module (`--settings`), run `migrate`, then `seed` **twice**.
  4. Against the throwaway database, check that `newcustomer` signs in with `newcustomer123` and has a blank email, the other demo users have confirmed emails and no pending request, and no two confirmed emails collide ignoring case.
  5. Re-check the `db.sqlite3` checksum and modification time and the `media/` listing, and confirm both are unchanged. Delete the temporary directory.
- **Manual:** after the isolated check, review the README demo-login table, the email/SMTP docs, and the updated signup wording in `plans/core-platform.md`.
- **Final check (last step of the feature):** run the full suite with `uv run pytest`, then `uv run ruff check .` and `uv run ruff format --check .`. All three must pass with no failures or changes needed. Report any failure with its output instead of marking the phase done.
