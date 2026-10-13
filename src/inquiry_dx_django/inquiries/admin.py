from django.contrib import admin

from .models import Category, Inquiry, InquiryEvent

admin.site.register(Category)


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(Inquiry)
class InquiryAdmin(ReadOnlyAdmin):
    list_display = ("id", "title", "requester", "status", "created_at")


admin.site.register(InquiryEvent, ReadOnlyAdmin)
