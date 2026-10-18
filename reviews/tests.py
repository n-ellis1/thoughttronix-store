import re
from datetime import timedelta
from http import HTTPStatus
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.template.defaultfilters import date
from django.template.loader import render_to_string
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertContains, assertNotContains

from orders.models import Order, OrderItem

from .forms import ReviewForm
from .models import Review


@pytest.fixture
def dana(db):
    """A named buyer whose username must never appear publicly."""
    return get_user_model().objects.create_user(
        username="dcole_77", password="dana123", first_name="Dana", last_name="Cole"
    )


@pytest.fixture
def superuser(db):
    return get_user_model().objects.create_superuser(
        username="admin", password="admin123"
    )


def make_review(user, product, rating=4, comment="Does what it says.", days_ago=0):
    return Review.objects.create(
        user=user,
        product=product,
        rating=rating,
        comment=comment,
        created_at=timezone.now() - timedelta(days=days_ago),
    )


def make_order(user, product, status=Order.Status.PLACED):
    """An order of one ``product`` by ``user``, in the given status."""
    order = Order.objects.create(
        user=user,
        status=status,
        subtotal=product.price,
        total=product.price,
        email="buyer@example.com",
        shipping_name="Casey Monroe",
        shipping_street="214 Synapse Street",
        shipping_city="Canyon",
        shipping_state="TX",
        shipping_zip="79015",
        billing_name="Casey Monroe",
        billing_street="214 Synapse Street",
        billing_city="Canyon",
        billing_state="TX",
        billing_zip="79015",
        card_last4="4242",
    )
    OrderItem.objects.create(
        order=order,
        product=product,
        product_name=product.name,
        unit_price=product.price,
        quantity=1,
    )
    return order


def mark_edited(review, editor):
    """Record an edit the way the PRD defines one: now, by ``editor``."""
    review.edited_at = timezone.now()
    review.edited_by = editor
    review.save()


# --- Model behavior ---------------------------------------------------------


@pytest.mark.parametrize(
    ("author", "editors", "delete_last_editor", "label"),
    [
        ("customer", [], False, ""),
        ("customer", ["customer"], False, "Edited"),
        ("staff_user", ["staff_user"], False, "Edited"),
        ("customer", ["staff_user"], False, "Edited by ThoughtTronix staff"),
        ("customer", ["staff_user", "customer"], False, "Edited"),
        ("customer", ["staff_user"], True, "Edited"),
    ],
    ids=[
        "never-edited",
        "author-edit",
        "staff-editing-own",
        "staff-editing-someone-elses",
        "author-again-after-staff",
        "last-editor-deleted",
    ],
)
def test_edit_label(request, product, author, editors, delete_last_editor, label):
    review = make_review(request.getfixturevalue(author), product)
    for name in editors:
        mark_edited(review, request.getfixturevalue(name))
    if delete_last_editor:
        review.edited_by.delete()
    review.refresh_from_db()

    assert review.edit_label == label


def test_summary_rounds_a_half_star_average_up(customer, staff_user, product):
    """4.5 shows five stars; Python's own round() would give four."""
    make_review(customer, product, rating=5)
    make_review(staff_user, product, rating=4)

    summary = Review.objects.summary_for(product)

    assert summary["average"] == 4.5
    assert summary["count"] == 2
    assert summary["stars"] == 5


def test_summary_rounds_below_half_down(customer, staff_user, dana, product):
    make_review(customer, product, rating=5)
    make_review(staff_user, product, rating=4)
    make_review(dana, product, rating=2)

    summary = Review.objects.summary_for(product)

    assert summary["count"] == 3
    assert summary["average"] == pytest.approx(11 / 3)
    assert summary["stars"] == 4


def test_summary_with_no_reviews(product):
    assert Review.objects.summary_for(product) == {
        "average": None,
        "count": 0,
        "stars": 0,
    }


def test_summary_counts_only_that_product(customer, product, unavailable_product):
    make_review(customer, product, rating=5)
    make_review(customer, unavailable_product, rating=1)

    summary = Review.objects.summary_for(product)

    assert (summary["average"], summary["count"]) == (5, 1)


def test_summary_is_one_query(customer, staff_user, product, django_assert_num_queries):
    make_review(customer, product)
    make_review(staff_user, product)

    with django_assert_num_queries(1):
        Review.objects.summary_for(product)


@pytest.mark.parametrize(
    ("buyer", "status", "purchased"),
    [
        ("customer", Order.Status.PLACED, True),
        ("customer", Order.Status.SHIPPED, True),
        ("customer", Order.Status.DELIVERED, True),
        ("customer", Order.Status.CANCELLED, False),
        ("dana", Order.Status.DELIVERED, False),
        (None, None, False),
    ],
    ids=["placed", "shipped", "delivered", "cancelled", "another-user", "no-orders"],
)
def test_has_purchased(
    request, customer, product, unavailable_product, buyer, status, purchased
):
    """Only the customer's own non-cancelled orders of *this* product count."""
    make_order(customer, unavailable_product)  # a different product never counts
    if buyer:
        make_order(request.getfixturevalue(buyer), product, status)

    assert Review.objects.has_purchased(customer, product) is purchased


def test_str(customer, product):
    assert str(make_review(customer, product)) == (
        "customer's review of Seraphine Home Hub"
    )


def test_user_product_pair_is_unique(customer, product):
    make_review(customer, product)

    with pytest.raises(IntegrityError), transaction.atomic():
        make_review(customer, product, rating=1)


@pytest.mark.parametrize("rating", [0, 6])
def test_rating_outside_one_to_five_is_rejected_by_the_database(
    customer, product, rating
):
    with pytest.raises(IntegrityError), transaction.atomic():
        make_review(customer, product, rating=rating)


@pytest.mark.parametrize("rating", [1, 5])
def test_rating_bounds_are_allowed(customer, product, rating):
    assert make_review(customer, product, rating=rating).rating == rating


def test_edited_by_without_edited_at_is_rejected_by_the_database(
    customer, staff_user, product
):
    review = make_review(customer, product)
    review.edited_by = staff_user

    with pytest.raises(IntegrityError), transaction.atomic():
        review.save()


def test_ordering_is_newest_first_with_pk_tiebreak(customer, staff_user, dana, product):
    oldest = make_review(dana, product, days_ago=7)
    moment = timezone.now()
    first_tied = Review.objects.create(
        user=customer, product=product, rating=4, comment="a", created_at=moment
    )
    second_tied = Review.objects.create(
        user=staff_user, product=product, rating=4, comment="b", created_at=moment
    )

    assert list(Review.objects.all()) == [second_tied, first_tied, oldest]


def test_editing_never_changes_position(customer, staff_user, dana, product):
    oldest = make_review(dana, product, days_ago=7)
    middle = make_review(customer, product, days_ago=3)
    newest = make_review(staff_user, product)

    mark_edited(middle, staff_user)

    assert list(Review.objects.all()) == [newest, middle, oldest]


def test_deleting_a_product_deletes_its_reviews(customer, product):
    make_review(customer, product)

    product.delete()

    assert Review.objects.count() == 0


def test_deleting_a_user_deletes_their_reviews(customer, product):
    make_review(customer, product)

    customer.delete()

    assert Review.objects.count() == 0


def test_deleting_the_last_editor_keeps_the_review_as_edited(
    customer, staff_user, product
):
    review = make_review(customer, product)
    mark_edited(review, staff_user)
    edited_at = review.edited_at

    staff_user.delete()
    review.refresh_from_db()

    assert review.edited_by is None
    assert review.edited_at == edited_at
    assert review.edit_label == "Edited"


def test_for_product_loads_both_people_in_one_query(
    customer, staff_user, product, unavailable_product, django_assert_num_queries
):
    mark_edited(make_review(customer, product), staff_user)
    make_review(staff_user, unavailable_product)

    with django_assert_num_queries(1):
        reviews = list(Review.objects.for_product(product))
        assert [(r.user.username, r.edited_by.username) for r in reviews] == [
            ("customer", "employee")
        ]


# --- The stars ----------------------------------------------------------------


@pytest.mark.parametrize("value", [1, 3, 5])
def test_stars_light_the_given_star_and_label_the_rating(value):
    html = render_to_string("reviews/partials/_stars.html", {"value": value})

    stars = html.split('class="mask mask-star-2')[1:]
    assert len(stars) == 5
    assert ["aria-current" in star for star in stars] == [
        n == value for n in range(1, 6)
    ]
    assert f'aria-label="Rated {value} out of 5 stars"' in html


def test_stars_label_an_average_exactly():
    html = render_to_string(
        "reviews/partials/_stars.html", {"value": 4, "average": 11 / 3}
    )

    assert 'aria-label="Average rating 3.7 out of 5 stars"' in html


# --- The product detail page --------------------------------------------------


def detail(client, product):
    return client.get(product.get_absolute_url())


def test_product_with_no_reviews_shows_the_empty_state(client, product):
    response = detail(client, product)

    assertContains(response, 'id="reviews"')
    assertContains(response, "No reviews yet")
    assertNotContains(response, "Average rating")
    assertNotContains(response, "0 reviews")


def test_header_shows_rounded_stars_one_decimal_and_count(
    client, customer, staff_user, dana, product
):
    make_review(customer, product, rating=5)
    make_review(staff_user, product, rating=4)
    make_review(dana, product, rating=2)

    response = detail(client, product)

    assert response.context["summary"]["stars"] == 4
    assertContains(response, 'aria-label="Average rating 3.7 out of 5 stars"')
    assertContains(response, '<span class="text-lg font-semibold">3.7</span>')
    assertContains(response, "3 reviews")
    assertNotContains(response, "No reviews yet")


def test_header_shows_five_stars_for_a_four_and_a_half_average(
    client, customer, staff_user, product
):
    make_review(customer, product, rating=5)
    make_review(staff_user, product, rating=4)

    response = detail(client, product)

    assert response.context["summary"]["stars"] == 5
    assertContains(response, '<span class="text-lg font-semibold">4.5</span>')
    assertContains(response, "2 reviews")


def test_header_count_is_singular_for_one_review(client, customer, product):
    make_review(customer, product, rating=4)

    response = detail(client, product)

    assertContains(response, "1 review<")
    assertContains(response, '<span class="text-lg font-semibold">4.0</span>')


def test_reviews_are_listed_newest_first(client, customer, staff_user, dana, product):
    make_review(dana, product, comment="Oldest thoughts", days_ago=7)
    make_review(customer, product, comment="Newest thoughts")
    make_review(staff_user, product, comment="Middle thoughts", days_ago=3)

    page = detail(client, product).content.decode()

    assert (
        page.index("Newest thoughts")
        < page.index("Middle thoughts")
        < page.index("Oldest thoughts")
    )


def test_card_shows_stars_public_name_date_and_never_the_username(
    client, dana, product
):
    review = make_review(dana, product, rating=2, days_ago=3)

    response = detail(client, product)

    assertContains(response, 'aria-label="Rated 2 out of 5 stars"')
    assertContains(response, "Dana C.")
    assertContains(response, date(timezone.localtime(review.created_at), "M j, Y"))
    assertNotContains(response, "dcole_77")
    assertNotContains(response, "Dana Cole")


def test_reviewer_without_a_first_name_shows_the_fallback(client, customer, product):
    make_review(customer, product)

    response = detail(client, product)

    assertContains(response, "ThoughtTronix customer")


def test_comment_keeps_line_breaks(client, dana, product):
    make_review(dana, product, comment="Line one.\nLine two.")

    assertContains(detail(client, product), "Line one.<br>Line two.")


def test_comment_is_escaped(client, dana, product):
    make_review(dana, product, comment="<script>alert('hi')</script>")

    response = detail(client, product)

    assertContains(response, "&lt;script&gt;")
    assertNotContains(response, "<script>alert")


@pytest.mark.parametrize(
    ("editor", "label"),
    [
        (None, None),
        ("dana", "Edited"),
        ("staff_user", "Edited by ThoughtTronix staff"),
    ],
    ids=["never-edited", "author-edit", "staff-edit"],
)
def test_card_shows_its_edit_label(request, client, dana, product, editor, label):
    review = make_review(dana, product)
    if editor:
        mark_edited(review, request.getfixturevalue(editor))

    response = detail(client, product)

    if label:
        assertContains(response, f">{label}</span>")
    else:
        assertNotContains(response, ">Edited")


def test_unavailable_product_still_shows_its_reviews(client, dana, unavailable_product):
    make_review(dana, unavailable_product, comment="Still listening.")

    response = detail(client, unavailable_product)

    assertContains(response, "Still listening.")
    assertContains(response, "1 review<")


def test_section_query_count_does_not_grow_with_reviews(
    client, customer, staff_user, dana, product
):
    make_review(dana, product)
    with CaptureQueriesContext(connection) as one_review:
        detail(client, product)

    mark_edited(make_review(customer, product), staff_user)
    mark_edited(make_review(staff_user, product), customer)
    with CaptureQueriesContext(connection) as three_reviews:
        detail(client, product)

    assert len(three_reviews) == len(one_review)


# --- Writing a review -----------------------------------------------------------


def create_url(product):
    return reverse("reviews:create", kwargs={"pk": product.pk})


def post_review(client, product, rating="4", comment="Love it!"):
    """Submit the create form the way HTMX does; None leaves a field out."""
    data = {"rating": rating, "comment": comment}
    return client.post(
        create_url(product),
        {name: value for name, value in data.items() if value is not None},
        headers={"HX-Request": "true"},
    )


def checked_rating(response):
    """The value of the checked star radio in the response, or None."""
    for star in re.findall(r"<input\b[^>]*>", response.content.decode()):
        if 'name="rating"' in star and re.search(r"\bchecked\b", star):
            return re.search(r'value="(\d+)"', star).group(1)
    return None


def assert_form_only(response):
    """The response is the review form alone — not the section, not a page."""
    names = [template.name for template in response.templates]
    assert "reviews/partials/_form.html" in names
    assert "reviews/partials/_section.html" not in names
    assert "base.html" not in names


def test_invalid_review_returns_only_the_form_retargeted_with_input_kept(
    client, customer, product
):
    """A whitespace-only comment is empty: the form comes back on its own,
    swapped over itself, so nothing else on the page changes."""
    make_order(customer, product)
    client.force_login(customer)

    response = post_review(client, product, rating="4", comment="   ")

    assert response.status_code == HTTPStatus.OK
    assert_form_only(response)
    assertContains(response, "Write a comment — even a short one.")
    assert checked_rating(response) == "4"
    assert response.headers.get("HX-Retarget") == "#review-form"
    assert response.headers.get("HX-Reswap") == "outerHTML"
    assert Review.objects.count() == 0


def test_second_review_gets_the_already_reviewed_error_with_input_kept(
    customer, product
):
    """A stale tab's submit is neither refused nor allowed to overwrite.

    A server error comes back as a 500 response rather than raising, so
    a crash fails the status assertion like any other wrong answer.
    """
    make_order(customer, product)
    existing = make_review(customer, product, rating=5, comment="Original words.")
    client = Client(raise_request_exception=False)
    client.force_login(customer)

    response = post_review(client, product, rating="2", comment="Second thoughts.")

    assert response.status_code == HTTPStatus.OK
    assertContains(response, "already reviewed this product. Edit your review instead.")
    assertContains(response, "Second thoughts.")
    assert checked_rating(response) == "2"
    existing.refresh_from_db()
    assert (existing.rating, existing.comment) == (5, "Original words.")
    assert Review.objects.count() == 1


def test_simultaneous_duplicate_gets_the_same_error(
    client, customer, product, monkeypatch
):
    """Both submits of a true race pass clean(); the database refuses one."""
    make_order(customer, product)
    existing = make_review(customer, product, rating=5, comment="Original words.")
    # As if this submit had been validated before the other one was saved.
    monkeypatch.setattr(ReviewForm, "clean", lambda form: form.cleaned_data)
    client.force_login(customer)

    response = post_review(client, product, rating="2", comment="Second thoughts.")

    assert response.status_code == HTTPStatus.OK
    assert_form_only(response)
    assertContains(response, "already reviewed this product. Edit your review instead.")
    assertContains(response, "Second thoughts.")
    assert response["HX-Retarget"] == "#review-form"
    existing.refresh_from_db()
    assert (existing.rating, existing.comment) == (5, "Original words.")
    assert Review.objects.count() == 1


def test_buyer_review_is_saved_and_the_section_returned_with_it_pinned(
    client, customer, dana, product
):
    make_order(customer, product)
    make_review(dana, product, rating=2, comment="Not for me.")
    customer.first_name, customer.last_name = "Casey", "Monroe"
    customer.save()
    client.force_login(customer)

    response = post_review(client, product, rating="4", comment="Love it!")

    assert response.status_code == HTTPStatus.OK
    names = [template.name for template in response.templates]
    assert "reviews/partials/_section.html" in names
    assert "base.html" not in names
    assert "HX-Retarget" not in response
    review = Review.objects.get(user=customer)
    assert (review.product, review.rating, review.comment) == (product, 4, "Love it!")
    assert review.edited_at is None
    page = response.content.decode()
    assert '<section id="reviews"' in page
    assert "2 reviews" in page
    assert '<span class="text-lg font-semibold">3.0</span>' in page
    assert (
        page.index("Your review") < page.index("Love it!") < page.index("Not for me.")
    )
    assert "Casey M." in page
    assert 'id="review-form"' not in page


@pytest.mark.parametrize(
    "status",
    [None, Order.Status.CANCELLED],
    ids=["never-bought", "cancelled-only"],
)
def test_review_without_a_qualifying_purchase_is_refused(
    client, customer, product, status
):
    if status:
        make_order(customer, product, status)
    client.force_login(customer)

    response = post_review(client, product)

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert Review.objects.count() == 0


def test_purchase_is_checked_before_the_form(client, customer, product):
    """A non-buyer's invalid submit is still a 403, not form errors."""
    client.force_login(customer)

    response = post_review(client, product, rating=None, comment="   ")

    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.parametrize(
    ("rating", "comment", "error", "kept_rating"),
    [
        (None, "Love it!", "Pick a star rating.", None),
        ("0", "Love it!", "Pick a rating from 1 to 5 stars.", None),
        ("6", "Love it!", "Pick a rating from 1 to 5 stars.", None),
        (
            "4",
            "x" * 2001,
            "Keep your comment to 2000 characters or fewer (it has 2001).",
            "4",
        ),
    ],
    ids=["missing-rating", "rating-0", "rating-6", "comment-2001-chars"],
)
def test_invalid_review_is_rejected_with_errors_and_input_kept(
    client, customer, product, rating, comment, error, kept_rating
):
    make_order(customer, product)
    client.force_login(customer)

    response = post_review(client, product, rating=rating, comment=comment)

    assert response.status_code == HTTPStatus.OK
    assert_form_only(response)
    assertContains(response, error)
    assertContains(response, comment)
    assert checked_rating(response) == kept_rating
    assert response["HX-Retarget"] == "#review-form"
    assert response["HX-Reswap"] == "outerHTML"
    assert Review.objects.count() == 0


def test_comment_of_exactly_2000_characters_is_accepted(client, customer, product):
    make_order(customer, product)
    client.force_login(customer)

    post_review(client, product, comment="x" * 2000)

    assert Review.objects.get().comment == "x" * 2000


def test_short_comment_is_accepted_and_stripped(client, customer, product):
    make_order(customer, product)
    client.force_login(customer)

    post_review(client, product, comment="  Love it!  ")

    assert Review.objects.get().comment == "Love it!"


def test_buyer_can_review_an_unavailable_product(client, customer, unavailable_product):
    make_order(customer, unavailable_product, Order.Status.DELIVERED)
    client.force_login(customer)

    response = post_review(client, unavailable_product)

    assert response.status_code == HTTPStatus.OK
    assert Review.objects.get().product == unavailable_product


def test_review_survives_a_later_cancellation(client, customer, product):
    order = make_order(customer, product)
    client.force_login(customer)
    post_review(client, product, comment="Written in good faith.")

    order.status = Order.Status.CANCELLED
    order.save()
    response = detail(client, product)

    assert Review.objects.count() == 1
    assertContains(response, "Your review")
    assertContains(response, "Written in good faith.")
    assertNotContains(response, "purchased this product")


def test_staff_follow_the_same_purchase_rule(client, staff_user, product):
    client.force_login(staff_user)

    refused = post_review(client, product)
    make_order(staff_user, product)
    accepted = post_review(client, product)

    assert refused.status_code == HTTPStatus.FORBIDDEN
    assert accepted.status_code == HTTPStatus.OK
    assert Review.objects.get().user == staff_user


def test_signed_out_htmx_post_gets_hx_redirect_and_saves_nothing(
    client, customer, product
):
    make_order(customer, product)

    response = post_review(client, product)

    assert response.status_code == HTTPStatus.OK
    assert response["HX-Redirect"] == (
        f"{reverse('accounts:login')}?next={product.get_absolute_url()}"
    )
    assert Review.objects.count() == 0


def test_signed_out_plain_post_redirects_to_sign_in_and_saves_nothing(client, product):
    response = client.post(create_url(product), {"rating": "4", "comment": "Hi"})

    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("accounts:login"))
    assert Review.objects.count() == 0


def test_unknown_product_404s(client, customer):
    client.force_login(customer)

    response = client.post(reverse("reviews:create", kwargs={"pk": 999}))

    assert response.status_code == HTTPStatus.NOT_FOUND


def test_get_is_rejected(client, customer, product):
    make_order(customer, product)
    client.force_login(customer)

    response = client.get(create_url(product))

    assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED


# --- The "your review" slot on the product page -------------------------------

NOTE = "Only customers who've purchased this product can review it."
SIGN_IN = "Sign in to write a review"


def slot_state(response):
    """Which of the slot's states the page shows: one of each, or a mix."""
    page = response.content.decode()
    shown = {
        "sign-in": SIGN_IN in page,
        "note": "purchased this product can review it" in page,
        "form": 'id="review-form"' in page,
        "own": "Your review" in page,
    }
    return [state for state, present in shown.items() if present]


def test_signed_out_slot_links_to_sign_in_and_back(client, product):
    response = detail(client, product)

    assert slot_state(response) == ["sign-in"]
    login = f"{reverse('accounts:login')}?next={product.get_absolute_url()}"
    assertContains(response, f'<a href="{login}"')


def test_signing_in_from_the_link_returns_to_the_product(client, customer, product):
    response = client.post(
        f"{reverse('accounts:login')}?next={product.get_absolute_url()}",
        {"username": "customer", "password": "customer123"},
    )

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == product.get_absolute_url()


@pytest.mark.parametrize(
    ("viewer", "status", "state"),
    [
        ("customer", None, "note"),
        ("customer", Order.Status.CANCELLED, "note"),
        ("customer", Order.Status.PLACED, "form"),
        ("customer", Order.Status.SHIPPED, "form"),
        ("customer", Order.Status.DELIVERED, "form"),
        ("staff_user", None, "note"),
        ("staff_user", Order.Status.DELIVERED, "form"),
    ],
    ids=[
        "never-bought",
        "cancelled-only",
        "placed",
        "shipped",
        "delivered",
        "staff-never-bought",
        "staff-bought",
    ],
)
@pytest.mark.parametrize("fixture", ["product", "unavailable_product"])
def test_signed_in_slot_follows_the_purchase_rule(
    request, client, viewer, status, state, fixture
):
    user = request.getfixturevalue(viewer)
    shown = request.getfixturevalue(fixture)
    if status:
        make_order(user, shown, status)
    client.force_login(user)

    response = detail(client, shown)

    assert slot_state(response) == [state]
    if state == "note":
        assertContains(response, NOTE)
        assertNotContains(response, create_url(shown))
    else:
        assertContains(response, f'hx-post="{create_url(shown)}"')


def test_create_form_offers_five_labelled_stars_and_disables_submit(
    client, customer, product
):
    make_order(customer, product)
    client.force_login(customer)

    response = detail(client, product)

    for stars in range(1, 6):
        assertContains(response, f'aria-label="{stars} star{"s" if stars > 1 else ""}"')
    assert checked_rating(response) is None
    assertContains(response, "hx-disabled-elt=\"find button[type='submit']\"")
    assertContains(response, 'hx-target="#reviews"')


def test_own_review_is_pinned_once_above_the_others(
    client, customer, staff_user, dana, product
):
    make_order(customer, product)
    make_review(dana, product, comment="Newest of all.")
    make_review(customer, product, comment="My own words.", days_ago=5)
    make_review(staff_user, product, comment="Middle of the pack.", days_ago=2)
    client.force_login(customer)

    response = detail(client, product)

    assert slot_state(response) == ["own"]
    assertContains(response, "My own words.", count=1)
    page = response.content.decode()
    assert (
        page.index("My own words.")
        < page.index("Newest of all.")
        < page.index("Middle of the pack.")
    )
    assertContains(response, "3 reviews")


def test_own_review_is_pinned_even_without_a_qualifying_purchase(
    client, customer, product
):
    make_review(customer, product, comment="From before the cancellation.")
    client.force_login(customer)

    assert slot_state(detail(client, product)) == ["own"]


def test_another_customers_review_is_never_pinned(client, customer, dana, product):
    make_order(customer, product)
    make_review(dana, product)
    client.force_login(customer)

    assert slot_state(detail(client, product)) == ["form"]


def test_signed_in_section_query_count_does_not_grow_with_reviews(
    client, customer, staff_user, dana, product
):
    make_order(customer, product)
    client.force_login(customer)
    make_review(dana, product)
    with CaptureQueriesContext(connection) as one_review:
        detail(client, product)

    mark_edited(make_review(staff_user, product), staff_user)
    with CaptureQueriesContext(connection) as two_reviews:
        detail(client, product)

    assert len(two_reviews) == len(one_review)


# --- The Django admin -----------------------------------------------------------


def test_admin_lists_and_searches_reviews(
    client, superuser, dana, customer, product, unavailable_product
):
    make_review(dana, product)
    make_review(customer, unavailable_product)
    client.force_login(superuser)
    changelist = reverse("admin:reviews_review_changelist")

    everything = client.get(changelist)
    by_username = client.get(changelist, {"q": "dcole"})
    by_product = client.get(changelist, {"q": "EchoPatch"})

    assert everything.status_code == HTTPStatus.OK
    for column in ("Product", "User", "Rating", "Created at"):
        assertContains(everything, column)
    assert [r.user for r in by_username.context["cl"].result_list] == [dana]
    assert [r.product for r in by_product.context["cl"].result_list] == [
        unavailable_product
    ]


# --- App boundaries -------------------------------------------------------------


def test_no_other_app_imports_reviews():
    """The seed command is exempt: it's where the apps are put together."""
    root = Path(__file__).resolve().parent.parent
    for app in ("accounts", "products", "orders", "dashboard", "wishlist"):
        for source in (root / app).rglob("*.py"):
            if "management" in source.parts:
                continue
            text = source.read_text(encoding="utf-8")
            assert "from reviews" not in text, f"{source} imports reviews"
            assert "import reviews" not in text, f"{source} imports reviews"
