from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordChangeForm,
    PasswordResetForm,
    SetPasswordForm,
    UserChangeForm,
    UserCreationForm,
)

from .models import User
from .ratelimit import confirmation_emails

EMAIL_TAKEN_MESSAGE = "That email address is already registered to another account."
CONFIRMATION_LIMIT_MESSAGE = (
    "You've requested several confirmation emails. "
    "Please wait before requesting another."
)


class SignupForm(UserCreationForm):
    """Django's stock signup fields plus a required email address.

    The email is not saved as the confirmed address: the view makes it the
    new account's *pending* address and emails a confirmation link. It is
    still checked, ignoring case, against other accounts' confirmed emails;
    pending addresses don't block it. The widgets carry DaisyUI classes
    because plain Django forms own their own styling here.
    """

    email = forms.EmailField(
        label="Email address",
        help_text="For account recovery and security notices. We'll send a "
        "link to confirm it.",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )

    field_order = ["username", "email", "password1", "password2"]

    class Meta(UserCreationForm.Meta):
        model = User

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"])
        if User.objects.email_taken(email):
            raise forms.ValidationError(EMAIL_TAKEN_MESSAGE)
        return email


class SignInForm(AuthenticationForm):
    """The stock authentication form, dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class ResetRequestForm(PasswordResetForm):
    """Django's reset-request form, dressed in DaisyUI.

    Its stock lookup already matches the *confirmed* email only, ignoring
    case, and skips inactive accounts and unusable passwords, so a pending
    address never receives a reset link.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].label = "Email address"
        self.fields["email"].widget.attrs["class"] = "input w-full"


class ResetPasswordForm(SetPasswordForm):
    """Set a new password from a reset link, no old password needed. The
    existing password validators still apply."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class ChangePasswordForm(PasswordChangeForm):
    """Django's password-change form, dressed in DaisyUI: the current
    password, then the new one twice, checked by the existing validators."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class EmailChangeForm(forms.Form):
    """Request a new confirmed email: the address plus the current password.

    The password check stops someone at an unattended, signed-in browser
    from redirecting the account's recovery email. An account that has
    spent its confirmation-email budget is refused, leaving any existing
    pending request as it was.
    """

    email = forms.EmailField(label="New email address")
    current_password = forms.CharField(
        label="Current password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"

    def clean_email(self):
        email = User.objects.normalize_email(self.cleaned_data["email"])
        if self.user.email and email.lower() == self.user.email.lower():
            raise forms.ValidationError("That's already your confirmed email.")
        if User.objects.email_taken(email, exclude=self.user):
            raise forms.ValidationError(EMAIL_TAKEN_MESSAGE)
        return email

    def clean_current_password(self):
        password = self.cleaned_data["current_password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Your current password is incorrect.")
        return password

    def clean(self):
        cleaned_data = super().clean()
        if confirmation_emails.is_limited(self.user.pk):
            raise forms.ValidationError(CONFIRMATION_LIMIT_MESSAGE)
        return cleaned_data


class AdminUserChangeForm(UserChangeForm):
    """The admin's user form, with the confirmed-email uniqueness rule as a
    field error rather than a database crash."""

    class Meta(UserChangeForm.Meta):
        model = User

    def clean_email(self):
        email = self.cleaned_data["email"]
        if email and User.objects.email_taken(email, exclude=self.instance):
            raise forms.ValidationError(EMAIL_TAKEN_MESSAGE)
        return email
