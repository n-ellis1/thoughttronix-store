from django.contrib import admin

from .models import Address, Cart, CartItem, DiscountCode, Order, OrderItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "item_count", "total")
    search_fields = ("user__username",)
    inlines = [CartItemInline]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "__str__", "is_default")
    search_fields = ("user__username",)


@admin.register(DiscountCode)
class DiscountCodeAdmin(admin.ModelAdmin):
    list_display = ("code", "kind", "value", "scope", "expires_on", "is_active")
    list_filter = ("is_active", "kind", "scope")
    search_fields = ("code",)
    filter_horizontal = ("products",)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("number", "user", "status", "total", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username", "shipping_name")
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]
