from django.urls import path

from . import views

urlpatterns = [
    path("companies/mine/", views.MyCompaniesView.as_view(), name="my-companies"),
    path("companies/<int:company_id>/", views.CompanyDetailView.as_view(), name="company-detail"),
    path(
        "companies/<int:company_id>/people/",
        views.CompanyPeopleView.as_view(),
        name="company-people",
    ),
    path(
        "companies/<int:company_id>/roles/",
        views.CompanyRolesView.as_view(),
        name="company-roles",
    ),
    path(
        "companies/<int:company_id>/members/",
        views.MembershipListView.as_view(),
        name="company-members",
    ),
    path(
        "companies/<int:company_id>/members/<int:membership_id>/",
        views.MembershipDetailView.as_view(),
        name="company-member-detail",
    ),
]
