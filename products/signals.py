"""Signal receivers for the catalog.

``post_delete`` fires for every delete path — a single product, a queryset
delete, the admin's bulk action — so the image file follows its product.
"""

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Product, delete_image_file_on_commit


@receiver(post_delete, sender=Product)
def delete_product_image(sender, instance, **kwargs):
    if instance.image:
        delete_image_file_on_commit(instance.image.name)
