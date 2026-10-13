import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.urls import reverse

from inquiry_dx_django.accounts.models import Department, SupportTeam
from inquiry_dx_django.inquiries.forms import InquiryCreateForm, new_submission_token
from inquiry_dx_django.inquiries.models import Category, Inquiry, InquiryEvent
from inquiry_dx_django.inquiries.services import create_inquiry


class EmployeeFlowTests(TestCase):
    def test_stylesheet_is_discoverable(self):
        self.assertIsNotNone(finders.find("inquiry_dx_django/app.css"))

    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(name="営業部")
        cls.team = SupportTeam.objects.create(name="IT")
        cls.category = Category.objects.create(name="PC・システム", default_team=cls.team)
        cls.employee = get_user_model().objects.create_user(
            username="employee",
            password="test-password",
            display_name="社員A",
            department=cls.department,
        )
        cls.other = get_user_model().objects.create_user(
            username="other", password="test-password", display_name="社員B"
        )

    def setUp(self):
        self.client.force_login(self.employee)

    def payload(self, **kwargs):
        data = {
            "title": "ログインできない",
            "description": "エラーが表示されます。",
            "impact": "INDIVIDUAL",
            "category": str(self.category.pk),
            "requested_date": "",
            "requested_reason": "",
            "submission_token": new_submission_token(self.employee),
        }
        data.update(kwargs)
        return data

    def create(self, **kwargs):
        self.client.post(reverse("inquiries:create"), self.payload(**kwargs))
        return Inquiry.objects.latest("created_at")

    def test_anonymous_cannot_access_employee_screens(self):
        self.client.logout()
        for url in [
            reverse("inquiries:list"),
            reverse("inquiries:create"),
            reverse("inquiries:detail", args=[uuid.uuid4()]),
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn("/accounts/login/", response.url)

    def test_create_records_actor_team_department_and_event(self):
        response = self.client.post(
            reverse("inquiries:create"),
            self.payload(
                requester=self.other.pk,
                status="COMPLETED",
                support_team="999",
                assignee=self.other.pk,
            ),
        )
        inquiry = Inquiry.objects.get()
        self.assertRedirects(response, reverse("inquiries:detail", args=[inquiry.pk]))
        self.assertEqual(inquiry.requester, self.employee)
        self.assertEqual(inquiry.created_by, self.employee)
        self.assertEqual(inquiry.support_team, self.team)
        self.assertEqual(inquiry.department_at_receipt, "営業部")
        self.assertEqual(inquiry.status, Inquiry.Status.RECEIVED)
        self.assertIsNone(inquiry.assignee)
        self.assertEqual(inquiry.events.get().actor, self.employee)

    def test_duplicate_submission_creates_one_inquiry_and_event(self):
        data = self.payload()
        first = self.client.post(reverse("inquiries:create"), data)
        data["description"] = "二回目の送信で内容が変わっても上書きしない"
        second = self.client.post(reverse("inquiries:create"), data)
        self.assertEqual(first.url, second.url)
        self.assertEqual(Inquiry.objects.count(), 1)
        self.assertEqual(InquiryEvent.objects.count(), 1)
        self.assertEqual(Inquiry.objects.get().description, "エラーが表示されます。")

    def test_other_employees_inquiry_is_neither_listed_nor_retrievable(self):
        inquiry = self.create()
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("inquiries:list")), inquiry.title)
        self.assertEqual(
            self.client.get(reverse("inquiries:detail", args=[inquiry.pk])).status_code, 404
        )

    def test_department_change_does_not_change_receipt_snapshot(self):
        inquiry = self.create()
        self.employee.department = Department.objects.create(name="経理部")
        self.employee.save()
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.department_at_receipt, "営業部")

    def test_whitespace_only_input_and_missing_hope_reason_are_rejected(self):
        for override in [{"title": "   "}, {"description": "  "}, {"requested_date": "2026-11-01"}]:
            response = self.client.post(reverse("inquiries:create"), self.payload(**override))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context["form"].errors)
        self.assertEqual(Inquiry.objects.count(), 0)

    def test_inactive_category_or_team_cannot_receive_inquiry(self):
        self.category.is_active = False
        self.category.save()
        response = self.client.post(reverse("inquiries:create"), self.payload())
        self.assertIn("category", response.context["form"].errors)
        self.category.is_active = True
        self.category.save()
        self.team.is_active = False
        self.team.save()
        response = self.client.post(reverse("inquiries:create"), self.payload())
        self.assertIn("category", response.context["form"].errors)
        self.assertEqual(Inquiry.objects.count(), 0)

    def test_tampered_foreign_and_expired_submission_tokens_are_rejected(self):
        tokens = ["tampered", new_submission_token(self.other)]
        with patch("django.core.signing.time.time", return_value=1):
            tokens.append(new_submission_token(self.employee))
        for token in tokens:
            response = self.client.post(
                reverse("inquiries:create"), self.payload(submission_token=token)
            )
            self.assertIn("submission_token", response.context["form"].errors)
        self.assertEqual(Inquiry.objects.count(), 0)

    def test_event_failure_rolls_back_inquiry(self):
        form = InquiryCreateForm(self.payload(), user=self.employee)
        self.assertTrue(form.is_valid())
        with patch.object(InquiryEvent.objects, "create", side_effect=RuntimeError("write failed")):
            with self.assertRaises(RuntimeError):
                create_inquiry(
                    actor=self.employee, submission_key=form.submission_key, data=form.cleaned_data
                )
        self.assertEqual(Inquiry.objects.count(), 0)

    def test_registration_does_not_accept_get_query_as_submission(self):
        self.client.get(reverse("inquiries:create"), self.payload())
        self.assertEqual(Inquiry.objects.count(), 0)

    def test_description_is_escaped_and_internal_event_is_not_rendered(self):
        inquiry = self.create(description='<script>alert("x")</script>')
        InquiryEvent.objects.create(
            inquiry=inquiry,
            actor=self.employee,
            kind="INTERNAL",
            changes={"secret": "内部専用情報"},
        )
        response = self.client.get(reverse("inquiries:detail", args=[inquiry.pk]))
        self.assertNotContains(response, "<script>")
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, "内部専用情報")

    def test_search_is_scoped_and_paginated(self):
        Inquiry.objects.bulk_create(
            [
                Inquiry(
                    submission_key=uuid.uuid4(),
                    requester=self.employee,
                    created_by=self.employee,
                    title=f"検索対象{i}",
                    description="内容",
                    category=self.category,
                    support_team=self.team,
                    impact="INDIVIDUAL",
                )
                for i in range(26)
            ]
        )
        response = self.client.get(
            reverse("inquiries:list"), {"q": "検索対象", "status": "RECEIVED", "page": 2}
        )
        self.assertEqual(len(response.context["page_obj"]), 1)
        self.assertEqual(response.context["page_obj"].paginator.count, 26)
        self.assertContains(response, "status=RECEIVED")

    def test_database_rejects_inconsistent_completion_state(self):
        inquiry = self.create()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Inquiry.objects.filter(pk=inquiry.pk).update(status="COMPLETED")

    def test_csrf_protection_is_enabled(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.employee)
        self.assertEqual(client.post(reverse("inquiries:create"), self.payload()).status_code, 403)

    def test_password_change_preserves_employee_flow(self):
        self.assertEqual(self.client.get(reverse("password_change")).status_code, 200)
        response = self.client.post(
            reverse("password_change"),
            {
                "old_password": "test-password",
                "new_password1": "A-strong-new-password-924!",
                "new_password2": "A-strong-new-password-924!",
            },
        )
        self.assertRedirects(response, reverse("password_change_done"))
        self.assertEqual(self.client.get(reverse("inquiries:list")).status_code, 200)

    def test_logout_requires_post(self):
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.assertRedirects(self.client.post(reverse("logout")), reverse("login"))
