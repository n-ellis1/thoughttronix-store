"""The seed's pure helpers. Tests never invoke the seed command itself."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.utils import timezone

from orders.models import Order, OrderItem
from products.management.commands.seed import qualifying_purchases
from products.models import Product


def make_order(user, product, status, ordered_at):
    """An order of one ``product`` by ``user``, placed at ``ordered_at``."""
    order = Order.objects.create(
        user=user,
        status=status,
        subtotal=product.price,
        total=product.price,
        email="buyer@example.com",
        shipping_name="Casey Monroe",
        shipping_street="214 Synapse Street",
        shipping_city="Canyon",
        shipping_state="TX",
        shipping_zip="79015",
        billing_name="Casey Monroe",
        billing_street="214 Synapse Street",
        billing_city="Canyon",
        billing_state="TX",
        billing_zip="79015",
        card_last4="4242",
        created_at=ordered_at,
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        unit_price=product.price,
        quantity=1,
    )
    return order


def test_qualifying_purchases_pairs_each_buyer_once_from_their_own_orders(
    customer, product, category
):
    """Cancelled orders never qualify, a purchase belongs only to its buyer,
    and a product bought twice is one pair dated by the earliest
    qualifying order."""
    other_buyer = get_user_model().objects.create_user(username="dcole")
    veil = Product.objects.create(
        name="Veil", slug="veil", price=Decimal("89.00"), category=category
    )
    now = timezone.now()

    def days_ago(days):
        return now - timedelta(days=days)

    # The customer's earliest order of the hub was cancelled, so it doesn't
    # date the pair; the placed one 30 days ago does.
    make_order(customer, product, Order.Status.CANCELLED, days_ago(60))
    make_order(customer, product, Order.Status.PLACED, days_ago(30))
    make_order(customer, product, Order.Status.DELIVERED, days_ago(10))
    # The customer ordered Veil only in a cancelled order; another user's
    # shipped Veil order makes that user eligible, never the customer.
    make_order(customer, veil, Order.Status.CANCELLED, days_ago(20))
    make_order(other_buyer, veil, Order.Status.SHIPPED, days_ago(5))

    assert [
        (user.username, bought.slug, ordered_at)
        for user, bought, ordered_at in qualifying_purchases()
    ] == [
        ("customer", "seraphine-home-hub", days_ago(30)),
        ("dcole", "veil", days_ago(5)),
    ]


def test_qualifying_purchases_skips_lines_whose_product_was_deleted(customer, product):
    """A deleted product leaves its order lines behind with no product;
    there is nothing left to review."""
    make_order(customer, product, Order.Status.DELIVERED, timezone.now())
    product.delete()

    assert qualifying_purchases() == []
