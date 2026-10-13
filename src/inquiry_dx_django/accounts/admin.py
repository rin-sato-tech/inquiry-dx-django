from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Department, SupportTeam, TeamMembership, User


@admin.register(User)
class EmployeeAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("社員情報", {"fields": ("display_name", "department")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("社員情報", {"fields": ("display_name", "department")}),
    )
    list_display = ("username", "display_name", "department", "is_active", "is_staff")


admin.site.register(Department)
admin.site.register(SupportTeam)
admin.site.register(TeamMembership)
