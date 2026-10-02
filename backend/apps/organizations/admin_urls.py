from django.urls import path

from . import admin_views as views

urlpatterns = [
    path("companies/", views.AdminCompanyListView.as_view(), name="admin-companies"),
    path(
        "companies/<int:company_id>/",
        views.AdminCompanyDetailView.as_view(),
        name="admin-company-detail",
    ),
    path(
        "companies/<int:company_id>/branches/",
        views.AdminBranchListView.as_view(),
        name="admin-company-branches",
    ),
    path(
        "companies/<int:company_id>/branches/<int:branch_id>/",
        views.AdminBranchDetailView.as_view(),
        name="admin-company-branch-detail",
    ),
    path("catalogs/<slug:kind>/", views.AdminCatalogListView.as_view(), name="admin-catalog"),
    path(
        "catalogs/<slug:kind>/<int:item_id>/",
        views.AdminCatalogDetailView.as_view(),
        name="admin-catalog-detail",
    ),
    path("matrix-roles/", views.AdminMatrixRolesView.as_view(), name="admin-matrix-roles"),
    path(
        "users/<int:user_id>/memberships/",
        views.AdminUserMembershipsView.as_view(),
        name="admin-user-memberships",
    ),
]
