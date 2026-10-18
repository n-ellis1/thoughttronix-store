from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from products.models import Product

RATING_CHOICES = [
    (stars, f"{stars} star{'s' if stars > 1 else ''}") for stars in range(1, 6)
]


class ReviewQuerySet(models.QuerySet):
    def for_product(self, product):
        """The product's reviews, newest first, with both people loaded."""
        return self.filter(product=product).select_related("user", "edited_by")

    def summary_for(self, product):
        """The product's ``average``, review ``count``, and whole ``stars``.

        One aggregate query. With no reviews, ``average`` is None and
        ``count`` and ``stars`` are 0.
        """
        summary = self.filter(product=product).aggregate(
            average=models.Avg("rating"), count=models.Count("pk")
        )
        average = summary["average"]
        summary["stars"] = (
            0
            if average is None
            # Half up, like orders' money rounding; round() would make 4.5 → 4.
            else int(Decimal(str(average)).quantize(Decimal("1"), ROUND_HALF_UP))
        )
        return summary


class Review(models.Model):
    """One customer's rating and comment on one product.

    ``edited_at`` records *whether* the review has been edited and
    ``edited_by`` records *who* made the last edit; ``edited_by`` is
    cleared if that account is deleted, but the review still counts as
    edited.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews"
    )
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField(max_length=2000)
    # default (not auto_now_add) so the seed can backdate reviews.
    created_at = models.DateTimeField(default=timezone.now)
    # Set explicitly by each edit, never auto_now.
    edited_at = models.DateTimeField(null=True, blank=True)
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    objects = ReviewQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "product"], name="unique_review_user_product"
            ),
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="review_rating_1_to_5",
            ),
            models.CheckConstraint(
                condition=models.Q(edited_by__isnull=True)
                | models.Q(edited_at__isnull=False),
                name="review_edited_by_requires_edited_at",
            ),
        ]

    def __str__(self):
        return f"{self.user.username}'s review of {self.product.name}"

    @property
    def edit_label(self):
        """The review's label: blank, "Edited", or "Edited by ThoughtTronix staff".

        Staff is named only when the last editor is someone other than the
        author. A deleted last editor still reads "Edited": the review is
        never shown as unedited once ``edited_at`` is set.
        """
        if self.edited_at is None:
            return ""
        if self.edited_by_id is None or self.edited_by_id == self.user_id:
            return "Edited"
        return "Edited by ThoughtTronix staff"
