"""The review form — it owns every rule a reviewer can break.

The view builds it around an unsaved ``Review`` that already carries
the user and product, so ``save()`` needs nothing else.
"""

from django import forms

from .models import RATING_CHOICES, Review

ALREADY_REVIEWED = "You've already reviewed this product. Edit your review instead."


class ReviewForm(forms.ModelForm):
    """A 1–5 star rating and a required comment of at most 2,000 characters.

    The comment is stripped, so whitespace alone counts as empty.
    """

    rating = forms.TypedChoiceField(
        choices=RATING_CHOICES,
        coerce=int,
        widget=forms.RadioSelect,
        error_messages={
            "required": "Pick a star rating.",
            "invalid_choice": "Pick a rating from 1 to 5 stars.",
        },
    )

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 4, "class": "textarea w-full"})
        }
        error_messages = {
            "comment": {
                "required": "Write a comment — even a short one.",
                "max_length": (
                    "Keep your comment to %(limit_value)d characters or fewer "
                    "(it has %(show_value)d)."
                ),
            }
        }

    def clean(self):
        """Refuse a second review of the same product, keeping the input.

        Django skips the (user, product) constraint here because neither
        is a form field, so the form checks it itself.
        """
        cleaned_data = super().clean()
        if Review.objects.filter(
            user=self.instance.user, product=self.instance.product
        ).exists():
            raise forms.ValidationError(ALREADY_REVIEWED, code="already_reviewed")
        return cleaned_data
