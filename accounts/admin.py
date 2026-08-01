from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.action(description='Activate selected user accounts')
def make_active(modeladmin, request, queryset):
    queryset.update(is_active=True)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ['email', 'username', 'role', 'is_active', 'is_staff']
    list_filter = ['role', 'is_active', 'is_staff']
    actions = [make_active] # Enables 1-click batch account activation in admin
    fieldsets = UserAdmin.fieldsets + (
        ('Role & Verification', {'fields': ('role',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role & Verification', {'fields': ('role',)}),
    ) 