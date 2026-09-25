"""Discount codes: pricing rules, checkout, saved order amounts, back office.

Fixtures from conftest: ``cart_item`` is 2 × Seraphine Home Hub
($349.99 each, $699.98), ``whole_order_code`` is THOUGHTS10 (10% off
the whole order), ``product_code`` is SERAPHINE25 ($25 off the hub only).
"""

import html
from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus

import pytest
from django.db import IntegrityError
from django.urls import reverse
from django.utils import timezone

from products.models import Product

from .forms import DiscountCodeForm
from .models import CartItem, DiscountCode, InvalidDiscountCode, Order
from .services import place_order
from .test_checkout_form import VALID_DATA

UNKNOWN = "We don't recognize that code."
RETIRED = "This code is no longer available."
NOT_APPLICABLE = "This code doesn't apply to anything in your cart."


def page(response):
    """The response body with HTML escapes undone (``don&#x27;t``)."""
    return html.unescape(response.content.decode())


def expired_message(date):
    return f"This code expired on {date:%B} {date.day}, {date.year}."


@pytest.fixture
def yesterday():
    return timezone.localdate() - timedelta(days=1)


@pytest.fixture
def expired_code(db, yesterday):
    return DiscountCode.objects.create(
        code="SUMMER-THOUGHTS", value=Decimal("15"), expires_on=yesterday
    )


@pytest.fixture
def retired_code(db):
    return DiscountCode.objects.create(
        code="LAUNCH-DAY",
        kind=DiscountCode.Kind.FIXED,
        value=Decimal("50.00"),
        is_active=False,
    )


@pytest.fixture
def lamp_line(cart, featured_product):
    """A second cart line: 1 × Oracle Desk Lamp at $89.00."""
    return CartItem.objects.create(cart=cart, product=featured_product, quantity=1)


def quote(code_text, cart):
    return DiscountCode.objects.quote(code_text, cart.lines())


# --- Codes: matching and uniqueness -----------------------------------------


def test_codes_are_stored_uppercase_and_matched_ignoring_case_and_spaces(
    cart, cart_item
):
    DiscountCode.objects.create(code="thoughts10", value=Decimal("10"))

    code, amount = quote("  Thoughts10 ", cart)

    assert code.code == "THOUGHTS10"
    assert amount == Decimal("70.00")


def test_a_code_name_stays_unique_even_after_retirement(retired_code):
    with pytest.raises(IntegrityError):
        DiscountCode.objects.create(code="launch-day", value=Decimal("5"))


def test_an_unknown_code_is_rejected(cart, cart_item):
    with pytest.raises(InvalidDiscountCode, match=UNKNOWN):
        quote("NOPE", cart)


# --- Pricing ------------------------------------------------------------------


def test_a_percent_code_discounts_the_whole_order(cart, cart_item, whole_order_code):
    _, amount = quote("THOUGHTS10", cart)

    assert amount == Decimal("70.00")  # 10% of 699.98 = 69.998, rounded to cents


def test_percent_discounts_round_half_up_to_the_cent(cart, category):
    cheap = Product.objects.create(
        name="Thought Sticker", slug="thought-sticker", price="0.25", category=category
    )
    cart.add(cheap)
    DiscountCode.objects.create(code="TENOFF", value=Decimal("10"))

    _, amount = quote("TENOFF", cart)

    assert amount == Decimal("0.03")  # 0.025 rounds up, not to even


def test_a_fixed_code_is_capped_at_what_it_applies_to(cart, lamp_line):
    DiscountCode.objects.create(
        code="BIG100", kind=DiscountCode.Kind.FIXED, value=Decimal("100.00")
    )

    _, amount = quote("BIG100", cart)

    assert amount == Decimal("89.00")  # the cart holds only the $89 lamp


def test_a_product_code_discounts_only_its_products(
    cart, cart_item, lamp_line, featured_product
):
    lamp_code = DiscountCode.objects.create(
        code="LAMP10", value=Decimal("10"), scope=DiscountCode.Scope.PRODUCTS
    )
    lamp_code.products.add(featured_product)

    _, amount = quote("LAMP10", cart)

    assert amount == Decimal("8.90")  # 10% of the $89 lamp; the hubs don't count


def test_a_fixed_product_code_applies_once_not_per_unit(
    cart, cart_item, lamp_line, product_code
):
    _, amount = quote("SERAPHINE25", cart)

    assert amount == Decimal("25.00")  # two hubs in the cart, one $25 discount


def test_a_product_code_with_none_of_its_products_is_rejected(
    cart, lamp_line, product_code
):
    with pytest.raises(InvalidDiscountCode, match=NOT_APPLICABLE):
        quote("SERAPHINE25", cart)


# --- Expiry and retirement ----------------------------------------------------


def test_an_expired_code_is_rejected_with_its_date(
    cart, cart_item, expired_code, yesterday
):
    with pytest.raises(InvalidDiscountCode) as excinfo:
        quote("SUMMER-THOUGHTS", cart)

    assert str(excinfo.value) == expired_message(yesterday)


def test_a_code_still_works_on_its_expiry_date(cart, cart_item, whole_order_code):
    whole_order_code.expires_on = timezone.localdate()
    whole_order_code.save()

    _, amount = quote("THOUGHTS10", cart)

    assert amount == Decimal("70.00")


def test_a_retired_code_is_rejected(cart, cart_item, retired_code):
    with pytest.raises(InvalidDiscountCode, match=RETIRED):
        quote("LAUNCH-DAY", cart)


def test_retired_outranks_expired_and_expired_outranks_not_applicable(
    cart, lamp_line, product_code, yesterday
):
    product_code.expires_on = yesterday
    product_code.save()
    with pytest.raises(InvalidDiscountCode) as excinfo:
        quote("SERAPHINE25", cart)
    assert str(excinfo.value) == expired_message(yesterday)

    product_code.retire()
    with pytest.raises(InvalidDiscountCode, match=RETIRED):
        quote("SERAPHINE25", cart)


def test_status_reflects_retirement_then_expiry(
    whole_order_code, expired_code, retired_code
):
    assert whole_order_code.status == "Active"
    assert expired_code.status == "Expired"
    retired_code.expires_on = expired_code.expires_on
    assert retired_code.status == "Retired"


# --- place_order and saved order amounts --------------------------------------


def test_place_order_saves_the_discount_on_the_order(cart, cart_item, whole_order_code):
    order = place_order(cart, cart.user, dict(VALID_DATA), coupon_code=" thoughts10")

    assert order.subtotal == Decimal("699.98")
    assert order.discount_amount == Decimal("70.00")
    assert order.total == Decimal("629.98")
    assert order.coupon_code == "THOUGHTS10"
    assert order.discount_code == whole_order_code


@pytest.mark.parametrize("code_fixture", ["expired_code", "retired_code"])
def test_place_order_rejects_a_bad_code_and_changes_nothing(
    request, cart, cart_item, code_fixture
):
    code = request.getfixturevalue(code_fixture)

    with pytest.raises(InvalidDiscountCode):
        place_order(cart, cart.user, dict(VALID_DATA), coupon_code=code.code)

    assert not Order.objects.exists()
    assert cart.items.count() == 1


def test_saved_order_amounts_survive_retiring_editing_and_catalog_changes(
    cart, cart_item, product_code, product
):
    order = place_order(cart, cart.user, dict(VALID_DATA), coupon_code="SERAPHINE25")

    product_code.value = Decimal("99.00")
    product_code.save()
    product_code.retire()
    product.price = Decimal("1.00")
    product.save()

    order.refresh_from_db()
    assert order.subtotal == Decimal("699.98")
    assert order.discount_amount == Decimal("25.00")
    assert order.total == Decimal("674.98")
    assert order.coupon_code == "SERAPHINE25"


def test_deleting_a_code_keeps_the_orders_saved_text_and_amounts(
    cart, cart_item, whole_order_code
):
    order = place_order(cart, cart.user, dict(VALID_DATA), coupon_code="THOUGHTS10")

    whole_order_code.delete()

    order.refresh_from_db()
    assert order.discount_code is None
    assert order.coupon_code == "THOUGHTS10"
    assert order.total == Decimal("629.98")


# --- Checkout: the preview and placing the order ------------------------------


def test_applying_a_code_previews_the_discounted_total(
    client, customer, cart_item, whole_order_code
):
    client.force_login(customer)

    response = client.post(
        reverse("orders:checkout_summary"), {"coupon_code": "thoughts10"}
    )

    body = page(response)
    assert response.status_code == HTTPStatus.OK
    assert "THOUGHTS10 applied." in body
    assert "−$70.00" in body
    assert "$629.98" in body
    assert 'id="place-order-total" hx-swap-oob="true"' in body
    assert 'value="THOUGHTS10"' in body  # the hidden input carries it to checkout
    assert "<html" not in body  # a partial, never base.html


@pytest.mark.parametrize(
    ("code_fixture", "typed", "message"),
    [
        (None, "NOPE", UNKNOWN),
        ("retired_code", "LAUNCH-DAY", RETIRED),
        ("expired_code", "SUMMER-THOUGHTS", None),  # message names the date
        ("product_code", "SERAPHINE25", NOT_APPLICABLE),
    ],
)
def test_a_rejected_code_shows_its_message_and_no_discount(
    request, client, customer, cart, lamp_line, yesterday, code_fixture, typed, message
):
    if code_fixture:
        request.getfixturevalue(code_fixture)
    client.force_login(customer)

    response = client.post(reverse("orders:checkout_summary"), {"coupon_code": typed})

    body = page(response)
    assert (message or expired_message(yesterday)) in body
    assert "Discount (" not in body
    assert "$89.00" in body  # total unchanged


def test_checkout_with_an_applied_code_places_a_discounted_order(
    client, customer, cart_item, product_code
):
    client.force_login(customer)

    response = client.post(
        reverse("orders:checkout"), {**VALID_DATA, "coupon_code": "SERAPHINE25"}
    )

    order = Order.objects.get()
    assert response.status_code == HTTPStatus.FOUND
    assert order.discount_amount == Decimal("25.00")
    assert order.total == Decimal("674.98")


def test_a_code_retired_after_applying_keeps_the_customer_on_checkout(
    client, customer, cart_item, whole_order_code
):
    client.force_login(customer)
    client.post(reverse("orders:checkout_summary"), {"coupon_code": "THOUGHTS10"})
    whole_order_code.retire()  # Marketing pulls it before the customer submits

    response = client.post(
        reverse("orders:checkout"), {**VALID_DATA, "coupon_code": "THOUGHTS10"}
    )

    body = page(response)
    assert response.status_code == HTTPStatus.OK
    assert RETIRED in body
    assert "12 Cortex Lane" in body  # everything typed is preserved
    assert not Order.objects.exists()
    assert CartItem.objects.exists()


def test_checkout_page_starts_with_the_undiscounted_total(client, customer, cart_item):
    client.force_login(customer)

    body = page(client.get(reverse("orders:checkout")))

    assert "Discount code" in body
    assert '<span id="place-order-total">$699.98</span>' in body


def test_the_preview_requires_login(client, db):
    response = client.post(reverse("orders:checkout_summary"), {"coupon_code": "X"})

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url


# --- Order pages show the saved amounts ---------------------------------------


@pytest.fixture
def discounted_order(cart, cart_item, whole_order_code):
    return place_order(cart, cart.user, dict(VALID_DATA), coupon_code="THOUGHTS10")


@pytest.mark.parametrize("url_name", ["orders:confirmation", "orders:detail"])
def test_customer_order_pages_show_subtotal_discount_and_total(
    client, customer, discounted_order, url_name
):
    client.force_login(customer)

    body = page(client.get(reverse(url_name, kwargs={"pk": discounted_order.pk})))

    assert "$699.98" in body
    assert "Discount (THOUGHTS10)" in body
    assert "−$70.00" in body
    assert "$629.98" in body


def test_back_office_order_detail_shows_the_saved_discount(
    client, staff_user, discounted_order
):
    client.force_login(staff_user)
    url = reverse("orders:manage_order_detail", kwargs={"pk": discounted_order.pk})

    body = page(client.get(url))

    assert "Discount (THOUGHTS10)" in body
    assert "$629.98" in body


# --- Back office --------------------------------------------------------------


def form_data(**overrides):
    return {
        "code": "new-code",
        "kind": "PERCENT",
        "value": "15",
        "scope": "ORDER",
        "expires_on": "",
        **overrides,
    }


def test_customers_cannot_manage_discount_codes(client, customer, whole_order_code):
    client.force_login(customer)
    pk = whole_order_code.pk
    for url in [
        reverse("orders:manage_discounts"),
        reverse("orders:manage_discount_create"),
        reverse("orders:manage_discount_update", kwargs={"pk": pk}),
        reverse("orders:manage_discount_delete", kwargs={"pk": pk}),
    ]:
        assert client.get(url).status_code == HTTPStatus.FORBIDDEN
    retire = reverse("orders:manage_discount_retire", kwargs={"pk": pk})
    assert client.post(retire).status_code == HTTPStatus.FORBIDDEN


def test_list_shows_status_and_usage(
    client, staff_user, discounted_order, expired_code, retired_code
):
    client.force_login(staff_user)

    body = page(client.get(reverse("orders:manage_discounts")))

    for text in ["THOUGHTS10", "Active", "Expired", "Retired", "1 order", "0 orders"]:
        assert text in body


def test_list_has_a_designed_empty_state(client, staff_user):
    client.force_login(staff_user)

    body = page(client.get(reverse("orders:manage_discounts")))

    assert "No discount codes yet" in body


def test_staff_can_create_a_code(client, staff_user):
    client.force_login(staff_user)

    response = client.post(reverse("orders:manage_discount_create"), form_data())

    assert response.status_code == HTTPStatus.FOUND
    code = DiscountCode.objects.get()
    assert code.code == "NEW-CODE"
    assert code.is_active


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"code": "BAD CODE!"}, "code"),
        ({"value": "0"}, "value"),
        ({"value": "101"}, "value"),
        ({"scope": "PRODUCTS"}, "products"),  # product scope with no products
    ],
)
def test_the_form_rejects_bad_codes(db, overrides, field):
    form = DiscountCodeForm(data=form_data(**overrides))

    assert not form.is_valid()
    assert field in form.errors


def test_the_form_rejects_a_duplicate_in_any_case(retired_code):
    form = DiscountCodeForm(data=form_data(code="launch-day"))

    assert not form.is_valid()
    assert "code" in form.errors


def test_a_used_codes_terms_are_locked_but_its_expiry_can_change(
    client, staff_user, discounted_order, whole_order_code
):
    client.force_login(staff_user)
    new_date = timezone.localdate() + timedelta(days=30)

    client.post(
        reverse("orders:manage_discount_update", kwargs={"pk": whole_order_code.pk}),
        form_data(code="RENAMED", value="50", expires_on=new_date.isoformat()),
    )

    whole_order_code.refresh_from_db()
    assert whole_order_code.code == "THOUGHTS10"
    assert whole_order_code.value == Decimal("10.00")
    assert whole_order_code.expires_on == new_date


def test_an_unused_code_can_be_edited_freely(client, staff_user, whole_order_code):
    client.force_login(staff_user)

    client.post(
        reverse("orders:manage_discount_update", kwargs={"pk": whole_order_code.pk}),
        form_data(code="THOUGHTS20", value="20"),
    )

    whole_order_code.refresh_from_db()
    assert whole_order_code.code == "THOUGHTS20"
    assert whole_order_code.value == Decimal("20.00")


def test_staff_can_retire_and_reactivate_with_post_only(
    client, staff_user, whole_order_code
):
    client.force_login(staff_user)
    retire = reverse(
        "orders:manage_discount_retire", kwargs={"pk": whole_order_code.pk}
    )
    reactivate = reverse(
        "orders:manage_discount_reactivate", kwargs={"pk": whole_order_code.pk}
    )

    assert client.get(retire).status_code == HTTPStatus.METHOD_NOT_ALLOWED
    client.post(retire)
    whole_order_code.refresh_from_db()
    assert not whole_order_code.is_active

    client.post(reactivate)
    whole_order_code.refresh_from_db()
    assert whole_order_code.is_active


def test_an_unused_code_can_be_deleted_after_confirmation(
    client, staff_user, whole_order_code
):
    client.force_login(staff_user)
    url = reverse("orders:manage_discount_delete", kwargs={"pk": whole_order_code.pk})

    assert "Delete THOUGHTS10?" in page(client.get(url))
    client.post(url)

    assert not DiscountCode.objects.exists()


def test_a_used_code_cannot_be_deleted(client, staff_user, discounted_order):
    client.force_login(staff_user)
    code = discounted_order.discount_code
    url = reverse("orders:manage_discount_delete", kwargs={"pk": code.pk})

    assert client.get(url).status_code == HTTPStatus.NOT_FOUND
    assert client.post(url).status_code == HTTPStatus.NOT_FOUND
    assert DiscountCode.objects.filter(pk=code.pk).exists()
