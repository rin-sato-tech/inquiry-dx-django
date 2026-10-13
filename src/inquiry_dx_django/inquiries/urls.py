from django.urls import path

from . import views

app_name = "inquiries"
urlpatterns = [
    path("", views.inquiry_list, name="home"),
    path("inquiries/", views.inquiry_list, name="list"),
    path("inquiries/new/", views.inquiry_create, name="create"),
    path("inquiries/<uuid:pk>/", views.inquiry_detail, name="detail"),
]
