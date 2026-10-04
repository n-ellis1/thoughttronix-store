"""Back-office forms for the catalog models.

ModelForms inherit the models' own rules (name required, slug unique);
the explicit ``price`` declaration adds the one rule the model doesn't
carry — the price must be positive. Widgets get their DaisyUI classes
in one shared ``__init__`` loop, as on ``CheckoutForm``.

``ProductImageField`` validates and processes product image uploads: by
the time the form saves, an upload is a finished WebP file.
"""

import uuid
from decimal import Decimal
from io import BytesIO

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Category, Product, Tag

MB = 1024 * 1024
MAX_IMAGE_BYTES = 10 * MB
MAX_IMAGE_PIXELS = 50_000_000
MIN_IMAGE_SIDE = 600
MAX_IMAGE_EDGE = 1200
WEBP_QUALITY = 80

ALLOWED_IMAGE_FORMATS = ("JPEG", "PNG", "WEBP")

# File signatures of the allowed formats — tells "a damaged JPEG" apart
# from "not a JPEG at all" when Pillow can't identify the file.
IMAGE_SIGNATURES = (b"\xff\xd8\xff", b"\x89PNG\r\n\x1a\n")


def _has_image_signature(head: bytes) -> bool:
    is_webp = head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    return is_webp or head.startswith(IMAGE_SIGNATURES)


class ProductImageInput(forms.ClearableFileInput):
    """Django's clearable file input, restyled, with the store's wording."""

    template_name = "products/widgets/product_image_input.html"
    clear_checkbox_label = "Remove image and use the category placeholder"


class ProductImageField(forms.ImageField):
    """An image upload checked cheapest-first, then re-encoded as WebP.

    Checks run in order, and nothing is fully decoded until all of them
    pass: the byte size, then the header (format by content, not by
    extension; no animation; the pixel limits). Only then is the image
    decoded, turned upright from its EXIF orientation, shrunk to fit
    ``MAX_IMAGE_EDGE`` (never enlarged), and saved as WebP with no EXIF
    but with its colour profile. The cleaned value is that WebP file,
    named ``<uuid>.webp``.
    """

    widget = ProductImageInput
    default_error_messages = {
        "too_big": (
            "This image is too large (%(size)s MB). Upload a file 10 MB or smaller."
        ),
        "too_many_pixels": (
            "This image is too large (%(dimensions)s). "
            "Upload an image of 50 megapixels or fewer."
        ),
        "too_small": (
            "This image is too small (%(dimensions)s). "
            "Upload an image at least 600 pixels on each side."
        ),
        "invalid_image": "Upload a JPEG, PNG, or WebP image.",
        "animated": "Animated images aren't supported. Upload a still image.",
        "unreadable": (
            "This image couldn't be read. It may be damaged or incomplete. "
            "Try saving or exporting it again as a JPEG, PNG, or WebP."
        ),
    }

    def __init__(self, **kwargs):
        kwargs.setdefault(
            "help_text",
            "JPEG, PNG, or WebP · 10 MB or smaller · 50 megapixels or fewer · "
            "at least 600 × 600 pixels · animated images aren't supported · "
            "resized to 1200 px and saved as WebP.",
        )
        super().__init__(**kwargs)

    def widget_attrs(self, widget: forms.Widget) -> dict[str, str]:
        attrs = super().widget_attrs(widget)
        attrs["accept"] = "image/jpeg,image/png,image/webp"
        return attrs

    def to_python(self, data: UploadedFile | None) -> ContentFile | None:
        """Validate an upload and return it processed as a WebP file.

        Deliberately skips ``ImageField.to_python``, which fully decodes
        the image before any limit is checked.
        """
        upload = forms.FileField.to_python(self, data)
        if upload is None:
            return None

        if upload.size > MAX_IMAGE_BYTES:
            raise ValidationError(
                self.error_messages["too_big"],
                code="too_big",
                params={"size": f"{upload.size / MB:.1f}"},
            )

        if hasattr(upload, "temporary_file_path"):
            source = upload.temporary_file_path()
        else:
            upload.seek(0)
            source = BytesIO(upload.read())

        try:
            image = Image.open(source, formats=ALLOWED_IMAGE_FORMATS)
        except Image.DecompressionBombError as error:
            # Beyond Pillow's own limit it refuses at open, before we see a size.
            raise ValidationError(
                self.error_messages["too_many_pixels"],
                code="too_many_pixels",
                params={
                    "dimensions": f"over {2 * Image.MAX_IMAGE_PIXELS // 1_000_000} "
                    "megapixels"
                },
            ) from error
        except (UnidentifiedImageError, OSError) as error:
            upload.seek(0)
            if _has_image_signature(upload.read(12)):
                raise ValidationError(
                    self.error_messages["unreadable"], code="unreadable"
                ) from error
            raise ValidationError(
                self.error_messages["invalid_image"], code="invalid_image"
            ) from error

        with image:
            self._check_header(image)
            return self._process(image)

    def _check_header(self, image: Image.Image) -> None:
        """Reject on what the header says, before any pixel is decoded."""
        if image.format not in ALLOWED_IMAGE_FORMATS + ("MPO",):
            raise ValidationError(
                self.error_messages["invalid_image"], code="invalid_image"
            )
        # MPO is a JPEG with extra pictures (e.g. phone depth maps), not an
        # animation; only its first picture is used.
        if image.format != "MPO" and getattr(image, "is_animated", False):
            raise ValidationError(self.error_messages["animated"], code="animated")

        width, height = image.size
        dimensions = f"{width} × {height} pixels"
        if width * height > MAX_IMAGE_PIXELS:
            raise ValidationError(
                self.error_messages["too_many_pixels"],
                code="too_many_pixels",
                params={"dimensions": dimensions},
            )
        if min(width, height) < MIN_IMAGE_SIDE:
            raise ValidationError(
                self.error_messages["too_small"],
                code="too_small",
                params={"dimensions": dimensions},
            )

    def _process(self, image: Image.Image) -> ContentFile:
        """Decode, orient, resize and re-encode an image that passed every check."""
        icc_profile = image.info.get("icc_profile")
        try:
            image.load()
            image = ImageOps.exif_transpose(image)
            image.thumbnail((MAX_IMAGE_EDGE, MAX_IMAGE_EDGE))
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA" if image.has_transparency_data else "RGB")
            # An RGB profile still describes the converted pixels; a CMYK
            # or greyscale one wouldn't, so it's dropped.
            if icc_profile and icc_profile[16:20] != b"RGB ":
                icc_profile = None
            output = BytesIO()
            image.save(output, "WEBP", quality=WEBP_QUALITY, icc_profile=icc_profile)
        except Exception as error:
            # Whatever Pillow raised while decoding, the image can't be used.
            raise ValidationError(
                self.error_messages["unreadable"], code="unreadable"
            ) from error
        return ContentFile(output.getvalue(), name=f"{uuid.uuid4()}.webp")


class StyledModelForm(forms.ModelForm):
    """Base form that dresses every widget in DaisyUI classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.FileInput):
                widget.attrs["class"] = "file-input w-full"
            elif isinstance(widget, forms.CheckboxInput):
                widget.attrs["class"] = "toggle toggle-primary"
            elif isinstance(widget, forms.Textarea):
                widget.attrs["class"] = "textarea w-full"
                widget.attrs.setdefault("rows", 6)
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs["class"] = "select h-auto w-full"
                widget.attrs.setdefault("size", 8)
            elif isinstance(widget, forms.Select):
                widget.attrs["class"] = "select w-full"
            else:
                widget.attrs["class"] = "input w-full"


class ProductForm(StyledModelForm):
    price = forms.DecimalField(
        label="Price (USD)",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    image = ProductImageField(label="Image", required=False)

    class Meta:
        model = Product
        fields = [
            "name",
            "slug",
            "tagline",
            "description",
            "price",
            "category",
            "tags",
            "image",
            "is_available",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Taken before validation can touch the instance, so a re-rendered
        # form still previews the image that's actually saved.
        self.current_image_url = self.instance.image_url if self.instance.pk else None

    @property
    def image_needs_reselect(self):
        """Whether a chosen file was lost because the form came back with errors.

        Browsers can't refill a file input, so the image must be chosen again.
        """
        return bool(self.errors) and bool(self.files.get(self.add_prefix("image")))


class CategoryForm(StyledModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug"]


class TagForm(StyledModelForm):
    class Meta:
        model = Tag
        fields = ["name", "slug"]
