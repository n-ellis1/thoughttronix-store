from django import template

from wishlist.models import WishlistItem

register = template.Library()


@register.inclusion_tag("wishlist/partials/_button.html", takes_context=True)
def wishlist_button(context, product):
    """Render the wishlist button for ``product`` in its first-load state.

    One existence query per button for signed-in users — fine on a
    detail page; revisit before putting buttons in catalog grids.
    """
    user = context["user"]
    saved = user.is_authenticated and WishlistItem.objects.contains(user, product)
    return {"user": user, "product": product, "saved": saved}
