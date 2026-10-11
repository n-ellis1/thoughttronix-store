from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", views.SignOutView.as_view(), name="logout"),
    path("security/", views.SecurityView.as_view(), name="security"),
    path("security/email/", views.EmailChangeView.as_view(), name="email_change"),
    path(
        "security/email/confirm/<str:token>/",
        views.EmailConfirmView.as_view(),
        name="email_confirm",
    ),
]
