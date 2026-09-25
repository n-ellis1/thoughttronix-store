"""The checkout form — the codebase's showcase of declarative validation.

Every rule is visible at its field declaration, in the style of data
annotations: field types validate (``EmailField``), field arguments
validate (``required``, ``max_length``, ``ChoiceField``), and the
``validators=[...]`` list carries the rest. No ``clean_*`` methods
and no ``clean()`` — none of its current rules need imperative validation.
"""

from django import forms
from django.core.validators import RegexValidator

from .models import Address, Order
from .validators import (
    US_STATES,
    validate_card_number,
    validate_expiry,
    zip_validator,
)

cvv_validator = RegexValidator(r"^\d{3,4}$", "Enter the 3- or 4-digit CVV.")


def style_widgets(form):
    """Give every widget its DaisyUI class — forms style themselves."""
    for field in form.fields.values():
        widget = field.widget
        if isinstance(widget, forms.CheckboxInput):
            widget.attrs["class"] = "checkbox checkbox-primary"
        elif isinstance(widget, forms.Select):
            widget.attrs["class"] = "select w-full"
        else:
            widget.attrs["class"] = "input w-full"


class CheckoutForm(forms.Form):
    """One page, one POST: contact, shipping, billing, payment."""

    email = forms.EmailField(label="Email")

    shipping_name = forms.CharField(label="Full name", max_length=100)
    shipping_street = forms.CharField(label="Street address", max_length=200)
    shipping_line2 = forms.CharField(
        label="Apt, suite, etc. (optional)", max_length=200, required=False
    )
    shipping_city = forms.CharField(label="City", max_length=100)
    shipping_state = forms.ChoiceField(label="State", choices=US_STATES)
    shipping_zip = forms.CharField(
        label="ZIP code", max_length=10, validators=[zip_validator]
    )

    billing_name = forms.CharField(label="Full name", max_length=100)
    billing_street = forms.CharField(label="Street address", max_length=200)
    billing_line2 = forms.CharField(
        label="Apt, suite, etc. (optional)", max_length=200, required=False
    )
    billing_city = forms.CharField(label="City", max_length=100)
    billing_state = forms.ChoiceField(label="State", choices=US_STATES)
    billing_zip = forms.CharField(
        label="ZIP code", max_length=10, validators=[zip_validator]
    )

    card_number = forms.CharField(
        label="Card number", max_length=23, validators=[validate_card_number]
    )
    card_expiry = forms.CharField(
        label="Expiry (MM/YY)", max_length=5, validators=[validate_expiry]
    )
    card_cvv = forms.CharField(label="CVV", max_length=4, validators=[cvv_validator])

    # Ticked boxes save that section to the customer's address book once
    # the order is placed. The view sets their starting state.
    save_shipping_address = forms.BooleanField(
        label="Save this address to my account", required=False
    )
    save_billing_address = forms.BooleanField(
        label="Save this address to my account", required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_widgets(self)

    # Field groups for the template — the form owns its own structure.

    def shipping_fields(self):
        return [self[name] for name in self.fields if name.startswith("shipping_")]

    def billing_fields(self):
        return [self[name] for name in self.fields if name.startswith("billing_")]

    def card_fields(self):
        return [self[name] for name in self.fields if name.startswith("card_")]


class AddressForm(forms.ModelForm):
    """Add or edit a saved address on My Addresses.

    Its rules come from the ``Address`` model fields, which declare the
    same ``US_STATES`` and ``zip_validator`` that ``CheckoutForm`` does.
    """

    class Meta:
        model = Address
        fields = Address.FIELDS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_widgets(self)


class OrderStatusForm(forms.ModelForm):
    """The back-office status dropdown — any of the four states, anytime.

    Guarding the workflow (no un-cancelling, no re-shipping a delivered
    order) is deliberately left as a student exercise.
    """

    class Meta:
        model = Order
        fields = ["status"]
        widgets = {"status": forms.Select(attrs={"class": "select"})}
