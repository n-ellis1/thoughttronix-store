"""Access-control mixins.

Per the PRD, back-office views gate on ``is_staff`` via mixins — roles
are Django's own vocabulary, nothing else. HTMX endpoints that only
need sign-in use ``HtmxLoginRequiredMixin``.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse


class StaffRequiredMixin(UserPassesTestMixin):
    """Allow staff only: anonymous users are redirected to the login
    page; signed-in non-staff get 403 (``AccessMixin``'s default split)."""

    def test_func(self):
        return self.request.user.is_staff


class HtmxLoginRequiredMixin(LoginRequiredMixin):
    """``LoginRequiredMixin`` that sends HTMX requests to a full sign-in page.

    A plain redirect would be followed by HTMX and the sign-in page
    swapped into the target element. Instead, a signed-out HTMX request
    gets an ``HX-Redirect`` header, so HTMX loads the whole page.
    Requests without ``HX-Request`` behave exactly like
    ``LoginRequiredMixin``.
    """

    def get_login_next_url(self):
        """Where to return after an HTMX-triggered sign-in. Endpoints
        override this: their own URL is rarely a page worth returning to."""
        return self.request.get_full_path()

    def handle_no_permission(self):
        if self.request.headers.get("HX-Request") != "true":
            return super().handle_no_permission()
        login = redirect_to_login(
            self.get_login_next_url(),
            self.get_login_url(),
            self.get_redirect_field_name(),
        )
        response = HttpResponse()
        response["HX-Redirect"] = login.url
        return response
