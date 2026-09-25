"""Saved addresses: the model's default rules, ``save_for``, the address
book pages, the checkout picker, and owner-only access throughout."""

from http import HTTPStatus

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.urls import reverse

from .forms import AddressForm, CheckoutForm
from .models import Address
from .test_checkout_form import VALID_DATA


@pytest.fixture
def other_customer(db):
    return get_user_model().objects.create_user(username="other", password="x")


@pytest.fixture
def office(customer, address):
    """A second address — saved after ``address``, so not the default."""
    return Address.objects.create(
        user=customer,
        name="Casey Monroe",
        street="77 Cortex Lane",
        line2="Suite 400",
        city="Amarillo",
        state="TX",
        zip="79101",
    )


@pytest.fixture
def strangers_address(other_customer):
    return Address.objects.create(
        user=other_customer,
        name="Someone Else",
        street="9 Axon Avenue",
        city="Norman",
        state="OK",
        zip="73019",
    )


def cleaned_checkout(**overrides):
    """What a valid ``CheckoutForm`` hands the view."""
    form = CheckoutForm(data={**VALID_DATA, **overrides})
    assert form.is_valid(), form.errors
    return form.cleaned_data


# --- Model rules -------------------------------------------------------------


def test_the_first_address_becomes_the_default(address):
    assert address.is_default


def test_later_addresses_are_not_the_default(address, office):
    assert not office.is_default


def test_str_is_a_short_summary(address):
    assert str(address) == "Casey Monroe — 214 Synapse Street, Canyon, TX 79015"


def test_default_comes_first_then_newest(customer, address, office):
    newest = Address.objects.create(
        user=customer,
        name="Casey Monroe",
        street="9 Axon Avenue",
        city="Norman",
        state="OK",
        zip="73019",
    )

    assert list(customer.addresses.all()) == [address, newest, office]


def test_make_default_moves_the_flag(address, office):
    office.make_default()
    address.refresh_from_db()

    assert office.is_default
    assert not address.is_default


def test_the_database_allows_only_one_default(address, office):
    office.is_default = True

    with pytest.raises(IntegrityError):
        office.save()


def test_deleting_the_default_promotes_the_newest_remaining(customer, address, office):
    address.delete()
    office.refresh_from_db()

    assert office.is_default


def test_deleting_the_last_address_leaves_no_default(customer, address):
    address.delete()

    assert not customer.addresses.exists()


def test_deleting_a_non_default_leaves_the_default_alone(address, office):
    office.delete()
    address.refresh_from_db()

    assert address.is_default


# --- save_for ----------------------------------------------------------------


def test_save_for_creates_an_address_from_a_checkout_section(customer):
    saved = Address.objects.save_for(customer, cleaned_checkout(), "shipping")

    assert saved.user == customer
    assert saved.street == "12 Cortex Lane"
    assert saved.line2 == "Unit 7"
    assert saved.zip == "79015"
    assert saved.is_default


def test_save_for_trims_whitespace(customer):
    data = {**cleaned_checkout(), "billing_city": "  Canyon  "}

    saved = Address.objects.save_for(customer, data, "billing")

    assert saved.city == "Canyon"


def test_save_for_reuses_an_exact_match(customer):
    data = cleaned_checkout()
    first = Address.objects.save_for(customer, data, "shipping")

    again = Address.objects.save_for(customer, data, "shipping")

    assert again == first
    assert customer.addresses.count() == 1


def test_the_same_address_in_both_sections_saves_once(customer):
    data = cleaned_checkout(billing_line2="Unit 7", billing_zip="79015")

    Address.objects.save_for(customer, data, "shipping")
    Address.objects.save_for(customer, data, "billing")

    assert customer.addresses.count() == 1


def test_save_for_never_reuses_another_customers_address(customer, other_customer):
    data = cleaned_checkout()
    theirs = Address.objects.save_for(other_customer, data, "shipping")

    mine = Address.objects.save_for(customer, data, "shipping")

    assert mine != theirs
    assert mine.user == customer


# --- AddressForm -------------------------------------------------------------

ADDRESS_DATA = {
    "name": "Casey Monroe",
    "street": "28 Ganglion Court",
    "line2": "",
    "city": "Denver",
    "state": "CO",
    "zip": "80202",
}


def test_a_valid_address_form_passes():
    assert AddressForm(data=ADDRESS_DATA).is_valid()


@pytest.mark.parametrize(
    ("field", "value"),
    [("state", "XX"), ("zip", "802"), ("zip", "80202-12"), ("name", "")],
)
def test_address_form_rejects_bad_input(field, value):
    form = AddressForm(data={**ADDRESS_DATA, field: value})

    assert not form.is_valid()
    assert field in form.errors


# --- My Addresses pages ------------------------------------------------------


def test_address_book_requires_login(client, db):
    response = client.get(reverse("orders:addresses"))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


def test_address_book_shows_an_empty_state(client, customer):
    client.force_login(customer)

    response = client.get(reverse("orders:addresses"))

    assert response.status_code == HTTPStatus.OK
    assert "No saved addresses yet" in response.content.decode()


def test_address_book_lists_only_my_addresses(
    client, customer, address, strangers_address
):
    client.force_login(customer)

    response = client.get(reverse("orders:addresses"))

    assert list(response.context["addresses"]) == [address]


def test_adding_an_address(client, customer):
    client.force_login(customer)

    response = client.post(reverse("orders:address_create"), ADDRESS_DATA)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("orders:addresses")
    saved = customer.addresses.get()
    assert saved.city == "Denver"
    assert saved.is_default


def test_adding_an_invalid_address_shows_errors(client, customer):
    client.force_login(customer)

    response = client.post(
        reverse("orders:address_create"), {**ADDRESS_DATA, "zip": "802"}
    )

    assert response.status_code == HTTPStatus.OK
    assert "zip" in response.context["form"].errors
    assert not customer.addresses.exists()


def test_editing_an_address(client, customer, address):
    client.force_login(customer)

    response = client.post(
        reverse("orders:address_update", args=[address.pk]),
        {**ADDRESS_DATA, "city": "Boulder", "zip": "80302"},
    )

    assert response.status_code == HTTPStatus.FOUND
    address.refresh_from_db()
    assert address.city == "Boulder"


def test_deleting_an_address_asks_first(client, customer, address):
    client.force_login(customer)

    response = client.get(reverse("orders:address_delete", args=[address.pk]))

    assert response.status_code == HTTPStatus.OK
    assert "Delete this address?" in response.content.decode()


def test_deleting_the_default_through_the_page_promotes_another(
    client, customer, address, office
):
    client.force_login(customer)

    response = client.post(reverse("orders:address_delete", args=[address.pk]))

    assert response.status_code == HTTPStatus.FOUND
    assert list(customer.addresses.all()) == [office]
    office.refresh_from_db()
    assert office.is_default


def test_make_default_through_the_page(client, customer, address, office):
    client.force_login(customer)

    response = client.post(reverse("orders:address_make_default", args=[office.pk]))

    assert response.status_code == HTTPStatus.FOUND
    office.refresh_from_db()
    assert office.is_default


def test_make_default_is_post_only(client, customer, address):
    client.force_login(customer)

    response = client.get(reverse("orders:address_make_default", args=[address.pk]))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


@pytest.mark.parametrize(
    ("name", "method"),
    [
        ("orders:address_update", "get"),
        ("orders:address_update", "post"),
        ("orders:address_delete", "get"),
        ("orders:address_delete", "post"),
        ("orders:address_make_default", "post"),
    ],
)
def test_another_customers_address_is_a_404(
    client, customer, strangers_address, name, method
):
    client.force_login(customer)

    response = getattr(client, method)(
        reverse(name, args=[strangers_address.pk]), ADDRESS_DATA
    )

    assert response.status_code == HTTPStatus.NOT_FOUND
    strangers_address.refresh_from_db()
    assert strangers_address.city == "Norman"


# --- Checkout ----------------------------------------------------------------


def test_checkout_prefills_both_sections_from_the_default(
    client, customer, cart_item, address, office
):
    client.force_login(customer)

    form = client.get(reverse("orders:checkout")).context["form"]

    assert form["shipping_street"].value() == "214 Synapse Street"
    assert form["billing_street"].value() == "214 Synapse Street"
    assert form["billing_zip"].value() == "79015"


def test_checkout_save_boxes_start_ticked_for_a_first_timer(
    client, customer, cart_item
):
    client.force_login(customer)

    form = client.get(reverse("orders:checkout")).context["form"]

    assert form["save_shipping_address"].value() is True
    assert form["save_billing_address"].value() is True
    assert form["shipping_street"].value() is None


def test_checkout_save_boxes_start_unticked_for_a_returning_customer(
    client, customer, cart_item, address
):
    client.force_login(customer)

    form = client.get(reverse("orders:checkout")).context["form"]

    assert form["save_shipping_address"].value() is False
    assert form["save_billing_address"].value() is False


def test_checkout_hides_the_picker_with_no_saved_addresses(client, customer, cart_item):
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    assert "Use a saved address" not in response.content.decode()


def test_checkout_offers_the_picker_with_saved_addresses(
    client, customer, cart_item, address
):
    client.force_login(customer)

    response = client.get(reverse("orders:checkout"))

    assert "Use a saved address" in response.content.decode()


def test_placing_an_order_saves_ticked_sections(client, customer, cart_item):
    client.force_login(customer)

    response = client.post(
        reverse("orders:checkout"),
        {**VALID_DATA, "save_shipping_address": "on", "save_billing_address": "on"},
    )

    assert response.status_code == HTTPStatus.FOUND
    # Shipping and billing differ in line2 and ZIP, so both are saved.
    assert customer.addresses.count() == 2
    assert customer.orders.count() == 1


def test_placing_an_order_saves_nothing_unticked(client, customer, cart_item):
    client.force_login(customer)

    client.post(reverse("orders:checkout"), VALID_DATA)

    assert customer.orders.count() == 1
    assert not customer.addresses.exists()


def test_editing_a_saved_address_never_changes_a_placed_order(
    client, customer, cart_item
):
    client.force_login(customer)
    client.post(
        reverse("orders:checkout"), {**VALID_DATA, "save_shipping_address": "on"}
    )

    saved = customer.addresses.get()
    saved.street = "1 Somewhere Else"
    saved.save()

    assert customer.orders.get().shipping_street == "12 Cortex Lane"


# --- The checkout picker (HTMX) ----------------------------------------------


def picker_url(section, address):
    url = reverse("orders:checkout_address_fields", args=[section])
    return f"{url}?address={address.pk}"


def test_picker_returns_a_filled_partial_for_the_section(client, customer, office):
    client.force_login(customer)

    response = client.get(picker_url("billing", office))
    html = response.content.decode()

    assert response.status_code == HTTPStatus.OK
    assert "<html" not in html
    assert 'name="billing_street"' in html
    assert 'value="77 Cortex Lane"' in html
    assert 'value="Suite 400"' in html
    assert 'name="shipping_street"' not in html


def test_picker_rejects_another_customers_address(client, customer, strangers_address):
    client.force_login(customer)

    response = client.get(picker_url("shipping", strangers_address))

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize("query", ["", "?address=", "?address=abc"])
def test_picker_rejects_a_missing_or_malformed_pk(client, customer, query):
    client.force_login(customer)
    url = reverse("orders:checkout_address_fields", args=["shipping"])

    response = client.get(url + query)

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_picker_rejects_an_unknown_section(client, customer, address):
    client.force_login(customer)

    response = client.get(picker_url("card", address))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_picker_requires_login(client, address):
    response = client.get(picker_url("shipping", address))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
