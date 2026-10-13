from django.contrib.auth.models import AbstractUser
from django.db import models


class Department(models.Model):
    name = models.CharField("部署名", max_length=100, unique=True)
    is_active = models.BooleanField("有効", default=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    display_name = models.CharField("表示名", max_length=100)
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, null=True, blank=True, verbose_name="部署"
    )

    def __str__(self):
        return self.display_name or self.username


class SupportTeam(models.Model):
    name = models.CharField("対応チーム名", max_length=100, unique=True)
    is_active = models.BooleanField("有効", default=True)

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    class Role(models.TextChoices):
        AGENT = "AGENT", "対応担当者"
        COORDINATOR = "COORDINATOR", "受付責任者"

    user = models.ForeignKey(User, on_delete=models.PROTECT)
    team = models.ForeignKey(SupportTeam, on_delete=models.PROTECT)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.AGENT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "team"], name="unique_team_member")]
