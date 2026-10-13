from .models import Inquiry


def employee_inquiries(user):
    return Inquiry.objects.filter(requester=user).select_related("category", "support_team")
