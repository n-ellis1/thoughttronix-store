from django.db import models, transaction
from django.templatetags.static import static
from django.urls import reverse

# Categories with a dedicated placeholder illustration; anything else
# falls back to default.svg. Products without an uploaded image show
# their category's placeholder, a static file.
PLACEHOLDER_CATEGORIES = {
    "home-assistants",
    "neural-implants",
    "neural-wearables",
    "accessories",
    "defense",
    "legacy-products",
}


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("products:category", kwargs={"slug": self.slug})

    @property
    def placeholder_image(self):
        """Static path of the placeholder image shown for this category's products."""
        if self.slug in PLACEHOLDER_CATEGORIES:
            return f"images/placeholders/{self.slug}.svg"
        return "images/placeholders/default.svg"


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def available(self):
        return self.filter(is_available=True)

    def search(self, text):
        """Simple icontains search over name and description."""
        return self.filter(
            models.Q(name__icontains=text) | models.Q(description__icontains=text)
        )


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    tagline = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")
    # Uploads arrive already processed by ProductImageField (products/forms.py)
    # as <uuid>.webp, so every upload gets a fresh name under products/.
    image = models.ImageField(upload_to="products/", blank=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """Save, then delete the previous image file if it was replaced or cleared."""
        old_name = (
            Product.objects.filter(pk=self.pk).values_list("image", flat=True).first()
            if self.pk
            else None
        )
        super().save(*args, **kwargs)
        if old_name and old_name != self.image.name:
            delete_image_file_on_commit(old_name)

    def get_absolute_url(self):
        return reverse("products:detail", kwargs={"slug": self.slug})

    @property
    def image_url(self):
        """URL of the uploaded image, or the category placeholder if there's no file.

        Checks that the file exists in storage, not that MEDIA_URL is served.
        """
        if self.image and self.image.storage.exists(self.image.name):
            return self.image.url
        return static(self.category.placeholder_image)


def delete_image_file_on_commit(name):
    """Delete an image file once the transaction commits — unless still in use.

    Skipped if the transaction rolls back, or if any product still references
    the file at commit time. Reduces unused files; it doesn't guarantee that
    storage and database stay in sync.
    """
    storage = Product._meta.get_field("image").storage

    def delete():
        if not Product.objects.filter(image=name).exists():
            storage.delete(name)

    transaction.on_commit(delete)
