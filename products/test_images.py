"""Product images: validation, processing, display, file lifecycle, back office.

Every test gets its own temporary MEDIA_ROOT; images are generated in
memory with Pillow.
"""

import re
import struct
import zlib
from http import HTTPStatus
from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.urls import reverse
from PIL import Image, ImageCms

from .forms import ProductImageField
from .models import Product

pytestmark = pytest.mark.django_db

UUID_WEBP_NAME = re.compile(
    r"^products/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.webp$"
)


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


# --- Building test images ----------------------------------------------------


def image_bytes(size=(800, 1000), fmt="PNG", mode="RGB", color="teal", **save_kwargs):
    buffer = BytesIO()
    Image.new(mode, size, color).save(buffer, fmt, **save_kwargs)
    return buffer.getvalue()


def noisy_jpeg(size=(800, 1000)):
    """A JPEG with real scan data, so truncating it cuts into the pixels."""
    buffer = BytesIO()
    Image.effect_noise(size, 64).convert("RGB").save(buffer, "JPEG", quality=95)
    return buffer.getvalue()


def animated_bytes(fmt, size=(800, 1000)):
    frames = [Image.new("RGB", size, color) for color in ("red", "blue")]
    buffer = BytesIO()
    frames[0].save(buffer, fmt, save_all=True, append_images=frames[1:], duration=100)
    return buffer.getvalue()


def png_chunk(kind, data):
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data))
    )


def png_header_only(width, height):
    """A PNG whose header claims a size but carries no pixel data at all.

    Opening it works; decoding it would fail — so a size rejection proves
    the check ran on the header alone.
    """
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", b"")
        + png_chunk(b"IEND", b"")
    )


def corrupt_png_header():
    data = bytearray(image_bytes())
    data[16] ^= 0xFF  # inside IHDR, so its checksum no longer matches
    return bytes(data)


def upload(content, name="photo.png", content_type="image/png"):
    return SimpleUploadedFile(name, content, content_type=content_type)


def clean(content, name="photo.png"):
    return ProductImageField(required=False).clean(upload(content, name))


def processed(content, name="photo.png"):
    """Run an upload through the field and open the WebP that comes out."""
    return Image.open(BytesIO(clean(content, name).read()))


def stored_files(media_root):
    return sorted(p for p in media_root.rglob("*") if p.is_file())


def give_image(product, name="original.webp"):
    product.image.save(name, ContentFile(image_bytes(fmt="WEBP")))
    return product.image.name


# --- Rejections ----------------------------------------------------------------

REJECTIONS = [
    pytest.param(
        image_bytes() + b"\0" * (11 * 1024 * 1024),
        "photo.png",
        "This image is too large (11.0 MB). Upload a file 10 MB or smaller.",
        id="over-10-mb",
    ),
    pytest.param(
        png_header_only(8000, 8000),
        "photo.png",
        "This image is too large (8000 × 8000 pixels). "
        "Upload an image of 50 megapixels or fewer.",
        id="over-50-megapixels",
    ),
    pytest.param(
        png_header_only(20000, 20000),
        "photo.png",
        "Upload an image of 50 megapixels or fewer.",
        id="decompression-bomb",
    ),
    pytest.param(
        image_bytes(size=(320, 240)),
        "photo.png",
        "This image is too small (320 × 240 pixels). "
        "Upload an image at least 600 pixels on each side.",
        id="under-600-pixels",
    ),
    pytest.param(
        image_bytes(size=(599, 1000)),
        "photo.png",
        "This image is too small (599 × 1000 pixels).",
        id="one-side-under-600",
    ),
    pytest.param(
        image_bytes(fmt="GIF"),
        "photo.gif",
        "Upload a JPEG, PNG, or WebP image.",
        id="wrong-format",
    ),
    pytest.param(
        image_bytes(fmt="BMP"),
        "photo.png",
        "Upload a JPEG, PNG, or WebP image.",
        id="bmp-named-png",
    ),
    pytest.param(
        b"Definitely a product photo. Trust us.",
        "photo.png",
        "Upload a JPEG, PNG, or WebP image.",
        id="renamed-non-image",
    ),
    # GIF isn't an accepted format, animated or not — the format check runs first.
    pytest.param(
        animated_bytes("GIF"),
        "photo.gif",
        "Upload a JPEG, PNG, or WebP image.",
        id="animated-gif",
    ),
    pytest.param(
        animated_bytes("WEBP"),
        "photo.webp",
        "Animated images aren't supported. Upload a still image.",
        id="animated-webp",
    ),
    pytest.param(
        animated_bytes("PNG"),
        "photo.png",
        "Animated images aren't supported. Upload a still image.",
        id="animated-png",
    ),
    pytest.param(
        noisy_jpeg()[:20_000],
        "photo.jpg",
        "This image couldn't be read. It may be damaged or incomplete. "
        "Try saving or exporting it again as a JPEG, PNG, or WebP.",
        id="truncated-jpeg",
    ),
    pytest.param(
        corrupt_png_header(),
        "photo.png",
        "This image couldn't be read.",
        id="corrupt-png-header",
    ),
]


@pytest.mark.parametrize(("content", "name", "message"), REJECTIONS)
def test_rejected_uploads_explain_why(content, name, message):
    with pytest.raises(ValidationError) as excinfo:
        clean(content, name)

    assert message in " ".join(excinfo.value.messages)


def test_oversized_files_are_rejected_before_decoding(monkeypatch):
    def never_open(*args, **kwargs):
        raise AssertionError("an oversized file must not be opened")

    monkeypatch.setattr("products.forms.Image.open", never_open)

    with pytest.raises(ValidationError, match="too large"):
        clean(image_bytes() + b"\0" * (11 * 1024 * 1024))


@pytest.mark.parametrize("size", [(600, 600), (600, 8000)])
def test_limits_are_inclusive(size):
    assert clean(image_bytes(size=size)) is not None


@pytest.mark.parametrize(("content", "name", "message"), REJECTIONS)
def test_rejected_upload_on_create_stores_nothing(
    client, staff_user, category, media_root, content, name, message
):
    client.force_login(staff_user)

    response = client.post(
        reverse("products:manage_product_create"),
        product_form_data(category, image=upload(content, name)),
    )

    assert response.status_code == HTTPStatus.OK
    assert not Product.objects.exists()
    assert stored_files(media_root) == []


@pytest.mark.parametrize(("content", "name", "message"), REJECTIONS)
def test_rejected_upload_on_edit_changes_nothing(
    client, staff_user, product, media_root, content, name, message
):
    original_name = give_image(product)
    files_before = stored_files(media_root)
    client.force_login(staff_user)

    response = client.post(
        reverse("products:manage_product_update", kwargs={"pk": product.pk}),
        product_form_data(
            product.category,
            name="Renamed",
            slug=product.slug,
            image=upload(content, name),
        ),
    )

    assert response.status_code == HTTPStatus.OK
    product.refresh_from_db()
    assert product.name == "Seraphine Home Hub"
    assert product.image.name == original_name
    assert stored_files(media_root) == files_before


# --- Processing -----------------------------------------------------------------


def test_output_is_a_uuid_named_webp():
    result = clean(image_bytes(), "My Photo.PNG")

    assert re.fullmatch(r"[0-9a-f-]{36}\.webp", result.name)
    assert Image.open(BytesIO(result.read())).format == "WEBP"


def test_large_images_shrink_to_1200_keeping_aspect_ratio():
    assert processed(image_bytes(size=(2400, 1600))).size == (1200, 800)
    assert processed(image_bytes(size=(1000, 3000))).size == (400, 1200)


def test_small_images_are_not_enlarged():
    assert processed(image_bytes(size=(700, 900))).size == (700, 900)


def test_transparency_is_preserved():
    content = image_bytes(mode="RGBA", color=(255, 0, 0, 0))

    image = processed(content)

    assert image.mode == "RGBA"
    assert image.getpixel((10, 10))[3] == 0


def test_palette_transparency_is_preserved():
    image = Image.new("P", (800, 1000), 0)
    buffer = BytesIO()
    image.save(buffer, "PNG", transparency=0)

    assert processed(buffer.getvalue()).mode == "RGBA"


def test_cmyk_jpegs_come_out_rgb():
    image = processed(image_bytes(fmt="JPEG", mode="CMYK", color=(0, 0, 0, 0)))

    assert image.mode == "RGB"


def test_exif_rotated_input_comes_out_upright():
    exif = Image.Exif()
    exif[0x0112] = 6  # stored sideways; display rotated 90° clockwise
    content = image_bytes(size=(1000, 700), fmt="JPEG", exif=exif.tobytes())

    assert processed(content, "photo.jpg").size == (700, 1000)


def test_output_has_no_exif():
    exif = Image.Exif()
    exif[0x010F] = "Camera Maker"
    content = image_bytes(fmt="JPEG", exif=exif.tobytes())

    image = processed(content, "photo.jpg")

    assert "exif" not in image.info
    assert dict(image.getexif()) == {}


def test_rgb_color_profile_is_kept():
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()

    image = processed(image_bytes(icc_profile=profile))

    assert image.info.get("icc_profile") == profile


# --- Display ------------------------------------------------------------------


def test_image_url_falls_back_to_the_category_placeholder(product):
    assert product.image_url == "/static/images/placeholders/home-assistants.svg"


def test_image_url_points_at_an_existing_upload(product):
    name = give_image(product)

    assert product.image_url == f"/media/{name}"


def test_image_url_falls_back_when_the_file_is_missing(product):
    product.image.name = "products/gone.webp"

    assert product.image_url == "/static/images/placeholders/home-assistants.svg"


def test_catalog_and_detail_show_the_image(client, product):
    give_image(product)

    catalog = client.get(reverse("products:catalog")).content.decode()
    category = client.get(product.category.get_absolute_url()).content.decode()
    detail = client.get(product.get_absolute_url()).content.decode()

    for page in (catalog, category, detail):
        assert product.image_url in page
        assert "aspect-[4/5]" in page
    assert 'loading="lazy"' in catalog


# --- File lifecycle -----------------------------------------------------------


def test_replacing_an_image_deletes_the_old_file(
    product, media_root, django_capture_on_commit_callbacks
):
    old_name = give_image(product)

    with django_capture_on_commit_callbacks(execute=True):
        product.image = ContentFile(image_bytes(fmt="WEBP"), name="new.webp")
        product.save()

    assert not (media_root / old_name).exists()
    assert (media_root / product.image.name).exists()


def test_clearing_an_image_deletes_the_file(
    product, media_root, django_capture_on_commit_callbacks
):
    old_name = give_image(product)

    with django_capture_on_commit_callbacks(execute=True):
        product.image = ""
        product.save()

    assert not (media_root / old_name).exists()


def test_deleting_a_product_deletes_its_file(
    product, media_root, django_capture_on_commit_callbacks
):
    name = give_image(product)

    with django_capture_on_commit_callbacks(execute=True):
        product.delete()

    assert not (media_root / name).exists()


def test_queryset_delete_deletes_files(
    product, media_root, django_capture_on_commit_callbacks
):
    name = give_image(product)

    with django_capture_on_commit_callbacks(execute=True):
        Product.objects.all().delete()

    assert not (media_root / name).exists()


def test_a_rolled_back_change_keeps_the_old_image(
    product, media_root, django_capture_on_commit_callbacks
):
    old_name = give_image(product)

    with django_capture_on_commit_callbacks(execute=True):
        with pytest.raises(RuntimeError), transaction.atomic():
            product.image = ContentFile(image_bytes(fmt="WEBP"), name="new.webp")
            product.save()
            raise RuntimeError("the database change fails")

    product.refresh_from_db()
    assert product.image.name == old_name
    assert (media_root / old_name).exists()


def test_a_shared_file_is_not_deleted(
    product, featured_product, media_root, django_capture_on_commit_callbacks
):
    name = give_image(product)
    Product.objects.filter(pk=featured_product.pk).update(image=name)

    with django_capture_on_commit_callbacks(execute=True):
        product.delete()

    assert (media_root / name).exists()


# --- Back office --------------------------------------------------------------


def product_form_data(category, **overrides):
    data = {
        "name": "MindSync Sleep Halo",
        "slug": "mindsync-sleep-halo",
        "price": "199.99",
        "is_available": "on",
        "category": str(category.pk),
    }
    data.update(overrides)
    return data


def test_staff_can_upload_an_image_on_create(client, staff_user, category, media_root):
    client.force_login(staff_user)

    client.post(
        reverse("products:manage_product_create"),
        product_form_data(category, image=upload(image_bytes(size=(2400, 3000)))),
    )

    product = Product.objects.get(slug="mindsync-sleep-halo")
    assert UUID_WEBP_NAME.match(product.image.name)
    with Image.open(media_root / product.image.name) as stored:
        assert (stored.format, stored.size) == ("WEBP", (960, 1200))


def test_staff_can_replace_an_image_on_edit(
    client, staff_user, product, media_root, django_capture_on_commit_callbacks
):
    old_name = give_image(product)
    client.force_login(staff_user)

    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            reverse("products:manage_product_update", kwargs={"pk": product.pk}),
            product_form_data(
                product.category,
                name=product.name,
                slug=product.slug,
                image=upload(image_bytes()),
            ),
        )

    product.refresh_from_db()
    assert UUID_WEBP_NAME.match(product.image.name)
    assert stored_files(media_root) == [media_root / product.image.name]
    assert old_name != product.image.name


def test_staff_can_clear_an_image(
    client, staff_user, product, media_root, django_capture_on_commit_callbacks
):
    give_image(product)
    client.force_login(staff_user)

    with django_capture_on_commit_callbacks(execute=True):
        client.post(
            reverse("products:manage_product_update", kwargs={"pk": product.pk}),
            product_form_data(
                product.category,
                name=product.name,
                slug=product.slug,
                **{"image-clear": "on"},
            ),
        )

    product.refresh_from_db()
    assert not product.image
    assert stored_files(media_root) == []


def test_edit_form_previews_the_image_with_the_clear_option(
    client, staff_user, product
):
    give_image(product)
    client.force_login(staff_user)

    page = client.get(
        reverse("products:manage_product_update", kwargs={"pk": product.pk})
    ).content.decode()

    assert 'enctype="multipart/form-data"' in page
    assert product.image_url in page
    assert "Remove image and use the category placeholder" in page
    assert "resized to 1200 px and saved as WebP" in page


def test_edit_form_previews_the_placeholder_without_an_image(
    client, staff_user, product
):
    client.force_login(staff_user)

    page = client.get(
        reverse("products:manage_product_update", kwargs={"pk": product.pk})
    ).content.decode()

    assert "/static/images/placeholders/home-assistants.svg" in page
    assert "Remove image and use the category placeholder" not in page


def test_errors_elsewhere_ask_for_the_image_again(client, staff_user, category):
    client.force_login(staff_user)
    url = reverse("products:manage_product_create")

    with_file = client.post(
        url, product_form_data(category, price="-1", image=upload(image_bytes()))
    ).content.decode()
    without_file = client.post(
        url, product_form_data(category, price="-1")
    ).content.decode()

    assert "Choose the image again" in with_file
    assert "Choose the image again" not in without_file


def test_product_list_shows_thumbnails(client, staff_user, product, featured_product):
    give_image(product)
    client.force_login(staff_user)

    page = client.get(reverse("products:manage_products")).content.decode()

    assert product.image_url in page
    assert featured_product.image_url in page


def test_admin_shows_the_image_read_only(client, product):
    give_image(product)
    admin = get_user_model().objects.create_superuser(
        username="admin", password="admin123"
    )
    client.force_login(admin)

    page = client.get(
        reverse("admin:products_product_change", args=[product.pk])
    ).content.decode()

    assert product.image_url in page
    assert 'type="file"' not in page
