# PRD: The ThoughtTronix Store — Account Security Center

---

## Problem Statement

ThoughtTronix customers sign up with only a username and password. The store never asks for an email address, so a customer who forgets their password has no way back into their account. Their order history and saved addresses are lost unless staff step in by hand. Signed-in customers also have no way to change their own password, and nobody is told when something security-sensitive happens to their account. If someone else changes a customer's password, the real owner finds out only when they can no longer sign in.

The sign-in form also accepts unlimited password guesses. Nothing slows down someone trying passwords against a customer's username, and a recovery flow built without limits could be used to flood an inbox with emails.

## Solution

An **Account Security Center**: a page every signed-in user can reach from an "Account" link in the navigation. It gives customers control over the two things that protect their account, their email address and their password, alongside a public "Forgot password?" flow.

- **A verified email on every new account.** Signup requires an email address. The address stays *pending* until the customer clicks a confirmation link, and only a confirmed address is ever used for password resets or security notices. Customers can still sign in and shop right away.
- **Email management.** Customers can add an email (if the account has none) or change it. Both require the current password and a confirmation link sent to the new address. The old address keeps working until the new one is confirmed, and then it receives a notice that the change happened.
- **Password change.** Customers change their password by entering the current one. Other signed-in browsers are signed out, and a notice goes to their confirmed email.
- **Forgotten-password reset.** Anyone can request a reset link by email. The page never reveals whether an address belongs to an account. Links expire after one hour, and a reset signs out every session and sends a notice.
- **Rate limits.** Failed sign-ins, reset requests, and confirmation emails are limited, with temporary cooldowns, so the flows can't be used for password guessing or inbox flooding.

Sign-in stays username-based. Email is for recovery and notices only.

## User Stories

**Visitor (not signed in)**

1. As a visitor, I want to give an email address when I sign up, so that I can recover my account if I forget my password.
2. As a visitor, I want signup to tell me when an email address is already registered to another account, so that I know to sign in or recover that account instead.
3. As a visitor, I want signup to treat email addresses that differ only in capitalization as the same address, so that I can't accidentally create a second account for the same inbox.
4. As a visitor, I want signup to accept an email address that another account has only *pending* (unconfirmed), so that someone who never confirmed my address can't block me from registering with it.
5. As a new customer, I want to be able to sign in and shop immediately after signing up, so that confirming my email doesn't stand between me and the store.
6. As a new customer, I want a confirmation link emailed to the address I signed up with, so that I can prove the address is mine.
7. As a visitor who forgot my password, I want a "Forgot password?" link on the sign-in page, so that I can find the reset flow.
8. As a visitor, I want to request a password reset by entering my email address, so that I get a link to set a new password.
9. As a visitor, I want the reset page to always respond "If an account exists for that address, we've sent a reset link," so that nobody can use it to find out whether an address belongs to a ThoughtTronix customer.
10. As a visitor whose reset email hasn't arrived, I want the reset page to remind me to check my spam folder and double-check the address I entered, so that I can work out what went wrong without the page revealing account details.
11. As a visitor, I want to set a new password from the reset link without entering my old password, so that I can recover an account whose password I've forgotten.
12. As a visitor who has just reset my password, I want to be sent to the sign-in page with a message asking me to sign in with my new password, so that I know the reset worked.
13. As a visitor with an expired or already-used reset link, I want a clear message explaining that the link no longer works, with a way to request another reset, so that I'm not stuck.
14. As a visitor who has entered the wrong password five times, I want a clear message saying to try again in 15 minutes, so that I understand why sign-in is refusing me.

**Customer (signed in)**

15. As a customer, I want an "Account" link beside "Addresses" in the navigation, so that I can find my Security Center.
16. As a customer, I want the Security Center overview to show my confirmed email address, so that I know where recovery emails and security notices will go.
17. As a customer, I want to change my email by entering the new address and my current password, so that someone at my unattended, signed-in browser can't take over my account.
18. As a customer, I want my current email to keep working until I confirm the new one, so that a typo in the new address can't lock me out.
19. As a customer, I want a confirmation link sent to my new address, so that the change only takes effect once I've proven I control that inbox.
20. As a customer, I want the Security Center to show my pending address with its status (link sent, or link expired), so that I know a change is in progress.
21. As a customer, I want to resend the confirmation link, so that I can get a new one if the first email got lost or expired. The new link replaces the old one.
22. As a customer, I want to cancel a pending change, so that I can back out of a change I no longer want. Canceling makes the outstanding link stop working.
23. As a customer, I want a new email-change request to replace any earlier pending request, so that only my latest choice can be confirmed.
24. As a customer, I want confirmation links to expire after 24 hours, so that an old link sitting in an inbox can't be used later.
25. As a customer, I want the confirmation link to work even if I open it in a browser where I'm not signed in, such as my phone's mail app, so that confirming is easy.
26. As a customer, I want clicking a confirmation link to never sign anyone in or switch which account is signed in, so that a link in an inbox is never a way into my account.
27. As a customer, I want my old address to receive a notice after my email change is confirmed, so that if the change wasn't me, I find out.
28. As a customer, I want confirmation to be refused if another account confirmed the same address first, with a message directing me to add a different address in my Security Center, so that two accounts can never share a confirmed email. My existing confirmed email, if I have one, stays in place.
29. As a customer, I want to change my password by entering my current password and a new one, so that I can keep my account secure.
30. As a customer, I want my new password checked against the store's existing password rules, so that I can't pick a weak one.
31. As a customer, I want to stay signed in on the browser where I changed my password while every other browser is signed out, so that anyone using my old password elsewhere loses access.
32. As a customer, I want to be returned to the Security Center with a success message after changing my password, so that I know it worked.
33. As a customer, I want a notice sent to my confirmed email when my password changes, including a link to the password reset page, so that I can take my account back if the change wasn't me.
34. As a customer, I want a notice sent to my confirmed email when my password is reset, so that an unexpected reset doesn't go unnoticed.
35. As a customer, I want every completed Security Center action to return me to the overview with a clear message, so that I always know what just happened.
36. As a customer, I want confirmation emails limited to three per hour across initial requests, replacement addresses, and resends, so that my account can't be used to flood an inbox. I want a clear message when I hit the limit.

**Customer without a confirmed email**

37. As a customer whose account has no confirmed email, I want the Security Center to remind me to "Add an email so you can recover your account," so that I notice the gap.
38. As a customer whose account has no confirmed email, I want the email action labeled "Add email" (instead of "Change email"), so that the button describes what I'm doing.
39. As a new customer who hasn't clicked my signup confirmation link yet, I want the Security Center to keep reminding me until I confirm, with the pending address shown alongside Resend and Cancel, so that I can finish setting up recovery.
40. As a customer without a confirmed email, I understand that password resets and security notices can't reach me, because only confirmed addresses are ever used.

**Account with an unusable password**

41. As a user whose account has no usable password, I want the Security Center's password section to say that password management isn't available for my account and that I should contact support, so that I'm not offered actions that can't work.
42. As a user whose account has no usable password, I want to be sent back to the overview with the contact-support message if I open the change-password page directly, so that I don't land on a form I can't use.
43. As a user whose account has no usable password, I want adding or changing an email to show the same contact-support message, because those actions require my current password.
44. As a user whose account has no usable password, I want to still be able to confirm, resend, or cancel a pending email request I already have, under the same expiry, rate-limit, and uniqueness rules as everyone else.

**Staff and admin**

45. As an employee or administrator, I want to use the Security Center for my own account, so that I can manage my email and password like any other user.
46. As an authorized admin, I want to edit a user's confirmed email directly in the Django admin, without confirmation or notices, so that I can help a customer who has lost access to their old inbox.
47. As an authorized admin, I want admin email edits to still enforce case-insensitive uniqueness, so that I can't accidentally give two accounts the same confirmed email.
48. As an authorized admin, I want any pending email request to be cleared when I change a user's confirmed email, so that an outdated link can't overwrite my correction.
49. As an authorized admin, I want to set a usable password for an account through the existing admin tools, so that I can help users whose accounts have no usable password.

**Developer and grader**

50. As a developer, I want emails to print to the terminal by default, so that I can test every flow by copying links from the server output, without any setup.
51. As a developer, I want SMTP delivery configured entirely through `.env`, with placeholder settings in `.env.example`, so that I can send real email without putting credentials in Git.
52. As a grader, I want a seeded demo customer with a usable password and no email, so that I can see the missing-email reminder right after signing in.
53. As a grader, I want the existing seeded demo accounts to start with confirmed emails, so that the password-reset and change flows work on them immediately.

## Implementation Decisions

**Identity and the email model**

- Sign-in stays username-based. Email addresses are used only for account recovery and security notices.
- The user's existing email field holds the **confirmed** address. Blank means the account has no confirmed email. New fields on the user store the **pending** address and whatever is needed to make only the newest confirmation link valid.
- Uniqueness is case-insensitive and covers **confirmed, non-blank** addresses only. It's enforced by a conditional database constraint on the lowercased email, so it holds everywhere: signup, email change, confirmation, and the Django admin. Blank emails are exempt, so any number of accounts can have no email.
- Pending addresses reserve nothing. Several accounts may have the same pending address, and the first to confirm wins.
- Uniqueness is checked against confirmed addresses twice: when an add/change is requested (or at signup), and again when the link is clicked.

**Signup**

- The signup form adds a required email field, validated case-insensitively against other accounts' confirmed emails ("already registered" on conflict).
- The signup email is saved as the new account's **pending** address. The confirmed email starts blank. A confirmation link is sent immediately, and that email counts toward the account's confirmation-email limit.
- After signup, the customer is still sent to the sign-in page, as today, and can sign in right away. The success message tells them to check their inbox to confirm their email.

**Email add/change and confirmation**

- The add/change form takes the new address and the current password. A valid request sets the pending address, invalidates any earlier link, and sends a confirmation link to the new address. The confirmed address is unchanged.
- There is one pending request per account. A new request, a resend, a cancel, or a successful confirmation invalidates every earlier link.
- Confirmation links are signed and expire after **24 hours**. They're tied to the specific pending request, so only the newest link for the current pending address works.
- The confirmation view does not require sign-in. A valid link confirms exactly the pending address it was issued for. It never signs anyone in and never changes which account is signed in.
- On successful confirmation, the pending address becomes the confirmed address, the pending request is cleared, and, if there was a previous confirmed address, a change notice goes to that **old** address. Signup confirmations and first-time additions have no old address, so no notice is sent.
- If confirmation finds another account already confirmed the address, the change is refused, the pending request is cleared, the existing confirmed email (if any) is kept, and the customer is directed to add a different address in the Security Center.
- An expired or superseded link shows a clear "this link is no longer valid" message and points the customer to the Security Center to resend.
- Accounts with an unusable password can't add or change an email (both require the current password) and see the contact-support message instead. They can still confirm, resend, or cancel an existing pending request under the same rules.

**Password change**

- Uses Django's built-in password change flow: current password, new password, and confirmation, checked by the existing password validators.
- The current browser stays signed in, and every other session is invalidated (Django's built-in behavior, tied to the password).
- On success, the customer returns to the Security Center overview with a success message, and a notice goes to the confirmed email with a link to the password reset page. No confirmed email means no notice.
- Accounts with an unusable password don't get this form. The overview shows a "password management unavailable, contact support" message, and opening the form directly redirects back to the overview with that message.

**Password reset**

- Uses Django's built-in password reset flow, which looks up accounts by their **confirmed** email only (case-insensitive).
- The request page always shows the same message: "If an account exists for that address, we've sent a reset link." It adds a reminder to check spam and double-check the address. The same message appears for unknown addresses, inactive accounts, accounts with unusable passwords, and throttled requests. None of those cases sends an email.
- Reset links expire after **1 hour**, which means lowering Django's password-reset timeout from its 3-day default. A link stops working once used.
- Setting a new password through the link does not require the old password. Afterward, the user is **not** signed in automatically. They're sent to sign in with the new password, all existing sessions are invalidated, and a notice goes to the confirmed email.
- Expired or used links show a clear message with an option to request another reset.
- The sign-in page gains a "Forgot password?" link.

**Rate limits**

| Action | Counted per | Limit | Cooldown | What the user sees |
|---|---|---|---|---|
| Sign-in | Submitted username, counted whether or not the username exists | 5 failures in 15 minutes | 15 minutes | "Too many failed sign-in attempts. Try again in 15 minutes." Even a correct password is refused during the cooldown. A successful sign-in clears the count. |
| Password reset request | Submitted email, lowercased first, counted whether or not it matches an account | 3 per hour | Remainder of the hour | The normal generic message. No email is sent. |
| Confirmation email | Account, including the newly created account at signup; covers initial signup confirmation, new add/change requests, replacement addresses, and resends | 3 per hour | Remainder of the hour | "You've requested several confirmation emails. Please wait before requesting another." The pending address and Cancel stay available, and a refused new request leaves the existing pending request unchanged. |

- "Per hour" means a 60-minute window that starts with the first counted request.
- Counters live in Django's cache, using the default in-process memory cache. No new database tables are needed. Counters reset when the server restarts and aren't shared between server processes, and this limitation must be documented. A production deployment would point the cache at a shared store.
- Cooldowns are always temporary. No account is ever permanently locked.

**Security Center page and navigation**

- Every signed-in user can access it, including staff and superusers. Signed-out visitors are redirected to sign in. The password reset flow stays public.
- The overview page has two sections:
  - **Email:** the confirmed address, or the "Add an email so you can recover your account" reminder; any pending address with its status (link sent or link expired) and **Resend** / **Cancel** actions; and a button labeled **"Add email"** when no email is confirmed and **"Change email"** otherwise.
  - **Password:** a "Change password" button, or the contact-support message for accounts with an unusable password.
- The email and password forms each have their own page, as separate class-based views, each with one form that owns its validation. Completed actions (request, resend, cancel, password change) return to the overview with a clear message.
- An "Account" link to the overview is added beside "Addresses" in the signed-in navigation.
- Security emails link back to the Security Center or the reset page, as appropriate.

**Architecture**

- The work lives in the existing `accounts` app. Email-confirmation state changes (request, resend, cancel, confirm) are methods on the user model, forms own validation (including the current-password and uniqueness checks), and views stay thin, following the project's architecture convention.
- Rate limiting is a small helper in the `accounts` app, built on Django's cache.

**Email delivery**

- Email settings are read from `.env` via environs: backend, host, port, username, password, TLS, and default sender. The default is the console backend, so the app works with no `.env` and no setup.
- The default sender is a ThoughtTronix no-reply address on a reserved example domain.
- All emails are plain text: signup/change confirmation, email-changed notice, password-changed notice, password-reset link, and password-reset notice.
- `.env.example` gains commented placeholder email settings. Real credentials stay in the gitignored `.env`.
- Documentation explains how to test emails by reading links from the terminal, and how to configure SMTP.

**Data, migration, and seed**

- The migration adds the pending-email fields and the conditional case-insensitive uniqueness constraint. Existing email values become those users' confirmed addresses without any data change. A read-only check of the current development database found 12 users, no blank emails, and no case-insensitive duplicates, so the constraint will apply cleanly.
- The seed command treats existing seeded emails as confirmed and adds one documented demo customer with a usable password and no email (`newcustomer` / `newcustomer123`), so the missing-email flow can be tested immediately.
- The seed command is updated but **must not be run** against the current development database, because it would erase products and uploaded images from earlier coursework.

**Django admin**

- Authorized admins can edit a user's confirmed email directly, with no confirmation and no notices. The uniqueness constraint still applies. Changing the confirmed email clears any pending request.
- Admins set usable passwords for accounts through the existing admin tools.

## Out of Scope

- Signing in with an email address, or with either a username or an email.
- "Sign out of all other devices" without a password change.
- A recent sign-in activity list.
- Two-factor authentication.
- Closing the signup form's "already registered" disclosure. This is accepted as a known trade-off of email uniqueness.
- HTML email templates and transactional email services. Delivery is console or SMTP only.
- Persistent or shared rate-limit storage, such as a database table or Redis.
- HTMX inline forms on the Security Center.
- Notices for admin-made email edits.
- Self-service recovery for accounts with unusable passwords.
- Auto sign-in after signup (unchanged from the core platform).

## Further Notes

- This reverses a core-platform decision: signup previously asked for no email, per the core PRD's user story 6 and the comment on the signup form. Both should be updated to match.
- Only confirmed addresses receive password-reset emails and security notices. Pending addresses receive confirmation emails only. Confirmation and reset flows never automatically sign anyone in. Customer security changes trigger notices as specified; admin email overrides are exempt.
- Seeded addresses use the reserved `example.com` domain, so nothing real is emailed even with SMTP configured.
- Some edge cases need dedicated tests: confirm-time uniqueness races between two pending accounts, superseded links (after resend, cancel, replacement, and confirmation), 24-hour and 1-hour expiry, sign-in throttling for usernames that don't exist, silent reset throttling, the shared confirmation-email budget across replacement addresses, and unusable-password accounts (blocked add/change, but allowed confirm/resend/cancel). Follow the project's testing conventions when writing them.
