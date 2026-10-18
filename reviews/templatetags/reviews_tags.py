from django import template

from reviews.models import Review

register = template.Library()


@register.inclusion_tag("reviews/partials/_section.html")
def reviews_section(product):
    """Render the product's Reviews section: summary, list, or empty state.

    Two queries however many reviews there are — one aggregate for the
    summary, one for the list with its people joined in.
    """
    return {
        "product": product,
        "summary": Review.objects.summary_for(product),
        "reviews": Review.objects.for_product(product),
    }
