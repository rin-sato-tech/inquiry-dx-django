from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import Category, Inquiry, InquiryEvent


@transaction.atomic
def create_inquiry(*, actor, submission_key, data):
    if not actor.is_active:
        raise PermissionDenied
    # フォーム検証後にカテゴリ・受付チームが無効化されていないか再確認する。
    category = (
        Category.objects.select_for_update()
        .select_related("default_team")
        .get(pk=data["category"].pk)
    )
    if not category.is_active or not category.default_team.is_active:
        raise ValidationError(
            "このカテゴリは受付を停止しています。別のカテゴリを選択してください。"
        )
    inquiry, created = Inquiry.objects.get_or_create(
        submission_key=submission_key,
        defaults={
            "requester": actor,
            "created_by": actor,
            "department_at_receipt": actor.department.name if actor.department else "",
            "title": data["title"],
            "description": data["description"],
            "category": category,
            "support_team": category.default_team,
            "impact": data["impact"],
            "requested_date": data.get("requested_date"),
            "requested_reason": data.get("requested_reason", ""),
        },
    )
    if inquiry.requester_id != actor.pk:
        raise PermissionDenied
    if created:
        InquiryEvent.objects.create(
            inquiry=inquiry,
            actor=actor,
            kind="CREATED",
            changes={"status": {"before": None, "after": Inquiry.Status.RECEIVED}},
        )
    return inquiry
