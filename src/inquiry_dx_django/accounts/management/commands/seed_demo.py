import os

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inquiry_dx_django.accounts.models import Department, SupportTeam, TeamMembership
from inquiry_dx_django.inquiries.models import Category


class Command(BaseCommand):
    help = "開発専用の部署・チーム・カテゴリ・社員アカウントを作成します。既存パスワードは変更しません。"

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("seed_demoはDJANGO_DEBUG=1の開発環境専用です。")
        password = os.environ.get("DEMO_PASSWORD", "")
        if not password:
            raise CommandError("DEMO_PASSWORDを環境変数または.envで設定してください。")
        try:
            validate_password(password)
        except ValidationError as error:
            raise CommandError(" / ".join(error.messages)) from error
        department, _ = Department.objects.get_or_create(name="デモ営業部")
        team, _ = SupportTeam.objects.get_or_create(name="デモITチーム")
        Category.objects.get_or_create(name="PC・システム", defaults={"default_team": team})
        for username, name, role in [
            ("demo_employee", "デモ社員", None),
            ("demo_agent", "デモ担当者", TeamMembership.Role.AGENT),
            ("demo_coordinator", "デモ受付責任者", TeamMembership.Role.COORDINATOR),
        ]:
            user, created = get_user_model().objects.get_or_create(
                username=username, defaults={"display_name": name, "department": department}
            )
            if created:
                user.set_password(password)
                user.save()
                if role:
                    TeamMembership.objects.create(user=user, team=team, role=role)
            self.stdout.write(
                f"{username}: {'作成しました' if created else '既存のため変更しません'}"
            )
