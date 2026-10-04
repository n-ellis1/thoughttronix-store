from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_available")
    list_filter = ("category", "is_available", "tags")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}
    # Images are uploaded through the back office, where they're validated
    # and processed; the admin only shows them.
    exclude = ("image",)
    readonly_fields = ("image_preview",)

    @admin.display(description="Image")
    def image_preview(self, product):
        if not product.pk:
            return "Upload images from the back office."
        return format_html(
            '<img src="{}" alt="{}" style="aspect-ratio: 4 / 5; width: 160px; '
            'object-fit: contain;">',
            product.image_url,
            product.name,
        )
