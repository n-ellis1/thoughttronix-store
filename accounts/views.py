from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, TemplateView, View

from .emails import (
    send_email_changed_notice,
    send_email_confirmation,
    send_password_reset_notice,
)
from .forms import (
    CONFIRMATION_LIMIT_MESSAGE,
    EmailChangeForm,
    ResetPasswordForm,
    ResetRequestForm,
    SignInForm,
    SignupForm,
)
from .models import EmailAlreadyConfirmed, User
from .ratelimit import confirmation_emails

CONTACT_SUPPORT_MESSAGE = (
    "Password management isn't available for your account. Please contact support."
)


class SignupView(SuccessMessageMixin, CreateView):
    """Create a customer account, then hand off to the login page.

    The signup email becomes the new account's pending address, and its
    confirmation link goes out right away and counts toward the new
    account's confirmation-email budget; the confirmed email starts blank. New users sign in themselves, confirmed or not — auto-login
    after signup is left as a student exercise.
    """

    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")
    success_message = (
        "Account created — you can now sign in. Check your inbox at %(email)s "
        "to confirm your email address."
    )

    def form_valid(self, form):
        response = super().form_valid(form)
        token = self.object.request_email_change(form.cleaned_data["email"])
        send_email_confirmation(self.request, self.object, token)
        return response


class SignInView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = SignInForm


class SignOutView(LogoutView):
    def post(self, request, *args, **kwargs):
        # Flash after super() has flushed the session, or the message
        # would be wiped along with it.
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have signed out.")
        return response


class ResetRequestView(PasswordResetView):
    """Email a one-hour reset link to the account with this confirmed email.

    Every submission lands on the same "sent" page, whether or not an
    email went out, so the page never reveals which addresses have
    accounts.
    """

    form_class = ResetRequestForm
    template_name = "accounts/password_reset.html"
    subject_template_name = "accounts/emails/password_reset_subject.txt"
    email_template_name = "accounts/emails/password_reset.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class ResetSentView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class ResetConfirmView(SuccessMessageMixin, PasswordResetConfirmView):
    """Set a new password from a reset link. Public on purpose.

    The link works once: the new password retires it. Nobody is signed in
    afterward, and changing the password signs out every existing session.
    A notice goes to the confirmed email.
    """

    form_class = ResetPasswordForm
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:login")
    success_message = (
        "Your password has been reset. Please sign in with your new password."
    )

    def form_valid(self, form):
        response = super().form_valid(form)
        send_password_reset_notice(self.request, self.user)
        return response


class SecurityView(LoginRequiredMixin, TemplateView):
    """The Account Security Center overview, open to every signed-in user.

    The template reads the confirmed email and password state straight off
    ``request.user``.
    """

    template_name = "accounts/security.html"


class EmailChangeView(LoginRequiredMixin, FormView):
    """Request an add or change of the confirmed email.

    The form needs the current password, so accounts without a usable one
    are sent back to the overview with the contact-support message.
    """

    form_class = EmailChangeForm
    template_name = "accounts/email_change.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_usable_password():
            messages.info(request, CONTACT_SUPPORT_MESSAGE)
            return redirect("accounts:security")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {"user": self.request.user, **super().get_form_kwargs()}

    def form_valid(self, form):
        user = self.request.user
        token = user.request_email_change(form.cleaned_data["email"])
        send_email_confirmation(self.request, user, token)
        messages.success(
            self.request,
            f"We sent a confirmation link to {user.pending_email}. "
            "Click it within 24 hours to finish. Your current email stays "
            "in place until then.",
        )
        return redirect("accounts:security")


class PendingEmailActionView(LoginRequiredMixin, View):
    """POST-only base for acting on the signed-in user's pending email.

    Open to accounts without a usable password too: these actions don't
    need the current password. With nothing pending, the user is sent
    back to the overview with a harmless message.
    """

    def post(self, request):
        if not request.user.pending_email:
            messages.info(request, "You have no pending email change.")
        else:
            self.act(request.user)
        return redirect("accounts:security")

    def act(self, user):
        raise NotImplementedError


class EmailResendView(PendingEmailActionView):
    def act(self, user):
        if confirmation_emails.is_limited(user.pk):
            messages.error(self.request, CONFIRMATION_LIMIT_MESSAGE)
            return
        token = user.resend_email_link()
        send_email_confirmation(self.request, user, token)
        messages.success(
            self.request,
            f"We sent a new confirmation link to {user.pending_email}. "
            "Earlier links no longer work.",
        )


class EmailCancelView(PendingEmailActionView):
    def act(self, user):
        pending = user.pending_email
        user.clear_pending_email()
        messages.success(
            self.request,
            f"Canceled the change to {pending}. Its confirmation link no longer works.",
        )


class EmailConfirmView(TemplateView):
    """Confirm a pending email from its link. Public on purpose.

    The link works in any browser, signed in or not, and never signs
    anyone in or changes who is signed in: it only acts on the account
    the link was issued for.
    """

    template_name = "accounts/email_confirm.html"

    def get(self, request, *args, **kwargs):
        user = User.objects.for_email_token(kwargs["token"])
        if user is None:
            return self.render_to_response(self.get_context_data(outcome="invalid"))
        try:
            old_email = user.confirm_pending_email()
        except EmailAlreadyConfirmed:
            return self.render_to_response(self.get_context_data(outcome="taken"))
        if old_email:
            send_email_changed_notice(request, user, old_email)
        return self.render_to_response(
            self.get_context_data(outcome="confirmed", email=user.email)
        )
