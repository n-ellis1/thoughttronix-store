import secrets
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, UserManager
from django.core import signing
from django.db import IntegrityError, models, transaction
from django.db.models.functions import Lower
from django.utils import timezone

EMAIL_CONFIRM_SALT = "accounts.email-confirm"

# Confirmation links stop working this long after they were sent.
EMAIL_LINK_LIFETIME = timedelta(hours=24)

PENDING_EMAIL_FIELDS = ["pending_email", "email_token", "email_link_sent_at"]


class EmailAlreadyConfirmed(Exception):
    """Another account confirmed the pending address first."""


class StoreUserManager(UserManager):
    def email_taken(self, email, exclude=None):
        """Has another account already confirmed ``email``, ignoring case?

        Only confirmed addresses count: pending addresses reserve nothing.
        """
        accounts = self.filter(email__iexact=email).exclude(email="")
        if exclude is not None and exclude.pk:
            accounts = accounts.exclude(pk=exclude.pk)
        return accounts.exists()

    def for_email_token(self, token):
        """The account a confirmation link belongs to, or None.

        None covers every link that no longer works: tampered, expired,
        replaced by a newer link, canceled, or already used.
        """
        try:
            data = signing.loads(token, salt=EMAIL_CONFIRM_SALT)
        except signing.BadSignature:
            return None
        user = (
            self.filter(pk=data.get("user"), email_token=data.get("nonce"))
            .exclude(email_token="")
            .exclude(pending_email="")
            .first()
        )
        if user is None or user.email_link_expired:
            return None
        return user


class User(AbstractUser):
    """The store's user model.

    Roles use Django's own vocabulary and nothing else: customers are
    plain users, employees are ``is_staff``, the admin is ``is_superuser``.

    ``email`` is the *confirmed* address (blank means none). An add or
    change request waits in ``pending_email`` until its link is clicked;
    ``email_token`` changes with every request so only the newest link
    works.
    """

    # Nullable per the PRD: an absent job title is unknown, not empty.
    job_title = models.CharField(max_length=150, null=True, blank=True)  # noqa: DJ001
    pending_email = models.EmailField(blank=True)
    email_token = models.CharField(max_length=64, blank=True)
    email_link_sent_at = models.DateTimeField(null=True, blank=True)

    objects = StoreUserManager()

    class Meta(AbstractUser.Meta):
        constraints = [
            # Confirmed emails are unique ignoring case; blanks are exempt.
            models.UniqueConstraint(
                Lower("email"),
                condition=~models.Q(email=""),
                name="accounts_user_email_ci_unique",
                violation_error_message="A user with that email address already exists.",
            ),
        ]

    @property
    def email_link_expired(self):
        return (
            self.email_link_sent_at is None
            or timezone.now() > self.email_link_sent_at + EMAIL_LINK_LIFETIME
        )

    def request_email_change(self, new_email):
        """Make ``new_email`` the pending address and return its link token.

        Replaces any earlier request, so earlier links stop working. The
        confirmed address is untouched until the link is clicked.
        """
        self.pending_email = new_email
        self.email_token = secrets.token_urlsafe(24)
        self.email_link_sent_at = timezone.now()
        self.save(update_fields=PENDING_EMAIL_FIELDS)
        return signing.dumps(
            {"user": self.pk, "nonce": self.email_token}, salt=EMAIL_CONFIRM_SALT
        )

    def clear_pending_email(self, save=True):
        """Drop the pending request; any outstanding link stops working."""
        self.pending_email = ""
        self.email_token = ""
        self.email_link_sent_at = None
        if save:
            self.save(update_fields=PENDING_EMAIL_FIELDS)

    def confirm_pending_email(self):
        """Promote the pending address to the confirmed one.

        Returns the previous confirmed address ("" if there was none).
        Either way the pending request is cleared, so the link can't be
        used twice. If another account has confirmed the address first,
        the existing confirmed email is kept and ``EmailAlreadyConfirmed``
        is raised.
        """
        new_email, old_email = self.pending_email, self.email
        self.clear_pending_email(save=False)
        if not type(self).objects.email_taken(new_email, exclude=self):
            self.email = new_email
            try:
                with transaction.atomic():
                    self.save(update_fields=["email", *PENDING_EMAIL_FIELDS])
            except IntegrityError:
                # Lost a race: another account confirmed it just now.
                self.email = old_email
            else:
                return old_email
        self.save(update_fields=PENDING_EMAIL_FIELDS)
        raise EmailAlreadyConfirmed(new_email)
