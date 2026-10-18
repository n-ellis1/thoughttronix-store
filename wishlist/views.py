"""Wishlist views — thin per the architecture convention.

The two HTMX endpoints, add and remove, each say what the customer
clicked — there is no toggle — so a double-click or a stale tab still
ends in the intended state. Both re-render only the button partial.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import ListView

from accounts.mixins import HtmxLoginRequiredMixin
from products.models import Product

from .models import WishlistItem


class WishlistView(LoginRequiredMixin, ListView):
    """The signed-in customer's saved products, newest first per the
    model ordering."""

    template_name = "wishlist/wishlist.html"
    context_object_name = "items"

    def get_queryset(self):
        # The category is joined too: image_url falls back to its placeholder.
        return WishlistItem.objects.filter(user=self.request.user).select_related(
            "product__category"
        )


class WishlistActionView(HtmxLoginRequiredMixin, View):
    """Base for HTMX add/remove: act, then re-render the button.

    Looks the product up among *all* products, not only ``available()``
    as ``AddToCartView`` does: saving isn't buying, and the cart and
    checkout already refuse to sell unavailable products. The button is
    rendered from the database after the action, so it shows what's
    actually saved. A session that ended while the page was open sends
    the customer to sign in and back to the product page.
    """

    def get_login_next_url(self):
        return get_object_or_404(Product, pk=self.kwargs["pk"]).get_absolute_url()

    def post(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        self.act(request.user, product)
        return render(
            request,
            "wishlist/partials/_button.html",
            {
                "product": product,
                "saved": WishlistItem.objects.contains(request.user, product),
            },
        )

    def act(self, user, product):
        raise NotImplementedError


class AddToWishlistView(WishlistActionView):
    def act(self, user, product):
        WishlistItem.objects.add(user, product)


class RemoveFromWishlistView(WishlistActionView):
    def act(self, user, product):
        WishlistItem.objects.remove(user, product)
