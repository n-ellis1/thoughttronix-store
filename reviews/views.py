"""Review views — thin per the architecture convention.

HTMX endpoints, not pages. Every write re-renders the whole Reviews
section from the database, the cart's pattern, so the summary, the
viewer's slot, and the list can never disagree. An invalid form
re-renders only itself.
"""

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, render
from django.views import View

from accounts.mixins import HtmxLoginRequiredMixin
from products.models import Product

from .forms import ALREADY_REVIEWED, ReviewForm
from .models import Review

SECTION_TEMPLATE = "reviews/partials/_section.html"
FORM_TEMPLATE = "reviews/partials/_form.html"
CARD_TEMPLATE = "reviews/partials/_card.html"


def section_context(product, user):
    """Everything the Reviews section renders, read fresh from the database.

    The viewer's own review is pinned in the slot and left out of the
    list; a signed-in viewer without one gets the create form only if
    they've bought the product.
    """
    own_review = Review.objects.own_review(user, product)
    reviews = Review.objects.for_product(product)
    if own_review:
        reviews = reviews.exclude(pk=own_review.pk)
    may_review = (
        user.is_authenticated
        and own_review is None
        and Review.objects.has_purchased(user, product)
    )
    return {
        "user": user,
        "product": product,
        "summary": Review.objects.summary_for(product),
        "own_review": own_review,
        "reviews": reviews,
        "form": ReviewForm() if may_review else None,
    }


class CreateReviewView(HtmxLoginRequiredMixin, View):
    """HTMX: write the signed-in buyer's review of a product.

    Looks the product up among *all* products: a buyer may review one
    that has since become unavailable. The checks run in a fixed order:
    no qualifying purchase is refused before the form is involved; a
    second review is a form error, never an overwrite; a valid review is
    saved and the whole section returned.
    """

    def get_login_next_url(self):
        return get_object_or_404(Product, pk=self.kwargs["pk"]).get_absolute_url()

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        if not Review.objects.has_purchased(request.user, product):
            raise PermissionDenied
        form = ReviewForm(
            request.POST, instance=Review(user=request.user, product=product)
        )
        if not form.is_valid():
            return form_invalid(request, form, product, "#review-form")
        try:
            with transaction.atomic():
                form.save()
        except IntegrityError:
            # Two submits at once both passed clean(); the database kept one.
            form.add_error(None, ALREADY_REVIEWED)
            return form_invalid(request, form, product, "#review-form")
        return render(request, SECTION_TEMPLATE, section_context(product, request.user))


def form_invalid(request, form, product, target):
    """Just the form, with its errors and input, swapped over itself at
    ``target`` rather than the section, so nothing else on the page moves."""
    response = render(request, FORM_TEMPLATE, {"form": form, "product": product})
    response["HX-Retarget"] = target
    response["HX-Reswap"] = "outerHTML"
    return response


def edit_form(review, data=None):
    """The edit form for ``review``, with ids that can't clash with any
    other form on the page."""
    return ReviewForm(data, instance=review, auto_id=f"id_review_{review.pk}_%s")


class ReviewEndpointMixin(HtmxLoginRequiredMixin):
    """Sign-in handling and the lookup for endpoints on one saved review.

    A signed-out request returns to the review's product page.
    """

    def get_login_next_url(self):
        review = get_object_or_404(Review, pk=self.kwargs["pk"])
        return review.product.get_absolute_url()

    def get_review(self):
        """The review, only if the requesting user may change it."""
        return get_object_or_404(
            Review.objects.editable_by(self.request.user).select_related("product"),
            pk=self.kwargs["pk"],
        )


class ReviewCardView(ReviewEndpointMixin, View):
    """HTMX: a review's normal card — what Cancel swaps back in."""

    def get(self, request, pk):
        return render(request, CARD_TEMPLATE, {"review": self.get_review()})


class EditReviewView(ReviewEndpointMixin, View):
    """HTMX: GET swaps a review's card for its edit form; POST saves it.

    Saving doesn't re-check the purchase: eligibility applies only when
    a review is written. An invalid save changes nothing in the database
    and comes back as the edit form alone, over itself.
    """

    def get(self, request, pk):
        review = self.get_review()
        return render(
            request,
            FORM_TEMPLATE,
            {"form": edit_form(review), "product": review.product},
        )

    def post(self, request, pk):
        review = self.get_review()
        form = edit_form(review, request.POST)
        if not form.is_valid():
            return form_invalid(request, form, review.product, f"#review-{review.pk}")
        form.instance.record_edit(request.user)
        return render(
            request, SECTION_TEMPLATE, section_context(review.product, request.user)
        )


class DeleteReviewView(ReviewEndpointMixin, View):
    """HTMX: delete a review and return the whole section, its slot
    chosen from the database as it now stands."""

    def post(self, request, pk):
        review = self.get_review()
        review.delete()
        return render(
            request, SECTION_TEMPLATE, section_context(review.product, request.user)
        )
