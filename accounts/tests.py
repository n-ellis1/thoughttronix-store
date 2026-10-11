import re
from datetime import timedelta
from http import HTTPStatus
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from accounts.models import EMAIL_LINK_LIFETIME, EmailAlreadyConfirmed

# --- Signup -----------------------------------------------------------------


def test_signup_page_returns_200(client, db):
    response = client.get(reverse("accounts:signup"))

    assert response.status_code == HTTPStatus.OK


def test_signup_creates_plain_customer(client, db):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "fresh-thinker",
            "password1": "neural-implant-9000",
            "password2": "neural-implant-9000",
        },
        follow=True,
    )

    user = get_user_model().objects.get(username="fresh-thinker")
    assert not user.is_staff
    assert not user.is_superuser

    # Signup hands off to the login page with a confirmation message;
    # auto-login is a student exercise, so the visitor is still anonymous.
    assert response.redirect_chain[-1][0] == reverse("accounts:login")
    assert "Account created" in response.content.decode()
    assert not response.context["user"].is_authenticated


def test_signup_password_mismatch_shows_field_error(client, db):
    response = client.post(
        reverse("accounts:signup"),
        {
            "username": "fresh-thinker",
            "password1": "neural-implant-9000",
            "password2": "neural-implant-9001",
        },
    )

    assert response.status_code == HTTPStatus.OK
    assert response.context["form"].errors["password2"]
    assert not get_user_model().objects.filter(username="fresh-thinker").exists()


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


def test_security_page_has_no_change_password_control_yet(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    assert "Change password" not in page


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
