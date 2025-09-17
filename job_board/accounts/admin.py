from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Account Type", {"fields": ("account_type",)}),
    )
    list_display = ("username", "email", "account_type", "is_staff", "is_active")
    list_filter = ("account_type", "is_staff", "is_superuser", "is_active")
