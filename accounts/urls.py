from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("login/", views.SignInView.as_view(), name="login"),
    path("logout/", views.SignOutView.as_view(), name="logout"),
    path("password-reset/", views.ResetRequestView.as_view(), name="password_reset"),
    path(
        "password-reset/sent/",
        views.ResetSentView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password-reset/<uidb64>/<token>/",
        views.ResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path("security/", views.SecurityView.as_view(), name="security"),
    path("security/email/", views.EmailChangeView.as_view(), name="email_change"),
    path(
        "security/email/resend/", views.EmailResendView.as_view(), name="email_resend"
    ),
    path(
        "security/email/cancel/", views.EmailCancelView.as_view(), name="email_cancel"
    ),
    path(
        "security/email/confirm/<str:token>/",
        views.EmailConfirmView.as_view(),
        name="email_confirm",
    ),
    path(
        "security/password/",
        views.ChangePasswordView.as_view(),
        name="password_change",
    ),
]
