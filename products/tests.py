from decimal import Decimal
from http import HTTPStatus

import pytest
from django.db import IntegrityError
from django.urls import reverse
from django.utils.html import escape

from .models import Category, Product

# --- Model behavior -------------------------------------------------------


def test_category_str(category):
    assert str(category) == "Home Assistants"


def test_product_str(product):
    assert str(product) == "Seraphine Home Hub"


def test_tag_str(tag):
    assert str(tag) == "bestseller"


def test_available_manager_excludes_unavailable(product, unavailable_product):
    available = Product.objects.available()

    assert product in available
    assert unavailable_product not in available


def test_search_matches_name_and_description(product, unavailable_product):
    assert product in Product.objects.search("home hub")
    assert product in Product.objects.search("seven-microphone")
    assert product not in Product.objects.search("death ray")


def test_product_slug_unique(product, category):
    with pytest.raises(IntegrityError):
        Product.objects.create(
            name="Another Hub",
            slug=product.slug,
            price=Decimal("1.00"),
            category=category,
        )


def test_product_get_absolute_url(product):
    assert product.get_absolute_url() == "/products/seraphine-home-hub/"


def test_category_get_absolute_url(category):
    assert category.get_absolute_url() == "/categories/home-assistants/"


# --- Catalog views ---------------------------------------------------------


def test_catalog_displays_product(client, product):
    """The catalog shows a product's name, category, tagline, and price."""
    response = client.get(reverse("products:catalog"))

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert product.name in page
    assert product.category.name in page
    assert escape(product.tagline) in page
    assert str(product.price) in page
    assert product.get_absolute_url() in page


def test_detail_page(client, product):
    response = client.get(product.get_absolute_url())

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert product.name in page
    assert escape(product.description) in page


def test_catalog_shows_featured_badge(client, featured_product):
    response = client.get(reverse("products:catalog"))

    assert "Featured" in response.content.decode()


def test_catalog_hides_featured_badge_for_unfeatured_product(client, product):
    response = client.get(reverse("products:catalog"))

    assert "Featured" not in response.content.decode()


def test_detail_shows_featured_badge(client, featured_product):
    response = client.get(featured_product.get_absolute_url())

    assert "Featured" in response.content.decode()


def test_detail_hides_featured_badge_for_unfeatured_product(client, product):
    response = client.get(product.get_absolute_url())

    assert "Featured" not in response.content.decode()


def test_product_defaults_to_unfeatured(product):
    assert product.is_featured is False


def test_detail_unknown_slug_404(client, db):
    response = client.get(reverse("products:detail", kwargs={"slug": "no-such-thing"}))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_detail_shows_availability(client, unavailable_product):
    response = client.get(unavailable_product.get_absolute_url())

    assert "Unavailable" in response.content.decode()


def test_category_page_lists_only_its_products(client, product):
    defense = Category.objects.create(name="Defense", slug="defense")
    Product.objects.create(
        name="SoulSear Mark II",
        slug="soulsear-mark-ii",
        price=Decimal("2400000.00"),
        category=defense,
    )

    response = client.get(defense.get_absolute_url())

    assert response.status_code == HTTPStatus.OK
    page = response.content.decode()
    assert "SoulSear Mark II" in page
    assert product.name not in page


def test_category_unknown_slug_404(client, db):
    response = client.get(reverse("products:category", kwargs={"slug": "nope"}))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_empty_category_shows_empty_state(client, db):
    empty = Category.objects.create(name="Defense", slug="defense")

    response = client.get(empty.get_absolute_url())

    assert "This shelf is empty" in response.content.decode()


# --- Search, filtering, and their composition ------------------------------


def test_search_filters_catalog(client, product, unavailable_product):
    response = client.get(reverse("products:catalog"), {"q": "home hub"})

    page = response.content.decode()
    assert product.name in page
    assert unavailable_product.name not in page


def test_search_no_results_shows_empty_state(client, product):
    response = client.get(reverse("products:catalog"), {"q": "death ray"})

    assert "Nothing matches" in response.content.decode()


def test_tag_filter(client, product, unavailable_product, tag):
    product.tags.add(tag)

    response = client.get(reverse("products:catalog"), {"tag": tag.slug})

    page = response.content.decode()
    assert product.name in page
    assert unavailable_product.name not in page


def test_search_and_tag_compose(client, product, unavailable_product, tag):
    product.tags.add(tag)
    unavailable_product.tags.add(tag)

    response = client.get(
        reverse("products:catalog"), {"tag": tag.slug, "q": "home hub"}
    )

    page = response.content.decode()
    assert product.name in page
    assert unavailable_product.name not in page


def test_category_querystring_filter(client, product):
    defense = Category.objects.create(name="Defense", slug="defense")
    Product.objects.create(
        name="SoulSear Mark II",
        slug="soulsear-mark-ii",
        price=Decimal("2400000.00"),
        category=defense,
    )

    response = client.get(reverse("products:catalog"), {"category": "defense"})

    page = response.content.decode()
    assert "SoulSear Mark II" in page
    assert product.name not in page


def test_catalog_paginates_at_twelve(client, category):
    for n in range(13):
        Product.objects.create(
            name=f"Widget {n:02d}",
            slug=f"widget-{n:02d}",
            price=Decimal("9.99"),
            category=category,
        )

    first = client.get(reverse("products:catalog"))
    second = client.get(reverse("products:catalog"), {"page": 2})

    assert len(first.context["products"]) == 12
    assert len(second.context["products"]) == 1
    assert "Page 2 of 2" in second.content.decode()
