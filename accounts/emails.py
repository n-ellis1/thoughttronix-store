"""Plain-text account emails.

Confirmation links go to the pending address; security notices go to the
confirmed (here: the previous confirmed) address only.
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse


def send_email_confirmation(request, user, token):
    """Email a confirmation link for ``user``'s pending address."""
    context = {
        "user": user,
        "confirm_url": request.build_absolute_uri(
            reverse("accounts:email_confirm", kwargs={"token": token})
        ),
    }
    send_mail(
        "Confirm your ThoughtTronix email address",
        render_to_string("accounts/emails/email_confirm.txt", context),
        None,
        [user.pending_email],
    )


def send_email_changed_notice(request, user, old_email):
    """Tell the previous confirmed address that the email was changed."""
    context = {
        "user": user,
        "security_url": request.build_absolute_uri(reverse("accounts:security")),
    }
    send_mail(
        "Your ThoughtTronix email address was changed",
        render_to_string("accounts/emails/email_changed.txt", context),
        None,
        [old_email],
    )
