from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserChangeForm,
    UserCreationForm,
)

from .models import User

EMAIL_TAKEN_MESSAGE = "That email address is already registered to another account."


class SignupForm(UserCreationForm):
    """Django's stock signup fields — username plus password and confirmation.

    No email: signing up asks for the minimum. The widgets carry DaisyUI
    classes because plain Django forms own their own styling here.
    """

    class Meta(UserCreationForm.Meta):
        model = User

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class SignInForm(AuthenticationForm):
    """The stock authentication form, dressed in DaisyUI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "input w-full"


class EmailChangeForm(forms.Form):
    """Request a new confirmed email: the address plus the current password.

    The password check stops someone at an unattended, signed-in browser
    from redirecting the account's recovery email.
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
