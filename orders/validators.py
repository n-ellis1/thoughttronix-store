"""Checkout's custom validators — small, pure, and unit-testable.

The card validators are plain functions that raise ``ValidationError``,
wired into ``CheckoutForm`` through ``validators=[...]`` so every rule
stays visible at the field declaration. The address rules (``US_STATES``,
``zip_validator``) live here too, because both ``CheckoutForm`` and the
``Address`` model declare them — and the model can't import from forms.
No form or view logic lives here.
"""

import datetime

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

US_STATES = [
    ("AL", "Alabama"),
    ("AK", "Alaska"),
    ("AZ", "Arizona"),
    ("AR", "Arkansas"),
    ("CA", "California"),
    ("CO", "Colorado"),
    ("CT", "Connecticut"),
    ("DE", "Delaware"),
    ("DC", "District of Columbia"),
    ("FL", "Florida"),
    ("GA", "Georgia"),
    ("HI", "Hawaii"),
    ("ID", "Idaho"),
    ("IL", "Illinois"),
    ("IN", "Indiana"),
    ("IA", "Iowa"),
    ("KS", "Kansas"),
    ("KY", "Kentucky"),
    ("LA", "Louisiana"),
    ("ME", "Maine"),
    ("MD", "Maryland"),
    ("MA", "Massachusetts"),
    ("MI", "Michigan"),
    ("MN", "Minnesota"),
    ("MS", "Mississippi"),
    ("MO", "Missouri"),
    ("MT", "Montana"),
    ("NE", "Nebraska"),
    ("NV", "Nevada"),
    ("NH", "New Hampshire"),
    ("NJ", "New Jersey"),
    ("NM", "New Mexico"),
    ("NY", "New York"),
    ("NC", "North Carolina"),
    ("ND", "North Dakota"),
    ("OH", "Ohio"),
    ("OK", "Oklahoma"),
    ("OR", "Oregon"),
    ("PA", "Pennsylvania"),
    ("RI", "Rhode Island"),
    ("SC", "South Carolina"),
    ("SD", "South Dakota"),
    ("TN", "Tennessee"),
    ("TX", "Texas"),
    ("UT", "Utah"),
    ("VT", "Vermont"),
    ("VA", "Virginia"),
    ("WA", "Washington"),
    ("WV", "West Virginia"),
    ("WI", "Wisconsin"),
    ("WY", "Wyoming"),
]

zip_validator = RegexValidator(
    r"^\d{5}(-\d{4})?$", "Enter a ZIP code like 79016 or 79016-1234."
)


def validate_card_number(value: str) -> None:
    """Reject a card number that fails the Luhn checksum.

    Spaces and hyphens are allowed, as people type them ("4242 4242
    4242 4242"). Standard test numbers such as 4242424242424242 and
    4111111111111111 pass; a single corrupted digit fails.
    """
    digits = value.replace(" ", "").replace("-", "")
    if not digits.isdigit() or not 13 <= len(digits) <= 19:
        raise ValidationError("Enter a valid card number.", code="card_number")

    total = 0
    for position, digit in enumerate(reversed(digits)):
        n = int(digit)
        if position % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    if total % 10 != 0:
        raise ValidationError("Enter a valid card number.", code="card_number")


def validate_expiry(value: str) -> None:
    """Reject an expiry that isn't MM/YY, or that is already in the past.

    The current month is still valid — a card expires at the end of its
    printed month, not the start.
    """
    try:
        month, year = value.split("/")
        if not (len(month) == 2 and month.isdigit() and len(year) == 2):
            raise ValueError
        expiry = datetime.date(2000 + int(year), int(month), 1)
    except (ValueError, TypeError):
        raise ValidationError(
            "Enter the expiry as MM/YY.", code="expiry_format"
        ) from None

    today = datetime.date.today()
    if expiry < today.replace(day=1):
        raise ValidationError("This card has expired.", code="expiry_past")
