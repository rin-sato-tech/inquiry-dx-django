from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from .forms import InquiryCreateForm, new_submission_token
from .models import Inquiry
from .selectors import employee_inquiries
from .services import create_inquiry


@login_required
@require_http_methods(["GET"])
def inquiry_list(request):
    qs = employee_inquiries(request.user)
    query = request.GET.get("q", "").strip()[:200]
    status = request.GET.get("status", "")
    if query:
        qs = qs.filter(title__icontains=query)
    if status in Inquiry.Status.values:
        qs = qs.filter(status=status)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "inquiries/list.html",
        {
            "page_obj": page,
            "query": query,
            "selected_status": status,
            "statuses": Inquiry.Status.choices,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def inquiry_create(request):
    form = InquiryCreateForm(
        request.POST if request.method == "POST" else None,
        user=request.user,
        initial={"submission_token": new_submission_token(request.user)}
        if request.method == "GET"
        else None,
    )
    if request.method == "POST" and form.is_valid():
        try:
            inquiry = create_inquiry(
                actor=request.user, submission_key=form.submission_key, data=form.cleaned_data
            )
        except ValidationError as error:
            form.add_error(None, error)
        else:
            return redirect("inquiries:detail", pk=inquiry.pk)
    return render(request, "inquiries/create.html", {"form": form})


@login_required
@require_http_methods(["GET"])
def inquiry_detail(request, pk):
    inquiry = get_object_or_404(employee_inquiries(request.user), pk=pk)
    return render(request, "inquiries/detail.html", {"inquiry": inquiry})
