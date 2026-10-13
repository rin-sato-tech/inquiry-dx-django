import uuid

from django import forms
from django.core import signing

from .models import Category, Inquiry

SALT = "inquiries.create"


def new_submission_token(user):
    return signing.dumps({"user": user.pk, "key": str(uuid.uuid4())}, salt=SALT)


class InquiryCreateForm(forms.ModelForm):
    submission_token = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = Inquiry
        fields = [
            "title",
            "category",
            "description",
            "impact",
            "requested_date",
            "requested_reason",
        ]
        widgets = {
            "requested_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 7}),
            "requested_reason": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["category"].queryset = Category.objects.filter(
            is_active=True, default_team__is_active=True
        ).order_by("name")
        for name in ("title", "description", "requested_reason"):
            self.fields[name].strip = True

    def clean_submission_token(self):
        token = self.cleaned_data["submission_token"]
        try:
            payload = signing.loads(token, salt=SALT, max_age=86400)
            if payload["user"] != self.user.pk:
                raise ValueError
            self.submission_key = uuid.UUID(payload["key"])
        except (signing.BadSignature, ValueError, KeyError, TypeError):
            raise forms.ValidationError(
                "送信情報が無効です。新規登録画面を開き直してください。"
            ) from None
        return token

    def clean(self):
        data = super().clean()
        if data.get("requested_date") and not data.get("requested_reason"):
            self.add_error(
                "requested_reason", "希望日を指定した場合は、その理由も入力してください。"
            )
        return data
