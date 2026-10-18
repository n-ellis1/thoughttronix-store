from django.conf import settings
from django.db import models
from django.utils import timezone

from products.models import Product


class WishlistItemManager(models.Manager):
    """The wishlist's whole workflow: add, remove, and check one product.

    Call these through ``WishlistItem.objects`` — the reverse manager
    ``user.wishlist_items`` has Django's own ``add()`` instead.
    """

    def add(self, user, product):
        """Save a product to the user's wishlist; saving it again is a no-op."""
        item, _ = self.get_or_create(user=user, product=product)
        return item

    def remove(self, user, product):
        """Take a product off the user's wishlist; a no-op if it isn't there."""
        self.filter(user=user, product=product).delete()

    def contains(self, user, product):
        """Whether the product is on the user's wishlist — one existence query."""
        return self.filter(user=user, product=product).exists()


class WishlistItem(models.Model):
    """One product a customer has saved for later.

    There is no container model: a user's rows *are* their wishlist.
    Saving isn't buying, so unavailable products can be saved and stay
    saved; deleting the product or the user removes the row.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # default (not auto_now_add) so the seed can backdate items.
    created_at = models.DateTimeField(default=timezone.now)

    objects = WishlistItemManager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"], name="unique_wishlist_user_product"
            )
        ]

    def __str__(self):
        return f"{self.product.name} on {self.user.username}'s wishlist"
