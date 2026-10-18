from datetime import timedelta
from http import HTTPStatus
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.template.defaultfilters import date
from django.template.loader import render_to_string
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from pytest_django.asserts import assertContains, assertNotContains

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
