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
    path("reviews/<int:pk>/", views.ReviewCardView.as_view(), name="card"),
    path("reviews/<int:pk>/edit/", views.EditReviewView.as_view(), name="edit"),
    path("reviews/<int:pk>/delete/", views.DeleteReviewView.as_view(), name="delete"),
]
