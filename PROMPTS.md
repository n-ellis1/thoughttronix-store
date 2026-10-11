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
