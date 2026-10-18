from django import template

from reviews.views import section_context

register = template.Library()


@register.inclusion_tag("reviews/partials/_section.html", takes_context=True)
def reviews_section(context, product):
    """Render the product's Reviews section in its first-load state.

    The same context every write response renders, so the section's
    states live in one place. The query count doesn't grow with the
    number of reviews.
    """
    return section_context(product, context["user"])
