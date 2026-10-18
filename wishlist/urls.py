from django.urls import path

from . import views

app_name = "wishlist"

urlpatterns = [
    path("wishlist/", views.WishlistView.as_view(), name="list"),
    # HTMX endpoints, not public pages — pks, as the cart's add endpoint uses.
    path("wishlist/add/<int:pk>/", views.AddToWishlistView.as_view(), name="add"),
    path(
        "wishlist/remove/<int:pk>/",
        views.RemoveFromWishlistView.as_view(),
        name="remove",
    ),
]
