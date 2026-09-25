from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models, transaction
from django.utils import timezone

from products.models import Product

from .validators import US_STATES, zip_validator


class Cart(models.Model):
    """A customer's cart — one per user, created lazily on first touch."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )

    def __str__(self):
        return f"Cart for {self.user.username}"

    @classmethod
    def for_user(cls, user):
        """Return the user's cart, creating it on first touch."""
        cart, _ = cls.objects.get_or_create(user=user)
        return cart

    def add(self, product):
        """Add a product to the cart; a duplicate add increments its line."""
        item, created = self.items.get_or_create(product=product)
        if not created:
            item.quantity += 1
            item.save()
        return item

    def lines(self):
        """Line items with their products loaded, ready for display."""
        return self.items.select_related("product")

    def total(self):
        return sum((item.line_total for item in self.lines()), Decimal("0.00"))

    def checkout_summary(self, coupon_code=""):
        """Subtotal, discount, and total for checkout's order summary.

        A preview only: ``place_order`` re-validates the code when the
        order is placed. A rejected code comes back as ``error`` (the
        customer-facing message) with no discount applied.
        """
        lines = list(self.lines())
        subtotal = sum((line.line_total for line in lines), Decimal("0.00"))
        summary = {
            "lines": lines,
            "subtotal": subtotal,
            "discount": Decimal("0.00"),
            "total": subtotal,
            "coupon_code": DiscountCode.normalize(coupon_code),
            "applied_code": None,
            "error": "",
        }
        if summary["coupon_code"]:
            try:
                code, discount = DiscountCode.objects.quote(coupon_code, lines)
            except InvalidDiscountCode as error:
                summary["error"] = str(error)
            else:
                summary.update(
                    applied_code=code, discount=discount, total=subtotal - discount
                )
        return summary

    def item_count(self):
        """Total units across all lines — the navbar badge number."""
        return self.items.aggregate(count=models.Sum("quantity"))["count"] or 0


class CartItem(models.Model):
    """One product line in a cart; the cart–product pair is unique."""

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"], name="unique_cart_product"
            )
        ]

    def __str__(self):
        return f"{self.quantity} × {self.product.name}"

    @property
    def line_total(self):
        return self.product.price * self.quantity

    def increment(self):
        self.quantity += 1
        self.save()

    def decrement(self):
        """Step the quantity down, stopping at one — removal is explicit."""
        if self.quantity > 1:
            self.quantity -= 1
            self.save()


class AddressManager(models.Manager):
    def save_for(self, user, checkout_data, prefix):
        """Save one checkout address section to the user's address book.

        ``prefix`` is ``"shipping"`` or ``"billing"``. Values are trimmed,
        and an exact match the user already has is returned instead of
        saving a duplicate.
        """
        values = {
            field: checkout_data[f"{prefix}_{field}"].strip()
            for field in Address.FIELDS
        }
        existing = self.filter(user=user, **values).first()
        return existing or self.create(user=user, **values)


class Address(models.Model):
    """A saved address — a typing shortcut for checkout, never a live link.

    It fills either checkout section: its fields mirror the suffixes of
    ``Order.shipping_*`` and ``Order.billing_*``. Orders copy the values,
    so editing or deleting an address never changes a placed order.

    Each user has at most one default. The model keeps that true: the
    first address saved becomes the default, and deleting the default
    promotes the newest remaining address. (Queryset bulk deletes bypass
    ``delete()``; the app only deletes one instance at a time.)
    """

    FIELDS = ["name", "street", "line2", "city", "state", "zip"]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="addresses",
    )
    name = models.CharField("Full name", max_length=100)
    street = models.CharField("Street address", max_length=200)
    line2 = models.CharField("Apt, suite, etc. (optional)", max_length=200, blank=True)
    city = models.CharField("City", max_length=100)
    state = models.CharField("State", max_length=2, choices=US_STATES)
    zip = models.CharField("ZIP code", max_length=10, validators=[zip_validator])
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    objects = AddressManager()

    class Meta:
        ordering = ["-is_default", "-created_at", "-pk"]
        verbose_name_plural = "addresses"
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="one_default_address_per_user",
            )
        ]

    def __str__(self):
        return f"{self.name} — {self.street}, {self.city}, {self.state} {self.zip}"

    def save(self, *args, **kwargs):
        """A user's first address becomes their default."""
        if self._state.adding and not Address.objects.filter(user=self.user).exists():
            self.is_default = True
        super().save(*args, **kwargs)

    @transaction.atomic
    def delete(self, *args, **kwargs):
        """Delete, promoting the newest remaining address if this was default."""
        was_default, user_id = self.is_default, self.user_id
        result = super().delete(*args, **kwargs)
        if was_default:
            successor = Address.objects.filter(user_id=user_id).first()
            if successor:
                successor.is_default = True
                successor.save(update_fields=["is_default"])
        return result

    @transaction.atomic
    def make_default(self):
        """Make this the user's default, clearing the old one first."""
        Address.objects.filter(user=self.user, is_default=True).exclude(
            pk=self.pk
        ).update(is_default=False)
        self.is_default = True
        self.save(update_fields=["is_default"])

    def as_initial(self, prefix):
        """This address as initial data for one checkout section."""
        return {f"{prefix}_{field}": getattr(self, field) for field in self.FIELDS}


CENT = Decimal("0.01")

code_validator = RegexValidator(
    r"^[A-Z0-9-]+$", "Use only letters, digits, and hyphens."
)


class InvalidDiscountCode(ValueError):
    """A code that can't be applied; the message is shown to the customer."""


class DiscountCodeQuerySet(models.QuerySet):
    def with_usage(self):
        """Annotate ``order_count`` and ``product_count`` for the back office."""
        return self.annotate(
            order_count=models.Count("orders", distinct=True),
            product_count=models.Count("products", distinct=True),
        )

    def unused(self):
        return self.filter(orders__isnull=True)

    def quote(self, raw_code, lines):
        """Validate a typed code against cart lines: ``(code, amount)``.

        The one entry point for both the checkout preview and
        ``place_order``, so both give identical answers and wording.
        Raises ``InvalidDiscountCode`` for an unknown code, or for any
        reason ``DiscountCode.discount_for`` rejects it.
        """
        code = self.filter(code=DiscountCode.normalize(raw_code)).first()
        if code is None:
            raise InvalidDiscountCode("We don't recognize that code.")
        return code, code.discount_for(lines)


class DiscountCode(models.Model):
    """A marketing discount code, entered at checkout.

    ``expires_on`` is optional and inclusive: the code works through the
    whole of that date in the store's time zone. ``is_active`` is the
    separate retire switch. Codes are stored uppercase and are unique
    forever — retired codes keep their name — so the code text copied
    onto an order always means exactly one promotion.

    Orders snapshot the discount they received; changing or retiring a
    code never changes a placed order.
    """

    class Kind(models.TextChoices):
        PERCENT = "PERCENT", "Percent off"
        FIXED = "FIXED", "Fixed amount off"

    class Scope(models.TextChoices):
        ORDER = "ORDER", "Whole order"
        PRODUCTS = "PRODUCTS", "Specific products"

    # The terms a used code can no longer change.
    LOCKED_WHEN_USED = ["code", "kind", "value", "scope", "products"]

    code = models.CharField(max_length=32, unique=True, validators=[code_validator])
    kind = models.CharField(max_length=7, choices=Kind.choices, default=Kind.PERCENT)
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="A percentage (1–100) or a dollar amount.",
    )
    scope = models.CharField(max_length=8, choices=Scope.choices, default=Scope.ORDER)
    products = models.ManyToManyField(
        Product,
        blank=True,
        related_name="discount_codes",
        help_text="Only these products are discounted (specific-products codes).",
    )
    expires_on = models.DateField(
        "Expires on",
        null=True,
        blank=True,
        help_text="Optional. The code works through the end of this date.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    objects = DiscountCodeQuerySet.as_manager()

    class Meta:
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(value__gt=0), name="discount_value_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(kind="FIXED") | models.Q(value__lte=100),
                name="discount_percent_at_most_100",
            ),
        ]

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        self.code = self.normalize(self.code)
        super().save(*args, **kwargs)

    @staticmethod
    def normalize(raw_code):
        """Trim and uppercase — how customers' typing matches stored codes."""
        return (raw_code or "").strip().upper()

    @property
    def value_display(self):
        """``10%`` or ``$20.00``."""
        if self.kind == self.Kind.PERCENT:
            return f"{self.value.normalize():f}%"
        return f"${self.value:,.2f}"

    def is_expired(self):
        return self.expires_on is not None and timezone.localdate() > self.expires_on

    @property
    def status(self):
        """Active, Retired, or Expired — retiring outranks the calendar."""
        if not self.is_active:
            return "Retired"
        if self.is_expired():
            return "Expired"
        return "Active"

    def is_used(self):
        return self.orders.exists()

    def eligible_subtotal(self, lines):
        """The part of the cart this code discounts.

        ``lines`` are cart lines: anything with ``product_id`` and
        ``line_total``.
        """
        lines = list(lines)
        if self.scope == self.Scope.PRODUCTS:
            eligible_ids = set(self.products.values_list("pk", flat=True))
            lines = [line for line in lines if line.product_id in eligible_ids]
        return sum((line.line_total for line in lines), Decimal("0.00"))

    def discount_for(self, lines):
        """The discount this code gives these cart lines, in cents.

        Checks run in a fixed order and the first failure wins: retired,
        then expired, then whether it applies to the cart at all. A
        fixed discount is capped at the eligible subtotal.
        """
        if not self.is_active:
            raise InvalidDiscountCode("This code is no longer available.")
        if self.is_expired():
            raise InvalidDiscountCode(
                f"This code expired on {self.expires_on:%B} "
                f"{self.expires_on.day}, {self.expires_on.year}."
            )
        eligible = self.eligible_subtotal(lines)
        if eligible <= 0:
            raise InvalidDiscountCode(
                "This code doesn't apply to anything in your cart."
            )
        if self.kind == self.Kind.PERCENT:
            amount = eligible * self.value / 100
        else:
            amount = min(self.value, eligible)
        return amount.quantize(CENT, rounding=ROUND_HALF_UP)

    def retire(self):
        self.is_active = False
        self.save(update_fields=["is_active"])

    def reactivate(self):
        self.is_active = True
        self.save(update_fields=["is_active"])


class Order(models.Model):
    """A placed order — a snapshot, never a live view of the catalog.

    Addresses are flat denormalized fields: the order must not change if
    the customer later edits anything. Of the card, only the last four
    digits survive checkout. Discounts are snapshotted the same way:
    ``subtotal - discount_amount = total``, and ``total`` is what the
    customer paid. ``coupon_code`` keeps the text used; the
    ``discount_code`` link is for back-office lookups only and is never
    used to recompute an amount.
    """

    class Status(models.TextChoices):
        PLACED = "PLACED", "Placed"
        SHIPPED = "SHIPPED", "Shipped"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PLACED
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00")
    )
    total = models.DecimalField(max_digits=10, decimal_places=2)
    coupon_code = models.CharField(max_length=32, blank=True)
    discount_code = models.ForeignKey(
        DiscountCode,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    email = models.EmailField()

    shipping_name = models.CharField(max_length=100)
    shipping_street = models.CharField(max_length=200)
    shipping_line2 = models.CharField(max_length=200, blank=True)
    shipping_city = models.CharField(max_length=100)
    shipping_state = models.CharField(max_length=2)
    shipping_zip = models.CharField(max_length=10)

    billing_name = models.CharField(max_length=100)
    billing_street = models.CharField(max_length=200)
    billing_line2 = models.CharField(max_length=200, blank=True)
    billing_city = models.CharField(max_length=100)
    billing_state = models.CharField(max_length=2)
    billing_zip = models.CharField(max_length=10)

    card_last4 = models.CharField(max_length=4)

    # default (not auto_now_add) so the seed can backdate orders.
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.number

    @property
    def number(self):
        """The customer-facing order number, e.g. ``TT-2026-00042``."""
        return f"TT-{self.created_at.year}-{self.pk:05d}"


class OrderItem(models.Model):
    """One line of an order, priced as of purchase time.

    Name and unit price are denormalized: order history must not change
    when the catalog does. The product FK survives for linking while the
    product exists.
    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    product_name = models.CharField(max_length=200)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ["pk"]

    def __str__(self):
        return f"{self.quantity} × {self.product_name}"

    @property
    def line_total(self):
        return self.unit_price * self.quantity
