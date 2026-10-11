from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .forms import AdminUserChangeForm
from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = AdminUserChangeForm
    fieldsets = (
        *DjangoUserAdmin.fieldsets,
        ("ThoughtTronix", {"fields": ("job_title",)}),
        ("Pending email change", {"fields": ("pending_email", "email_link_sent_at")}),
    )
    readonly_fields = ("pending_email", "email_link_sent_at")
    list_display = ("username", "email", "job_title", "is_staff")

    def save_model(self, request, obj, form, change):
        # An admin correction wins: drop any pending request so an old
        # link can't overwrite it. No confirmation and no notice.
        if change and "email" in form.changed_data:
            obj.clear_pending_email(save=False)
        super().save_model(request, obj, form, change)
