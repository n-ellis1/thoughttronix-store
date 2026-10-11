from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

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


def test_security_page_has_no_action_controls_yet(client, customer):
    client.force_login(customer)

    page = client.get(reverse("accounts:security")).content.decode()

    for label in ("Add email", "Change email", "Change password"):
        assert label not in page
