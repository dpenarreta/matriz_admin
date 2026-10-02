from django.urls import path

from . import views

urlpatterns = [
    path(
        "companies/<int:company_id>/catalogs/",
        views.CatalogsView.as_view(),
        name="company-catalogs",
    ),
    path(
        "companies/<int:company_id>/dashboard/",
        views.DashboardView.as_view(),
        name="company-dashboard",
    ),
    path(
        "companies/<int:company_id>/periods/",
        views.PeriodListView.as_view(),
        name="company-periods",
    ),
    path(
        "companies/<int:company_id>/calendar/",
        views.CalendarView.as_view(),
        name="company-calendar",
    ),
    path(
        "companies/<int:company_id>/documents-overview/",
        views.DocumentsOverviewView.as_view(),
        name="company-documents-overview",
    ),
    path("companies/<int:company_id>/reports/", views.ReportView.as_view(), name="company-reports"),
    path(
        "companies/<int:company_id>/audit/", views.CompanyAuditView.as_view(), name="company-audit"
    ),
    path(
        "companies/<int:company_id>/obligations/",
        views.ObligationCreateView.as_view(),
        name="company-obligations",
    ),
    path(
        "obligations/<int:obligation_id>/",
        views.ObligationDetailView.as_view(),
        name="obligation-detail",
    ),
    path("periods/<int:period_id>/", views.PeriodDetailView.as_view(), name="period-detail"),
    path(
        "periods/<int:period_id>/due-date/",
        views.PeriodDueDateView.as_view(),
        name="period-due-date",
    ),
    path("periods/<int:period_id>/submit/", views.PeriodSubmitView.as_view(), name="period-submit"),
    path(
        "periods/<int:period_id>/validate/",
        views.PeriodValidateView.as_view(),
        name="period-validate",
    ),
    path("periods/<int:period_id>/return/", views.PeriodReturnView.as_view(), name="period-return"),
    path(
        "periods/<int:period_id>/history/", views.PeriodHistoryView.as_view(), name="period-history"
    ),
    path(
        "periods/<int:period_id>/documents/",
        views.PeriodDocumentsView.as_view(),
        name="period-documents",
    ),
    path(
        "documents/<int:document_id>/file/", views.DocumentFileView.as_view(), name="document-file"
    ),
    path(
        "documents/<int:document_id>/reject/",
        views.DocumentRejectView.as_view(),
        name="document-reject",
    ),
    path(
        "documents/<int:document_id>/", views.DocumentDeleteView.as_view(), name="document-delete"
    ),
]
