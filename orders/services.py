"""Order placement — one of the codebase's two deliberate deep modules.

The interface is the product: one function that turns a cart and a
validated checkout into an order, all-or-nothing. Callers never touch
``Order`` construction directly.
"""

from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.db import transaction

from .models import Cart, DiscountCode, Order, OrderItem

ADDRESS_FIELDS = [
    "email",
    "shipping_name",
    "shipping_street",
    "shipping_line2",
    "shipping_city",
    "shipping_state",
    "shipping_zip",
    "billing_name",
    "billing_street",
    "billing_line2",
    "billing_city",
    "billing_state",
    "billing_zip",
]


@transaction.atomic
def place_order(
    cart: Cart,
    user: AbstractBaseUser,
    checkout_data: Mapping[str, Any],
    *,
    coupon_code: str | None = None,
) -> Order:
    """Create an order from the cart's contents, then empty the cart.

    ``checkout_data`` is the ``cleaned_data`` of a valid ``CheckoutForm``.
    Addresses and line prices are denormalized onto the order — an order
    is a snapshot, immune to later catalog or address edits. Of the card,
    only the last four digits are stored; the full number and CVV never
    touch the database.

    All-or-nothing: runs in a transaction, so a failure partway through
    leaves no partial order and the cart intact.

    ``coupon_code`` is the code as the customer typed it; blank means no
    discount. It is validated and priced here, inside the transaction,
    whatever the checkout preview showed. The order snapshots the result
    — ``subtotal``, ``discount_amount``, ``total`` (what was paid), and
    the code text — so later edits to or retirement of the code never
    change it.

    Raises ``ValueError`` if the cart is empty or holds a product that is
    no longer available, and its subclass ``InvalidDiscountCode`` if the
    coupon code is unknown, retired, expired, or matches nothing in the
    cart. Either way no order is created and the cart is untouched.
    """
    lines = list(cart.lines())
    if not lines:
        raise ValueError("Cannot place an order from an empty cart.")
    unavailable = [line.product.name for line in lines if not line.product.is_available]
    if unavailable:
        raise ValueError(
            f"No longer available: {', '.join(unavailable)}. "
            "Remove them from the cart to check out."
        )

    subtotal = sum((line.line_total for line in lines), Decimal("0.00"))
    discount_code, discount = None, Decimal("0.00")
    if DiscountCode.normalize(coupon_code):
        # Re-validated here, not trusted from the checkout preview: the
        # code may have expired or been retired since the customer applied it.
        discount_code, discount = DiscountCode.objects.quote(coupon_code, lines)

    card_digits = checkout_data["card_number"].replace(" ", "").replace("-", "")
    order = Order.objects.create(
        user=user,
        subtotal=subtotal,
        discount_amount=discount,
        total=subtotal - discount,
        coupon_code=discount_code.code if discount_code else "",
        discount_code=discount_code,
        card_last4=card_digits[-4:],
        **{name: checkout_data[name] for name in ADDRESS_FIELDS},
    )
    for line in lines:
        OrderItem.objects.create(
            order=order,
            product=line.product,
            product_name=line.product.name,
            unit_price=line.product.price,
            quantity=line.quantity,
        )
    cart.items.all().delete()
    return order
