import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from inquiry_dx_django.accounts.models import SupportTeam


class Category(models.Model):
    name = models.CharField("カテゴリ名", max_length=100, unique=True)
    default_team = models.ForeignKey(
        SupportTeam, on_delete=models.PROTECT, verbose_name="受付チーム"
    )
    is_active = models.BooleanField("有効", default=True)

    def __str__(self):
        return self.name


class Inquiry(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "受付済み"
        IN_PROGRESS = "IN_PROGRESS", "対応中"
        WAITING_REQUESTER = "WAITING_REQUESTER", "依頼者回答待ち"
        COMPLETED = "COMPLETED", "完了"
        CANCELLED = "CANCELLED", "取消"

    class Impact(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", "自分の業務に影響"
        TEAM = "TEAM", "部署・チームの業務に影響"
        COMPANY = "COMPANY", "全社の業務に影響"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    submission_key = models.UUIDField(unique=True, editable=False)
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="requested_inquiries"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_inquiries"
    )
    department_at_receipt = models.CharField(max_length=100, blank=True)
    title = models.CharField("件名", max_length=200)
    description = models.TextField("内容", max_length=10000)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="カテゴリ")
    support_team = models.ForeignKey(SupportTeam, on_delete=models.PROTECT)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_inquiries",
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    impact = models.CharField("業務への影響", max_length=20, choices=Impact.choices)
    requested_date = models.DateField("希望日", null=True, blank=True)
    requested_reason = models.TextField("希望日の理由", max_length=10000, blank=True)
    due_date = models.DateField("対応期限", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    waiting_since = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ["-updated_at", "-id"]
        indexes = [
            models.Index(fields=["requester", "-updated_at"]),
            models.Index(fields=["support_team", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "RECEIVED",
                        "IN_PROGRESS",
                        "WAITING_REQUESTER",
                        "COMPLETED",
                        "CANCELLED",
                    ]
                ),
                name="valid_inquiry_status",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["RECEIVED", "CANCELLED"]) | Q(assignee__isnull=False),
                name="active_inquiry_has_assignee",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="COMPLETED", completed_at__isnull=False)
                    | (~Q(status="COMPLETED") & Q(completed_at__isnull=True))
                ),
                name="completed_time_matches_status",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="CANCELLED", cancelled_at__isnull=False)
                    | (~Q(status="CANCELLED") & Q(cancelled_at__isnull=True))
                ),
                name="cancelled_time_matches_status",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="WAITING_REQUESTER", waiting_since__isnull=False)
                    | (~Q(status="WAITING_REQUESTER") & Q(waiting_since__isnull=True))
                ),
                name="waiting_time_matches_status",
            ),
        ]

    def __str__(self):
        return self.title


class InquiryEvent(models.Model):
    inquiry = models.ForeignKey(Inquiry, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    kind = models.CharField(max_length=30)
    changes = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
