from django.urls import path

from . import views

app_name = "reviews"

urlpatterns = [
    # HTMX endpoints, not public pages — pks, as the wishlist and cart use.
    path(
        "reviews/create/<int:pk>/",
        views.CreateReviewView.as_view(),
        name="create",
    ),
]
