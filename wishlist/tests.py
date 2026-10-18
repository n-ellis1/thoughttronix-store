import re
from datetime import timedelta
from http import HTTPStatus
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertContains, assertNotContains

from .models import WishlistItem


@pytest.fixture
def other_customer(db):
    return get_user_model().objects.create_user(
        username="othercustomer", password="other123"
    )


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        username="admin", password="admin123"
    )


def add_url(product):
    return reverse("wishlist:add", kwargs={"pk": product.pk})


def remove_url(product):
    return reverse("wishlist:remove", kwargs={"pk": product.pk})


def saved(user, product):
    return WishlistItem.objects.filter(user=user, product=product).count()


def assert_partial_only(response, partial):
    """The response is the partial alone — never a full page."""
    names = [template.name for template in response.templates]
    assert partial in names
    assert "base.html" not in names


# --- Model behavior ---------------------------------------------------------


def test_str(customer, product):
    item = WishlistItem.objects.add(customer, product)

    assert str(item) == "Seraphine Home Hub on customer's wishlist"


def test_add_is_idempotent(customer, product):
    first = WishlistItem.objects.add(customer, product)
    second = WishlistItem.objects.add(customer, product)

    assert first == second
    assert saved(customer, product) == 1


def test_remove_deletes_the_item(customer, product):
    WishlistItem.objects.add(customer, product)

    WishlistItem.objects.remove(customer, product)

    assert saved(customer, product) == 0


def test_remove_of_an_absent_item_does_nothing(customer, product):
    WishlistItem.objects.remove(customer, product)

    assert WishlistItem.objects.count() == 0


def test_contains(customer, product, unavailable_product):
    WishlistItem.objects.add(customer, product)

    assert WishlistItem.objects.contains(customer, product)
    assert not WishlistItem.objects.contains(customer, unavailable_product)


def test_user_product_pair_is_unique(customer, product):
    WishlistItem.objects.create(user=customer, product=product)

    with pytest.raises(IntegrityError):
        WishlistItem.objects.create(user=customer, product=product)


def test_related_name(customer, product):
    item = WishlistItem.objects.add(customer, product)

    assert list(customer.wishlist_items.all()) == [item]


def test_ordering_is_newest_first(customer, product, unavailable_product):
    older = WishlistItem.objects.add(customer, product)
    newer = WishlistItem.objects.add(customer, unavailable_product)

    assert list(WishlistItem.objects.all()) == [newer, older]


def test_deleting_a_product_removes_it_from_wishlists(customer, product):
    WishlistItem.objects.add(customer, product)

    product.delete()

    assert WishlistItem.objects.count() == 0


def test_marking_a_product_unavailable_keeps_it_saved(customer, product):
    WishlistItem.objects.add(customer, product)

    product.is_available = False
    product.save()

    assert saved(customer, product) == 1


def test_deleting_a_user_removes_their_wishlist(customer, product):
    WishlistItem.objects.add(customer, product)

    customer.delete()

    assert WishlistItem.objects.count() == 0


# --- The add and remove endpoints --------------------------------------------


def test_add_saves_and_returns_the_saved_button(client, customer, product):
    client.force_login(customer)

    response = client.post(add_url(product))

    assert response.status_code == HTTPStatus.OK
    assert_partial_only(response, "wishlist/partials/_button.html")
    page = response.content.decode()
    assert "On your wishlist" in page
    assert remove_url(product) in page
    assert saved(customer, product) == 1


def test_remove_unsaves_and_returns_the_unsaved_button(client, customer, product):
    WishlistItem.objects.add(customer, product)
    client.force_login(customer)

    response = client.post(remove_url(product))

    assert response.status_code == HTTPStatus.OK
    assert_partial_only(response, "wishlist/partials/_button.html")
    page = response.content.decode()
    assert "Save to wishlist" in page
    assert add_url(product) in page
    assert saved(customer, product) == 0


def test_adding_twice_leaves_one_row_and_stays_saved(client, customer, product):
    client.force_login(customer)

    client.post(add_url(product))
    response = client.post(add_url(product))

    assert "On your wishlist" in response.content.decode()
    assert saved(customer, product) == 1


def test_removing_an_unsaved_product_succeeds_and_stays_unsaved(
    client, customer, product
):
    client.force_login(customer)

    response = client.post(remove_url(product))

    assert response.status_code == HTTPStatus.OK
    assert "Save to wishlist" in response.content.decode()
    assert WishlistItem.objects.count() == 0


def test_unavailable_product_can_be_added_and_removed(
    client, customer, unavailable_product
):
    client.force_login(customer)

    added = client.post(add_url(unavailable_product))
    assert added.status_code == HTTPStatus.OK
    assert saved(customer, unavailable_product) == 1

    removed = client.post(remove_url(unavailable_product))
    assert removed.status_code == HTTPStatus.OK
    assert saved(customer, unavailable_product) == 0


@pytest.mark.parametrize("name", ["wishlist:add", "wishlist:remove"])
def test_unknown_product_404s(client, customer, name):
    client.force_login(customer)

    response = client.post(reverse(name, kwargs={"pk": 999}))

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize("url", [add_url, remove_url])
def test_get_is_rejected(client, customer, product, url):
    client.force_login(customer)

    response = client.get(url(product))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
    assert WishlistItem.objects.count() == 0


def test_signed_out_add_redirects_to_sign_in_and_saves_nothing(client, product):
    response = client.post(add_url(product))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
    assert WishlistItem.objects.count() == 0


def test_signed_out_remove_redirects_to_sign_in_and_removes_nothing(
    client, customer, product
):
    WishlistItem.objects.add(customer, product)

    response = client.post(remove_url(product))

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
    assert saved(customer, product) == 1


@pytest.mark.parametrize(
    ("url", "rows"),
    [(add_url, 0), (remove_url, 1)],
    ids=["add-saves-nothing", "remove-removes-nothing"],
)
def test_signed_out_htmx_post_gets_hx_redirect_to_sign_in_and_changes_nothing(
    client, customer, product, url, rows
):
    if rows:
        WishlistItem.objects.add(customer, product)

    response = client.post(url(product), headers={"HX-Request": "true"})

    assert response.status_code == HTTPStatus.OK
    assert response["HX-Redirect"] == (
        f"{reverse('accounts:login')}?next={product.get_absolute_url()}"
    )
    assert WishlistItem.objects.count() == rows
    assert saved(customer, product) == rows


@pytest.mark.parametrize("name", ["wishlist:add", "wishlist:remove"])
def test_signed_out_htmx_post_for_unknown_product_404s(client, db, name):
    response = client.post(
        reverse(name, kwargs={"pk": 999}), headers={"HX-Request": "true"}
    )

    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.parametrize("fixture", ["staff_user", "superuser"])
def test_staff_and_superusers_have_wishlists(client, request, product, fixture):
    user = request.getfixturevalue(fixture)
    client.force_login(user)

    client.post(add_url(product))
    assert saved(user, product) == 1

    client.post(remove_url(product))
    assert saved(user, product) == 0


# --- Isolation ---------------------------------------------------------------


def test_adding_never_touches_another_customers_wishlist(
    client, customer, other_customer, product
):
    client.force_login(customer)

    client.post(add_url(product))

    assert saved(customer, product) == 1
    assert saved(other_customer, product) == 0


def test_removing_never_touches_another_customers_wishlist(
    client, customer, other_customer, product
):
    WishlistItem.objects.add(other_customer, product)
    client.force_login(customer)

    response = client.post(remove_url(product))

    assert "Save to wishlist" in response.content.decode()
    assert saved(other_customer, product) == 1


# --- The product detail page --------------------------------------------------


def detail(client, product):
    return client.get(product.get_absolute_url()).content.decode()


def test_detail_page_shows_unsaved_button(client, customer, product):
    client.force_login(customer)

    page = detail(client, product)

    assert add_url(product) in page
    assert remove_url(product) not in page


def test_detail_page_shows_saved_button(client, customer, product):
    WishlistItem.objects.add(customer, product)
    client.force_login(customer)

    page = detail(client, product)

    assert remove_url(product) in page
    assert add_url(product) not in page
    assert "On your wishlist" in page


def test_detail_page_ignores_another_customers_wishlist(
    client, customer, other_customer, product
):
    WishlistItem.objects.add(other_customer, product)
    client.force_login(customer)

    assert add_url(product) in detail(client, product)


def test_unavailable_detail_page_shows_the_wishlist_button(
    client, customer, unavailable_product
):
    client.force_login(customer)

    assert add_url(unavailable_product) in detail(client, unavailable_product)


def wishlist_link_attrs(page):
    """The attributes of the "Save to wishlist" ``<a>`` link, or None."""
    match = re.search(r"<a\b([^>]*)>\s*Save to wishlist\s*</a>", page)
    return match and match.group(1)


def test_detail_page_shows_sign_in_link_when_signed_out(client, product):
    attrs = wishlist_link_attrs(detail(client, product))

    assert attrs is not None
    login = f"{reverse('accounts:login')}?next={product.get_absolute_url()}"
    assert f'href="{login}"' in attrs
    assert "hx-" not in attrs


def test_signing_in_from_the_link_returns_to_the_product_unsaved(
    client, customer, product
):
    response = client.post(
        f"{reverse('accounts:login')}?next={product.get_absolute_url()}",
        {"username": "customer", "password": "customer123"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == product.get_absolute_url()
    assert WishlistItem.objects.count() == 0


def test_signed_out_detail_page_has_no_htmx_wishlist_button(client, product):
    page = detail(client, product)

    assert add_url(product) not in page
    assert remove_url(product) not in page


# --- App boundaries ------------------------------------------------------------


def test_cart_views_keep_plain_login_redirect_for_htmx(client, product):
    """Moving the cart onto ``HtmxLoginRequiredMixin`` is a separate
    follow-up; until then its HTMX endpoints still get a plain redirect."""
    response = client.post(
        reverse("orders:add", kwargs={"pk": product.pk}),
        headers={"HX-Request": "true"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert reverse("accounts:login") in response.url
    assert "HX-Redirect" not in response


def test_products_app_never_imports_wishlist():
    """The seed command is exempt: it's where the apps are put together."""
    products_dir = Path(__file__).resolve().parent.parent / "products"
    for source in products_dir.rglob("*.py"):
        if "management" in source.parts:
            continue
        text = source.read_text(encoding="utf-8")
        assert "wishlist" not in text, f"{source} mentions wishlist"


# --- The wishlist page ------------------------------------------------------


def list_page(client):
    return client.get(reverse("wishlist:list"))


def test_list_shows_only_own_items_newest_first(
    client, customer, other_customer, product, unavailable_product, featured_product
):
    # Saved first but backdated less, so pk order and date order disagree.
    newest = WishlistItem.objects.add(customer, unavailable_product)
    oldest = WishlistItem.objects.add(customer, product)
    newest.created_at = timezone.now() - timedelta(days=1)
    newest.save()
    oldest.created_at = timezone.now() - timedelta(days=5)
    oldest.save()
    WishlistItem.objects.add(other_customer, featured_product)
    client.force_login(customer)

    response = list_page(client)

    assert list(response.context["items"]) == [newest, oldest]


def test_list_loads_products_without_a_query_per_row(
    client, customer, product, unavailable_product, featured_product
):
    client.force_login(customer)
    WishlistItem.objects.add(customer, product)
    with CaptureQueriesContext(connection) as one_item:
        list_page(client)

    WishlistItem.objects.add(customer, unavailable_product)
    WishlistItem.objects.add(customer, featured_product)
    with CaptureQueriesContext(connection) as three_items:
        list_page(client)

    assert len(three_items) == len(one_item)


def test_product_that_becomes_unavailable_stays_listed_with_a_badge(
    client, customer, product, featured_product
):
    WishlistItem.objects.add(customer, product)
    WishlistItem.objects.add(customer, featured_product)
    client.force_login(customer)
    assert "Unavailable" not in list_page(client).content.decode()

    product.is_available = False
    product.save()
    response = list_page(client)

    assertContains(response, product.name)
    assertContains(response, featured_product.name)
    assertContains(response, "Unavailable", count=1)


def test_list_requires_sign_in(client, db):
    response = list_page(client)

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == (
        f"{reverse('accounts:login')}?next={reverse('wishlist:list')}"
    )


@pytest.mark.parametrize("fixture", ["customer", "staff_user", "superuser"])
def test_list_is_open_to_every_signed_in_role(client, request, fixture):
    client.force_login(request.getfixturevalue(fixture))

    assert list_page(client).status_code == HTTPStatus.OK


def test_list_row_shows_image_linked_name_and_price(client, customer, product):
    WishlistItem.objects.add(customer, product)
    client.force_login(customer)

    response = list_page(client)

    assertContains(response, f'src="{product.image_url}"')
    assertContains(response, f'href="{product.get_absolute_url()}" class="link-hover"')
    assertContains(response, "$349.99")
    assertNotContains(response, "Unavailable")


def test_deleted_product_disappears_from_the_list(client, customer, product):
    WishlistItem.objects.add(customer, product)
    product.delete()
    client.force_login(customer)

    response = list_page(client)

    assert list(response.context["items"]) == []
    assertNotContains(response, product.name)


def test_empty_list_shows_the_empty_state(client, customer):
    client.force_login(customer)

    response = list_page(client)

    assertContains(response, "Your wishlist is empty")
    assertContains(response, f'href="{reverse("products:catalog")}" class="btn')


def test_list_has_no_remove_controls(client, customer, product):
    WishlistItem.objects.add(customer, product)
    client.force_login(customer)

    response = list_page(client)

    assertNotContains(response, remove_url(product))
    assertNotContains(response, "hx-post")


def test_navbar_shows_wishlist_link_when_signed_in(client, customer):
    client.force_login(customer)

    response = client.get(reverse("products:catalog"))

    assertContains(response, f'href="{reverse("wishlist:list")}"')


def test_navbar_hides_wishlist_link_when_signed_out(client, db):
    response = client.get(reverse("products:catalog"))

    assertNotContains(response, f'href="{reverse("wishlist:list")}"')
