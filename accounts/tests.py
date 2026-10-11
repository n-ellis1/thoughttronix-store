import re
from datetime import datetime, timedelta
from http import HTTPStatus
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import EMAIL_LINK_LIFETIME, EmailAlreadyConfirmed
from accounts.ratelimit import RateLimit, reset_requests

# --- Signup -----------------------------------------------------------------


def test_signup_page_returns_200(client, db):
    response = client.get(reverse("accounts:signup"))

    assert response.status_code == HTTPStatus.OK


def signup(client, email="fresh@example.com", **overrides):
    data = {
        "username": "fresh-thinker",
        "email": email,
        "password1": "neural-implant-9000",
        "password2": "neural-implant-9000",
        **overrides,
    }
    return client.post(reverse("accounts:signup"), data, follow=True)


def test_signup_creates_plain_customer(client, db):
    response = signup(client)

    user = get_user_model().objects.get(username="fresh-thinker")
    assert not user.is_staff
    assert not user.is_superuser

    # Signup hands off to the login page with a confirmation message;
    # auto-login is a student exercise, so the visitor is still anonymous.
    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    page = response.content.decode()
    assert "Account created" in page
    assert "Check your inbox at fresh@example.com" in page
    assert not response.context["user"].is_authenticated


def test_signup_password_mismatch_shows_field_error(client, db):
    response = signup(client, password2="neural-implant-9001")

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["password2"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


@pytest.mark.parametrize("email", ["", "not-an-email"])
def test_signup_requires_a_valid_email(client, db, mailoutbox, email):
    response = signup(client, email=email)

    assert response.context["form"].errors["email"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()
    assert mailoutbox == []


@pytest.mark.parametrize("email", ["taken@example.com", "TAKEN@Example.COM"])
def test_signup_rejects_address_confirmed_elsewhere(client, db, mailoutbox, email):
    get_user_model().objects.create_user(username="first", email="taken@example.com")

    response = signup(client, email=email)

    assert "already registered" in response.context["form"].errors["email"][0]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()
    assert mailoutbox == []


def test_signup_allows_address_pending_elsewhere(client, customer):
    customer.request_email_change("shared@example.com")

    signup(client, email="shared@example.com")

    user = get_user_model().objects.get(username="fresh-thinker")
    assert user.pending_email == "shared@example.com"


def test_signup_email_is_pending_with_one_confirmation_link(client, db, mailoutbox):
    signup(client)

    user = get_user_model().objects.get(username="fresh-thinker")
    assert user.email == ""
    assert user.pending_email == "fresh@example.com"
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["fresh@example.com"]
    confirm_path(mailoutbox[0])


def test_new_customer_can_sign_in_before_confirming(client, db):
    signup(client)

    response = client.post(
        reverse("accounts:login"),
        {"username": "fresh-thinker", "password": "neural-implant-9000"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert client.get(reverse("accounts:security")).context["user"].is_authenticated


def test_unconfirmed_signup_shows_reminder_and_pending_address(client, db):
    signup(client)
    client.login(username="fresh-thinker", password="neural-implant-9000")

    page = client.get(reverse("accounts:security")).content.decode()

    assert "Add an email so you can recover your account." in page
    assert "fresh@example.com" in page
    assert "Link sent" in page
    assert reverse("accounts:email_resend") in page
    assert reverse("accounts:email_cancel") in page


def test_signup_link_confirms_without_a_change_notice(client, db, mailoutbox):
    signup(client)

    page = client.get(confirm_path(mailoutbox[0])).content.decode()

    assert "Your email address is confirmed" in page
    user = get_user_model().objects.get(username="fresh-thinker")
    assert user.email == "fresh@example.com"
    assert user.pending_email == ""
    assert len(mailoutbox) == 1


# --- Login and logout --------------------------------------------------------


def test_login_page_returns_200(client, db):
    response = client.get(reverse("accounts:login"))

    assert response.status_code == HTTPStatus.OK


def test_login_round_trip(client, customer):
    response = client.post(
        reverse("accounts:login"),
        {"username": "customer", "password": "customer123"},
        follow=True,
    )

    assert response.redirect_chain[-1][0] == reverse("products:catalog")
    assert response.context["user"] == customer


def test_login_bad_credentials_stays_put(client, customer):
    response = client.post(
        reverse("accounts:login"),
        {"username": "customer", "password": "wrong"},
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].non_field_errors()


def test_logout_signs_out_with_message(client, customer):
    client.force_login(customer)

    response = client.post(reverse("accounts:logout"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("products:catalog")
    assert "You have signed out." in response.content.decode()
    assert not response.context["user"].is_authenticated


# --- Auth-aware navbar --------------------------------------------------------


def test_navbar_offers_login_and_signup_to_visitors(client, db):
    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:login") in page
    assert reverse("accounts:signup") in page
    assert "Sign out" not in page


def test_navbar_greets_signed_in_customer(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert "Hi, customer" in page
    assert "Sign out" in page
    assert reverse("accounts:signup") not in page


def test_navbar_offers_account_link_to_signed_in_users(client, customer):
    client.force_login(customer)

    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:security") in page
    # The Account link sits beside Addresses.
    assert page.index(reverse("orders:addresses")) < page.index(
        reverse("accounts:security")
    )


def test_navbar_hides_account_link_from_visitors(client, db):
    page = client.get(reverse("products:catalog")).content.decode()

    assert reverse("accounts:security") not in page


# --- Security Center overview ------------------------------------------------

EMAIL_REMINDER = "Add an email so you can recover your account."
CONTACT_SUPPORT = "Password management isn't available for your account."


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        username="admin", password="admin123", email="admin@example.com"
    )


@pytest.mark.parametrize("role", ["customer", "staff_user", "superuser"])
def test_security_page_open_to_every_role(client, request, role):
    client.force_login(request.getfixturevalue(role))

    response = client.get(reverse("accounts:security"))

    assert response.status_code == HTTPStatus.OK


def test_security_page_redirects_visitors_to_sign_in(client, db):
    url = reverse("accounts:security")

    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"


def test_security_page_shows_confirmed_email(client, customer):
    customer.email = "customer@example.com"
    customer.save()
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "customer@example.com" in page
    assert EMAIL_REMINDER not in page


def test_security_page_reminds_users_without_email(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert EMAIL_REMINDER in page


def test_security_page_shows_contact_support_for_unusable_password(client, customer):
    customer.set_unusable_password()
    customer.save()
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert CONTACT_SUPPORT in page


def test_security_page_hides_contact_support_for_usable_password(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert CONTACT_SUPPORT not in page


# --- Email add/change and confirmation ---------------------------------------

LINK_INVALID = "This link is no longer valid."
ADDRESS_TAKEN = "Please add a different address in your Security Center."


def confirm_path(message):
    """The confirmation link's path, read out of a sent email."""
    match = re.search(
        r"https?://[^/\s]+(/accounts/security/email/confirm/\S+/)", message.body
    )
    assert match, message.body
    return match.group(1)


def request_change(client, email, password="customer123"):
    return client.post(
        reverse("accounts:email_change"),
        {"email": email, "current_password": password},
    )


@pytest.fixture
def confirmed_customer(customer):
    customer.email = "customer@example.com"
    customer.save()
    return customer


@pytest.fixture
def other_customer(db):
    return get_user_model().objects.create_user(
        username="other", password="other123", email="other@example.com"
    )


def test_constraint_rejects_case_insensitive_duplicate_emails(db):
    User = get_user_model()
    User.objects.create_user(username="first", email="Taken@Example.com")

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(username="second", email="taken@example.com")


def test_constraint_allows_any_number_of_blank_emails(db):
    User = get_user_model()
    for username in ("one", "two", "three"):
        User.objects.create_user(username=username, email="")

    assert User.objects.filter(email="").count() == 3


def test_security_page_offers_add_email_without_confirmed_email(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "Add email" in page
    assert "Change email" not in page
    assert reverse("accounts:email_change") in page


def test_security_page_offers_change_email_with_confirmed_email(
    client, confirmed_customer
):
    client.force_login(confirmed_customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "Change email" in page
    assert "Add email" not in page


def test_email_change_page_requires_sign_in(client, db):
    url = reverse("accounts:email_change")

    response = client.get(url)

    assert response.url == f"{reverse('accounts:login')}?next={url}"


def test_email_change_rejects_wrong_password(client, customer, mailoutbox):
    client.force_login(customer)

    response = request_change(client, "new@example.com", password="wrong")

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["current_password"]
    customer.refresh_from_db()
    assert customer.pending_email == ""
    assert mailoutbox == []


@pytest.mark.parametrize("email", ["other@example.com", "OTHER@Example.COM"])
def test_email_change_rejects_address_confirmed_elsewhere(
    client, customer, other_customer, mailoutbox, email
):
    client.force_login(customer)

    response = request_change(client, email)

    assert "already registered" in response.context["form"].errors["email"][0]
    customer.refresh_from_db()
    assert customer.pending_email == ""
    assert mailoutbox == []


@pytest.mark.parametrize("email", ["customer@example.com", "Customer@EXAMPLE.com"])
def test_email_change_rejects_own_confirmed_address(
    client, confirmed_customer, mailoutbox, email
):
    client.force_login(confirmed_customer)

    response = request_change(client, email)

    errors = response.context["form"].errors["email"]
    assert errors == ["That's already your confirmed email."]
    confirmed_customer.refresh_from_db()
    assert confirmed_customer.pending_email == ""
    assert mailoutbox == []


def test_email_change_allows_address_pending_elsewhere(
    client, customer, other_customer
):
    other_customer.request_email_change("shared@example.com")
    client.force_login(customer)

    request_change(client, "shared@example.com")

    customer.refresh_from_db()
    assert customer.pending_email == "shared@example.com"


def test_valid_request_sends_one_link_and_keeps_confirmed_email(
    client, confirmed_customer, mailoutbox
):
    client.force_login(confirmed_customer)

    response = request_change(client, "new@example.com")

    assert response.url == reverse("accounts:security")
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["new@example.com"]
    confirm_path(mailoutbox[0])
    confirmed_customer.refresh_from_db()
    assert confirmed_customer.email == "customer@example.com"
    assert confirmed_customer.pending_email == "new@example.com"
    page = client.get(response.url).content.decode()
    assert "We sent a confirmation link to new@example.com" in page


def test_confirmation_link_confirms_the_address(client, customer, mailoutbox):
    client.force_login(customer)
    request_change(client, "new@example.com")

    page = client.get(confirm_path(mailoutbox[0])).content.decode()

    assert "Your email address is confirmed" in page
    customer.refresh_from_db()
    assert customer.email == "new@example.com"
    assert customer.pending_email == ""


def test_first_time_addition_sends_no_notice(client, customer, mailoutbox):
    client.force_login(customer)
    request_change(client, "new@example.com")

    client.get(confirm_path(mailoutbox[0]))

    assert len(mailoutbox) == 1


def test_change_sends_notice_to_old_address(client, confirmed_customer, mailoutbox):
    client.force_login(confirmed_customer)
    request_change(client, "new@example.com")

    client.get(confirm_path(mailoutbox[0]))

    assert len(mailoutbox) == 2
    notice = mailoutbox[1]
    assert notice.to == ["customer@example.com"]
    assert "was changed" in notice.subject
    assert "http://testserver" + reverse("accounts:security") in notice.body


def test_second_request_replaces_the_first_link(client, customer, mailoutbox):
    client.force_login(customer)
    request_change(client, "first@example.com")
    request_change(client, "second@example.com")
    first_link, second_link = (confirm_path(m) for m in mailoutbox)

    assert LINK_INVALID in client.get(first_link).content.decode()
    customer.refresh_from_db()
    assert customer.email == ""

    client.get(second_link)
    customer.refresh_from_db()
    assert customer.email == "second@example.com"


def test_used_link_is_refused_the_second_time(client, customer, mailoutbox):
    client.force_login(customer)
    request_change(client, "new@example.com")
    link = confirm_path(mailoutbox[0])
    client.get(link)

    page = client.get(link).content.decode()

    assert LINK_INVALID in page


def test_link_older_than_24_hours_is_refused(client, customer, mailoutbox):
    client.force_login(customer)
    request_change(client, "new@example.com")
    get_user_model().objects.filter(pk=customer.pk).update(
        email_link_sent_at=timezone.now() - EMAIL_LINK_LIFETIME - timedelta(seconds=1)
    )

    page = client.get(confirm_path(mailoutbox[0])).content.decode()

    assert LINK_INVALID in page
    customer.refresh_from_db()
    assert customer.email == ""


def test_link_just_under_24_hours_still_works(client, customer, mailoutbox):
    client.force_login(customer)
    request_change(client, "new@example.com")
    get_user_model().objects.filter(pk=customer.pk).update(
        email_link_sent_at=timezone.now() - EMAIL_LINK_LIFETIME + timedelta(minutes=1)
    )

    client.get(confirm_path(mailoutbox[0]))

    customer.refresh_from_db()
    assert customer.email == "new@example.com"


def test_tampered_link_is_refused(client, customer):
    token = customer.request_email_change("new@example.com")

    url = reverse("accounts:email_confirm", kwargs={"token": token + "x"})
    page = client.get(url).content.decode()

    assert LINK_INVALID in page
    customer.refresh_from_db()
    assert customer.email == ""


def test_confirmation_works_anonymously_without_signing_in(client, customer):
    token = customer.request_email_change("new@example.com")

    response = client.get(reverse("accounts:email_confirm", kwargs={"token": token}))

    assert response.status_code == HTTPStatus.OK
    assert "_auth_user_id" not in client.session
    customer.refresh_from_db()
    assert customer.email == "new@example.com"


def test_confirmation_never_switches_the_signed_in_account(
    client, customer, other_customer
):
    token = customer.request_email_change("new@example.com")
    client.force_login(other_customer)

    client.get(reverse("accounts:email_confirm", kwargs={"token": token}))

    assert client.session["_auth_user_id"] == str(other_customer.pk)
    customer.refresh_from_db()
    other_customer.refresh_from_db()
    assert customer.email == "new@example.com"
    assert other_customer.email == "other@example.com"


def test_first_account_to_confirm_a_shared_pending_address_wins(
    client, customer, other_customer
):
    first = customer.request_email_change("shared@example.com")
    second = other_customer.request_email_change("SHARED@example.com")

    client.get(reverse("accounts:email_confirm", kwargs={"token": first}))
    page = client.get(
        reverse("accounts:email_confirm", kwargs={"token": second})
    ).content.decode()

    assert ADDRESS_TAKEN in page
    customer.refresh_from_db()
    other_customer.refresh_from_db()
    assert customer.email == "shared@example.com"
    assert other_customer.email == "other@example.com"
    assert other_customer.pending_email == ""
    assert other_customer.email_token == ""


def test_confirm_survives_losing_a_race_at_the_database(customer, other_customer):
    customer.request_email_change("shared@example.com")
    # Another account confirms the address after this one's check passed.
    get_user_model().objects.filter(pk=other_customer.pk).update(
        email="shared@example.com"
    )

    with mock.patch.object(type(customer).objects, "email_taken", return_value=False):
        with pytest.raises(EmailAlreadyConfirmed):
            customer.confirm_pending_email()

    customer.refresh_from_db()
    assert customer.email == ""
    assert customer.pending_email == ""


def test_unusable_password_user_is_sent_back_with_contact_support(client, customer):
    customer.set_unusable_password()
    customer.save()
    client.force_login(customer)

    response = client.get(reverse("accounts:email_change"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    messages = [str(m) for m in response.context["messages"]]
    assert any(CONTACT_SUPPORT in m for m in messages)


def test_unusable_password_user_cannot_post_a_request(client, customer, mailoutbox):
    customer.set_unusable_password()
    customer.save()
    client.force_login(customer)

    request_change(client, "new@example.com")

    customer.refresh_from_db()
    assert customer.pending_email == ""
    assert mailoutbox == []


# --- Admin email edits --------------------------------------------------------


def admin_change_data(user, **overrides):
    """POST data for the admin's user change form, matching ``user``."""
    data = {
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "is_active": "on",
        "date_joined_0": "2026-01-01",
        "date_joined_1": "00:00:00",
        "last_login_0": "",
        "last_login_1": "",
        "job_title": "",
    }
    data.update(overrides)
    return data


def test_admin_email_edit_clears_pending_request_without_email(
    client, superuser, confirmed_customer, mailoutbox
):
    token = confirmed_customer.request_email_change("pending@example.com")
    client.force_login(superuser)
    url = reverse("admin:accounts_user_change", args=[confirmed_customer.pk])

    response = client.post(
        url, admin_change_data(confirmed_customer, email="fixed@example.com")
    )

    assert response.status_code == HTTPStatus.FOUND
    confirmed_customer.refresh_from_db()
    assert confirmed_customer.email == "fixed@example.com"
    assert confirmed_customer.pending_email == ""
    assert mailoutbox == []
    # The outdated link can no longer overwrite the correction.
    client.get(reverse("accounts:email_confirm", kwargs={"token": token}))
    confirmed_customer.refresh_from_db()
    assert confirmed_customer.email == "fixed@example.com"


def test_admin_save_without_email_change_keeps_pending_request(
    client, superuser, confirmed_customer
):
    confirmed_customer.request_email_change("pending@example.com")
    client.force_login(superuser)
    url = reverse("admin:accounts_user_change", args=[confirmed_customer.pk])

    client.post(url, admin_change_data(confirmed_customer, first_name="Casey"))

    confirmed_customer.refresh_from_db()
    assert confirmed_customer.first_name == "Casey"
    assert confirmed_customer.pending_email == "pending@example.com"


def test_admin_duplicate_email_is_a_form_error(
    client, superuser, confirmed_customer, other_customer
):
    client.force_login(superuser)
    url = reverse("admin:accounts_user_change", args=[confirmed_customer.pk])

    response = client.post(
        url, admin_change_data(confirmed_customer, email="Other@Example.com")
    )

    assert response.status_code == HTTPStatus.OK
    errors = response.context["adminform"].form.errors["email"]
    assert "already registered" in errors[0]
    confirmed_customer.refresh_from_db()
    assert confirmed_customer.email == "customer@example.com"


def test_admin_sets_a_usable_password_for_an_unusable_password_account(
    client, superuser, confirmed_customer
):
    confirmed_customer.set_unusable_password()
    confirmed_customer.save()
    client.force_login(superuser)
    # Django's UserAdmin names this URL after auth.User, even for custom models.
    url = reverse("admin:auth_user_password_change", args=[confirmed_customer.pk])

    response = client.post(
        url,
        {
            "usable_password": "true",
            "password1": "fresh-thoughts-2026",
            "password2": "fresh-thoughts-2026",
        },
    )

    assert response.status_code == HTTPStatus.FOUND
    confirmed_customer.refresh_from_db()
    assert confirmed_customer.has_usable_password()
    assert Client().login(username="customer", password="fresh-thoughts-2026")
    # The Security Center now offers password management instead of support.
    client.force_login(confirmed_customer)
    page = client.get(reverse("accounts:security")).content.decode()
    assert CONTACT_SUPPORT not in page
    assert reverse("accounts:password_change") in page


# --- Managing a pending request ----------------------------------------------

NO_PENDING = "You have no pending email change."


def flashed(response):
    return [str(m) for m in response.context["messages"]]


@pytest.fixture
def unusable_customer(customer):
    customer.set_unusable_password()
    customer.save()
    return customer


def test_overview_shows_pending_address_with_link_sent(client, customer):
    customer.request_email_change("new@example.com")
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "new@example.com" in page
    assert "Link sent" in page
    assert "Link expired" not in page
    assert reverse("accounts:email_resend") in page
    assert reverse("accounts:email_cancel") in page


def test_overview_shows_link_expired_after_24_hours(client, customer):
    customer.request_email_change("new@example.com")
    get_user_model().objects.filter(pk=customer.pk).update(
        email_link_sent_at=timezone.now() - EMAIL_LINK_LIFETIME - timedelta(seconds=1)
    )
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "new@example.com" in page
    assert "Link expired" in page
    assert "Link sent" not in page


def test_overview_hides_pending_block_without_a_request(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "Waiting for confirmation" not in page
    assert reverse("accounts:email_resend") not in page
    assert reverse("accounts:email_cancel") not in page


def test_resend_sends_new_link_and_retires_the_old_one(client, customer, mailoutbox):
    client.force_login(customer)
    request_change(client, "new@example.com")

    response = client.post(reverse("accounts:email_resend"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    assert any("We sent a new confirmation link" in m for m in flashed(response))
    assert len(mailoutbox) == 2
    assert mailoutbox[1].to == ["new@example.com"]
    old_link, new_link = (confirm_path(m) for m in mailoutbox)
    assert LINK_INVALID in client.get(old_link).content.decode()
    client.get(new_link)
    customer.refresh_from_db()
    assert customer.email == "new@example.com"


def test_resend_revives_an_expired_request(client, customer, mailoutbox):
    customer.request_email_change("new@example.com")
    get_user_model().objects.filter(pk=customer.pk).update(
        email_link_sent_at=timezone.now() - EMAIL_LINK_LIFETIME - timedelta(seconds=1)
    )
    client.force_login(customer)

    client.post(reverse("accounts:email_resend"))
    client.get(confirm_path(mailoutbox[0]))

    customer.refresh_from_db()
    assert customer.email == "new@example.com"


def test_cancel_clears_request_and_retires_the_link(
    client, confirmed_customer, mailoutbox
):
    client.force_login(confirmed_customer)
    request_change(client, "new@example.com")

    response = client.post(reverse("accounts:email_cancel"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    assert any("Canceled the change to new@example.com" in m for m in flashed(response))
    assert len(mailoutbox) == 1
    confirmed_customer.refresh_from_db()
    assert confirmed_customer.pending_email == ""
    assert confirmed_customer.email == "customer@example.com"
    assert LINK_INVALID in client.get(confirm_path(mailoutbox[0])).content.decode()
    confirmed_customer.refresh_from_db()
    assert confirmed_customer.email == "customer@example.com"


@pytest.mark.parametrize("name", ["accounts:email_resend", "accounts:email_cancel"])
def test_pending_actions_reject_get(client, customer, name):
    customer.request_email_change("new@example.com")
    client.force_login(customer)

    response = client.get(reverse(name))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    customer.refresh_from_db()
    assert customer.pending_email == "new@example.com"


@pytest.mark.parametrize("name", ["accounts:email_resend", "accounts:email_cancel"])
def test_pending_actions_require_sign_in(client, db, mailoutbox, name):
    url = reverse(name)

    response = client.post(url)

    assert response.url == f"{reverse('accounts:login')}?next={url}"
    assert mailoutbox == []


@pytest.mark.parametrize("name", ["accounts:email_resend", "accounts:email_cancel"])
def test_pending_actions_without_a_request_are_harmless(
    client, confirmed_customer, mailoutbox, name
):
    client.force_login(confirmed_customer)

    response = client.post(reverse(name), follow=True)

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    assert NO_PENDING in flashed(response)
    assert mailoutbox == []
    confirmed_customer.refresh_from_db()
    assert confirmed_customer.email == "customer@example.com"


def test_unusable_password_user_can_resend_and_confirm(
    client, unusable_customer, mailoutbox
):
    unusable_customer.request_email_change("new@example.com")
    client.force_login(unusable_customer)

    response = client.post(reverse("accounts:email_resend"), follow=True)
    client.get(confirm_path(mailoutbox[0]))

    assert any("We sent a new confirmation link" in m for m in flashed(response))
    unusable_customer.refresh_from_db()
    assert unusable_customer.email == "new@example.com"


def test_unusable_password_user_can_cancel(client, unusable_customer):
    unusable_customer.request_email_change("new@example.com")
    client.force_login(unusable_customer)

    response = client.post(reverse("accounts:email_cancel"), follow=True)

    assert any("Canceled the change" in m for m in flashed(response))
    unusable_customer.refresh_from_db()
    assert unusable_customer.pending_email == ""


# --- Confirmation-email rate limit -------------------------------------------

LIMIT_MESSAGE = (
    "You've requested several confirmation emails. "
    "Please wait before requesting another."
)


def at(moment):
    """Freeze ``timezone.now()`` at ``moment`` (it is patched project-wide)."""
    return mock.patch("django.utils.timezone.now", return_value=moment)


@pytest.fixture
def window():
    return RateLimit("test", limit=3, window=timedelta(hours=1))


def test_rate_limit_allows_up_to_the_limit(window):
    window.hit("key")
    window.hit("key")
    assert not window.is_limited("key")

    window.hit("key")

    assert window.is_limited("key")


def test_rate_limit_window_starts_with_the_first_event(window):
    start = timezone.now()
    with at(start):
        window.hit("key")
    with at(start + timedelta(minutes=50)):
        window.hit("key")
    with at(start + timedelta(minutes=59)):
        window.hit("key")
        assert window.is_limited("key")

    # Sixty minutes after the *first* event, not the last, the key is free.
    with at(start + timedelta(minutes=60)):
        assert not window.is_limited("key")


def test_rate_limit_opens_a_fresh_window_after_expiry(window):
    start = timezone.now()
    with at(start):
        for _ in range(3):
            window.hit("key")

    with at(start + timedelta(minutes=61)):
        window.hit("key")
        window.hit("key")
        assert not window.is_limited("key")
        window.hit("key")
        assert window.is_limited("key")


def test_rate_limit_keys_are_independent(window):
    for _ in range(3):
        window.hit("one")

    assert window.is_limited("one")
    assert not window.is_limited("two")


@pytest.mark.parametrize("run", [1, 2])
def test_rate_limit_counters_do_not_leak_between_tests(window, run):
    # The second run would start limited if the first run's counts leaked.
    assert not window.is_limited("leak")
    for _ in range(3):
        window.hit("leak")
    assert window.is_limited("leak")


@pytest.fixture
def spent_customer(client, customer, mailoutbox):
    """A signed-in customer who has sent all three confirmation emails:
    one request and two resends, all for first@example.com."""
    client.force_login(customer)
    request_change(client, "first@example.com")
    client.post(reverse("accounts:email_resend"))
    client.post(reverse("accounts:email_resend"))
    assert len(mailoutbox) == 3
    return customer


def test_signup_email_counts_toward_the_budget(client, db, mailoutbox):
    signup(client)
    client.login(username="fresh-thinker", password="neural-implant-9000")
    client.post(reverse("accounts:email_resend"))
    client.post(reverse("accounts:email_resend"))
    assert len(mailoutbox) == 3

    response = client.post(reverse("accounts:email_resend"), follow=True)

    assert LIMIT_MESSAGE in flashed(response)
    assert len(mailoutbox) == 3


def test_three_new_addresses_spend_the_budget(client, customer, mailoutbox):
    client.force_login(customer)
    for address in ["a@example.com", "b@example.com", "c@example.com"]:
        request_change(client, address)
    assert len(mailoutbox) == 3

    response = request_change(client, "d@example.com")

    assert response.status_code == HTTPStatus.OK
    assert LIMIT_MESSAGE in response.context["form"].non_field_errors()
    assert len(mailoutbox) == 3
    customer.refresh_from_db()
    assert customer.pending_email == "c@example.com"


def test_resend_is_refused_once_the_budget_is_spent(client, spent_customer, mailoutbox):
    response = client.post(reverse("accounts:email_resend"), follow=True)

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    assert LIMIT_MESSAGE in flashed(response)
    assert len(mailoutbox) == 3
    # The pending address and Cancel stay available on the overview.
    page = response.content.decode()
    assert "first@example.com" in page
    assert reverse("accounts:email_cancel") in page


def test_refused_request_leaves_the_pending_request_and_its_link(
    client, spent_customer, mailoutbox
):
    request_change(client, "second@example.com")

    assert len(mailoutbox) == 3
    spent_customer.refresh_from_db()
    assert spent_customer.pending_email == "first@example.com"
    client.get(confirm_path(mailoutbox[-1]))
    spent_customer.refresh_from_db()
    assert spent_customer.email == "first@example.com"


def test_cancel_still_works_once_the_budget_is_spent(client, spent_customer):
    response = client.post(reverse("accounts:email_cancel"), follow=True)

    assert any("Canceled the change" in m for m in flashed(response))
    spent_customer.refresh_from_db()
    assert spent_customer.pending_email == ""


def test_budget_returns_after_the_window(client, customer, mailoutbox):
    start = timezone.now()
    client.force_login(customer)
    with at(start):
        request_change(client, "first@example.com")
        client.post(reverse("accounts:email_resend"))
        client.post(reverse("accounts:email_resend"))
    with at(start + timedelta(minutes=59)):
        request_change(client, "second@example.com")
        assert len(mailoutbox) == 3

    with at(start + timedelta(minutes=60)):
        request_change(client, "second@example.com")

    assert len(mailoutbox) == 4
    assert mailoutbox[-1].to == ["second@example.com"]
    customer.refresh_from_db()
    assert customer.pending_email == "second@example.com"


def test_budgets_are_per_account(client, spent_customer, other_customer, mailoutbox):
    client.force_login(other_customer)

    request_change(client, "elsewhere@example.com", password="other123")

    assert len(mailoutbox) == 4
    other_customer.refresh_from_db()
    assert other_customer.pending_email == "elsewhere@example.com"


# --- Forgotten-password reset ------------------------------------------------

RESET_SENT = "If an account exists for that address, we've sent a reset link."
RESET_LINK_INVALID = "This password reset link is no longer valid."
NEW_PASSWORD = "fresh-synapse-2026"


def reset_path(message):
    """The reset link's path, read out of a sent email."""
    match = re.search(
        r"https?://[^/\s]+(/accounts/password-reset/[^/\s]+/[^/\s]+/)", message.body
    )
    assert match, message.body
    return match.group(1)


def request_reset(client, email):
    return client.post(
        reverse("accounts:password_reset"), {"email": email}, follow=True
    )


def without_csrf(page):
    """The page with its per-request CSRF tokens blanked out."""
    return re.sub(r'(csrfmiddlewaretoken" value="|"X-CSRFToken": ")[^"]+', r"\1", page)


def set_new_password(client, path, password=NEW_PASSWORD):
    """Open a reset link, then submit a new password on the form it leads to."""
    form_path = client.get(path, follow=True).redirect_chain[-1][0]
    return client.post(
        form_path,
        {"new_password1": password, "new_password2": password},
        follow=True,
    )


def reset_tokens_at(moment):
    """Run Django's reset-token clock at ``moment``."""
    return mock.patch(
        "django.contrib.auth.tokens.PasswordResetTokenGenerator._now",
        return_value=moment,
    )


def test_login_page_links_to_password_reset(client, db):
    page = client.get(reverse("accounts:login")).content.decode()

    assert reverse("accounts:password_reset") in page
    assert "Forgot password?" in page


@pytest.mark.parametrize(
    "name", ["accounts:password_reset", "accounts:password_reset_done"]
)
def test_password_reset_pages_are_public(client, db, name):
    assert client.get(reverse(name)).status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    "email", ["customer@example.com", "CUSTOMER@Example.COM", "Customer@example.com"]
)
def test_reset_sends_one_email_to_the_confirmed_address(
    client, confirmed_customer, mailoutbox, email
):
    response = request_reset(client, email)

    assert response.redirect_chain[-1][0] == reverse("accounts:password_reset_done")
    assert RESET_SENT in response.content.decode()
    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["customer@example.com"]
    reset_path(mailoutbox[0])


def make_unknown(customer):
    return "nobody@example.com"


def make_pending_only(customer):
    customer.request_email_change("pending@example.com")
    return "pending@example.com"


def make_inactive(customer):
    customer.email = "customer@example.com"
    customer.is_active = False
    customer.save()
    return "customer@example.com"


def make_unusable(customer):
    customer.email = "customer@example.com"
    customer.set_unusable_password()
    customer.save()
    return "customer@example.com"


@pytest.mark.parametrize(
    "setup", [make_unknown, make_pending_only, make_inactive, make_unusable]
)
def test_reset_reveals_nothing_and_sends_nothing(client, customer, mailoutbox, setup):
    email = setup(customer)
    baseline = request_reset(client, "never-registered@example.com")

    response = request_reset(client, email)

    assert response.redirect_chain == baseline.redirect_chain
    page = without_csrf(response.content.decode())
    assert page == without_csrf(baseline.content.decode())
    assert RESET_SENT in page
    assert mailoutbox == []


def test_reset_page_says_to_check_spam_and_the_address(client, db):
    page = request_reset(client, "nobody@example.com").content.decode()

    assert "spam folder" in page
    assert "double-check" in page


def test_reset_link_sets_a_new_password_without_the_old_one(
    client, confirmed_customer, mailoutbox
):
    request_reset(client, "customer@example.com")

    set_new_password(client, reset_path(mailoutbox[0]))

    confirmed_customer.refresh_from_db()
    assert confirmed_customer.check_password(NEW_PASSWORD)


@pytest.mark.parametrize("weak", ["12345678", "password", "short"])
def test_reset_rejects_weak_passwords(client, confirmed_customer, mailoutbox, weak):
    request_reset(client, "customer@example.com")

    response = set_new_password(client, reset_path(mailoutbox[0]), password=weak)

    assert response.context["form"].errors["new_password2"]
    confirmed_customer.refresh_from_db()
    assert confirmed_customer.check_password("customer123")


def test_after_reset_user_signs_in_again_with_the_new_password(
    client, confirmed_customer, mailoutbox
):
    request_reset(client, "customer@example.com")

    response = set_new_password(client, reset_path(mailoutbox[0]))

    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert (
        "Your password has been reset. Please sign in with your new password."
        in flashed(response)
    )
    assert not response.context["user"].is_authenticated
    assert client.login(username="customer", password=NEW_PASSWORD)


def test_reset_signs_out_existing_sessions(client, confirmed_customer, mailoutbox):
    elsewhere = Client()
    elsewhere.force_login(confirmed_customer)
    assert elsewhere.get(reverse("accounts:security")).status_code == HTTPStatus.OK
    request_reset(client, "customer@example.com")

    set_new_password(client, reset_path(mailoutbox[0]))

    response = elsewhere.get(reverse("accounts:security"))
    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("accounts:login"))


def test_reset_sends_a_notice_to_the_confirmed_address(
    client, confirmed_customer, mailoutbox
):
    request_reset(client, "customer@example.com")

    set_new_password(client, reset_path(mailoutbox[0]))

    assert len(mailoutbox) == 2
    notice = mailoutbox[1]
    assert notice.to == ["customer@example.com"]
    assert "password was reset" in notice.subject
    assert f"http://testserver{reverse('accounts:password_reset')}" in notice.body


def test_used_reset_link_shows_the_invalid_page(client, confirmed_customer, mailoutbox):
    request_reset(client, "customer@example.com")
    path = reset_path(mailoutbox[0])
    set_new_password(client, path)

    page = client.get(path, follow=True).content.decode()

    assert RESET_LINK_INVALID in page
    assert reverse("accounts:password_reset") in page


def test_reset_link_older_than_an_hour_shows_the_invalid_page(
    client, confirmed_customer, mailoutbox
):
    start = datetime.now()
    with reset_tokens_at(start):
        request_reset(client, "customer@example.com")

    with reset_tokens_at(start + timedelta(hours=1, seconds=1)):
        page = client.get(reset_path(mailoutbox[0]), follow=True).content.decode()

    assert RESET_LINK_INVALID in page
    assert reverse("accounts:password_reset") in page


def test_reset_link_just_under_an_hour_still_works(
    client, confirmed_customer, mailoutbox
):
    start = datetime.now()
    with reset_tokens_at(start):
        request_reset(client, "customer@example.com")

    with reset_tokens_at(start + timedelta(minutes=59)):
        set_new_password(client, reset_path(mailoutbox[0]))

    confirmed_customer.refresh_from_db()
    assert confirmed_customer.check_password(NEW_PASSWORD)


def test_tampered_reset_link_shows_the_invalid_page(client, confirmed_customer):
    url = reverse(
        "accounts:password_reset_confirm",
        kwargs={"uidb64": "MQ", "token": "bad-token"},
    )

    page = client.get(url, follow=True).content.decode()

    assert RESET_LINK_INVALID in page


# --- Password change ---------------------------------------------------------

PASSWORD_CHANGED = (
    "Your password has been changed. Your other browsers were signed out."
)


def change_password(client, old="customer123", new1=NEW_PASSWORD, new2=None):
    return client.post(
        reverse("accounts:password_change"),
        {
            "old_password": old,
            "new_password1": new1,
            "new_password2": new1 if new2 is None else new2,
        },
        follow=True,
    )


def test_security_page_offers_change_password(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "Change password" in page
    assert reverse("accounts:password_change") in page


def test_security_page_hides_change_password_for_unusable_password(
    client, unusable_customer
):
    client.force_login(unusable_customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "Change password" not in page
    assert reverse("accounts:password_change") not in page


def test_password_change_page_requires_sign_in(client, db):
    url = reverse("accounts:password_change")

    response = client.get(url)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == f"{reverse('accounts:login')}?next={url}"


def test_password_change_page_returns_200(client, customer):
    client.force_login(customer)

    assert client.get(reverse("accounts:password_change")).status_code == HTTPStatus.OK


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"old": "wrong-password"}, "old_password"),
        ({"new2": "something-else-2026"}, "new_password2"),
        ({"new1": "12345678"}, "new_password2"),
        ({"new1": "password"}, "new_password2"),
        ({"new1": "short"}, "new_password2"),
    ],
)
def test_password_change_form_errors(
    client, confirmed_customer, mailoutbox, data, field
):
    client.force_login(confirmed_customer)

    response = change_password(client, **data)

    assert response.context["form"].errors[field]
    confirmed_customer.refresh_from_db()
    assert confirmed_customer.check_password("customer123")
    assert mailoutbox == []


def test_password_change_keeps_this_browser_signed_in(client, customer):
    client.force_login(customer)

    response = change_password(client)

    assert response.redirect_chain[-1][0] == reverse("accounts:security")
    assert PASSWORD_CHANGED in flashed(response)
    assert response.context["user"] == customer
    customer.refresh_from_db()
    assert customer.check_password(NEW_PASSWORD)
    assert client.get(reverse("accounts:security")).status_code == HTTPStatus.OK


def test_password_change_signs_out_other_sessions(client, customer):
    elsewhere = Client()
    elsewhere.force_login(customer)
    assert elsewhere.get(reverse("accounts:security")).status_code == HTTPStatus.OK
    client.force_login(customer)

    change_password(client)

    response = elsewhere.get(reverse("accounts:security"))
    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("accounts:login"))


def test_password_change_sends_notice_with_reset_link(
    client, confirmed_customer, mailoutbox
):
    client.force_login(confirmed_customer)

    change_password(client)

    assert len(mailoutbox) == 1
    notice = mailoutbox[0]
    assert notice.to == ["customer@example.com"]
    assert "password was changed" in notice.subject
    assert f"http://testserver{reverse('accounts:password_reset')}" in notice.body


def test_password_change_notice_skips_pending_and_missing_email(
    client, customer, mailoutbox
):
    customer.request_email_change("pending@example.com")
    mailoutbox.clear()
    client.force_login(customer)

    change_password(client)

    assert mailoutbox == []


@pytest.mark.parametrize("method", ["get", "post"])
def test_unusable_password_user_is_sent_back_from_password_change(
    client, unusable_customer, method
):
    client.force_login(unusable_customer)

    response = getattr(client, method)(reverse("accounts:password_change"), follow=True)

    assert response.redirect_chain == [(reverse("accounts:security"), HTTPStatus.FOUND)]
    assert any(CONTACT_SUPPORT in m for m in flashed(response))


# --- Sign-in and reset-request throttling ------------------------------------

SIGN_IN_LIMITED = "Too many failed sign-in attempts. Try again in 15 minutes."


def sign_in(client, username="customer", password="customer123"):
    return client.post(
        reverse("accounts:login"), {"username": username, "password": password}
    )


def fail_sign_ins(client, times, username="customer"):
    for _ in range(times):
        response = sign_in(client, username=username, password="wrong-guess")
        assert response.status_code == HTTPStatus.OK
        assert SIGN_IN_LIMITED not in response.context["form"].non_field_errors()


def is_signed_in(client):
    return client.get(reverse("accounts:security")).status_code == HTTPStatus.OK


def test_rate_limit_cooldown_runs_from_the_event_that_hits_the_limit():
    lock = RateLimit(
        "test", limit=2, window=timedelta(minutes=15), cooldown=timedelta(minutes=15)
    )
    start = timezone.now()
    with at(start):
        lock.hit("key")
    with at(start + timedelta(minutes=14)):
        lock.hit("key")

    # The window alone would close at minute 15; the cooldown holds to 29.
    with at(start + timedelta(minutes=28, seconds=59)):
        assert lock.is_limited("key")
    with at(start + timedelta(minutes=29)):
        assert not lock.is_limited("key")


def test_rate_limit_clear_forgets_the_count(window):
    for _ in range(3):
        window.hit("key")

    window.clear("key")

    assert not window.is_limited("key")


def test_five_failures_lock_the_username_even_for_the_right_password(client, customer):
    fail_sign_ins(client, 5)

    response = sign_in(client)

    assert response.status_code == HTTPStatus.OK
    assert SIGN_IN_LIMITED in response.context["form"].non_field_errors()
    assert SIGN_IN_LIMITED in response.content.decode()
    assert not is_signed_in(client)


def test_four_failures_do_not_lock(client, customer):
    fail_sign_ins(client, 4)

    response = sign_in(client)

    assert response.status_code == HTTPStatus.FOUND
    assert is_signed_in(client)


def test_unknown_username_is_throttled_the_same_way(client, db):
    fail_sign_ins(client, 5, username="nobody-here")

    response = sign_in(client, username="nobody-here")

    assert SIGN_IN_LIMITED in response.context["form"].non_field_errors()


def test_lock_ignores_username_capitalization(client, customer):
    fail_sign_ins(client, 5, username="CUSTOMER")

    response = sign_in(client)

    assert SIGN_IN_LIMITED in response.context["form"].non_field_errors()


def test_successful_sign_in_clears_the_count(client, customer):
    fail_sign_ins(client, 4)
    assert sign_in(client).status_code == HTTPStatus.FOUND
    client.logout()

    # Four more failures would have locked the username if the count stayed.
    fail_sign_ins(client, 4)
    response = sign_in(client)

    assert response.status_code == HTTPStatus.FOUND
    assert is_signed_in(client)


def test_sign_in_works_again_15_minutes_after_the_fifth_failure(client, customer):
    start = timezone.now()
    with at(start):
        fail_sign_ins(client, 1)
    with at(start + timedelta(minutes=14)):
        fail_sign_ins(client, 4)

    with at(start + timedelta(minutes=28, seconds=59)):
        response = sign_in(client)
        assert SIGN_IN_LIMITED in response.context["form"].non_field_errors()
    with at(start + timedelta(minutes=29)):
        response = sign_in(client)

    assert response.status_code == HTTPStatus.FOUND
    assert is_signed_in(client)


def test_failures_outside_the_window_do_not_add_up(client, customer):
    start = timezone.now()
    with at(start):
        fail_sign_ins(client, 4)
    with at(start + timedelta(minutes=15)):
        fail_sign_ins(client, 1)
        response = sign_in(client)

    assert response.status_code == HTTPStatus.FOUND


def test_locking_one_username_does_not_affect_another(client, customer, staff_user):
    fail_sign_ins(client, 5)

    response = sign_in(client, username="employee", password="employee123")

    assert response.status_code == HTTPStatus.FOUND
    assert is_signed_in(client)


@pytest.mark.parametrize(
    "emails",
    [
        ["customer@example.com"] * 4,
        [
            "customer@example.com",
            "CUSTOMER@example.com",
            "Customer@Example.com",
            "customer@EXAMPLE.COM",
        ],
    ],
)
def test_fourth_reset_request_sends_nothing_and_looks_the_same(
    client, confirmed_customer, mailoutbox, emails
):
    responses = [request_reset(client, email) for email in emails[:3]]
    assert len(mailoutbox) == 3

    response = request_reset(client, emails[3])

    assert len(mailoutbox) == 3
    assert response.redirect_chain == responses[0].redirect_chain
    assert without_csrf(response.content.decode()) == without_csrf(
        responses[0].content.decode()
    )
    assert RESET_SENT in response.content.decode()


def test_reset_requests_for_unknown_addresses_are_counted(client, db):
    for _ in range(3):
        request_reset(client, "nobody@example.com")

    assert reset_requests.is_limited("nobody@example.com")


def test_reset_requests_send_again_after_the_hour(
    client, confirmed_customer, mailoutbox
):
    start = timezone.now()
    with at(start):
        for _ in range(3):
            request_reset(client, "customer@example.com")
    with at(start + timedelta(minutes=59)):
        request_reset(client, "customer@example.com")
        assert len(mailoutbox) == 3

    with at(start + timedelta(minutes=60)):
        request_reset(client, "customer@example.com")

    assert len(mailoutbox) == 4


def test_reset_limit_is_per_address(client, confirmed_customer, mailoutbox):
    for _ in range(3):
        request_reset(client, "nobody@example.com")

    request_reset(client, "customer@example.com")

    assert len(mailoutbox) == 1
    assert mailoutbox[0].to == ["customer@example.com"]
