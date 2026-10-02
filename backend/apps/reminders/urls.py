from django.urls import path

from . import views

urlpatterns = [
    path(
        "companies/<int:company_id>/reminder-config/",
        views.ReminderConfigView.as_view(),
        name="company-reminder-config",
    ),
    path(
        "companies/<int:company_id>/notifications/",
        views.CompanyNotificationsView.as_view(),
        name="company-notifications",
    ),
    path(
        "periods/<int:period_id>/reminders/",
        views.PeriodRemindersView.as_view(),
        name="period-reminders",
    ),
    path(
        "periods/<int:period_id>/reminders/send/",
        views.PeriodReminderSendView.as_view(),
        name="period-reminders-send",
    ),
    path(
        "periods/<int:period_id>/reminders/preview/",
        views.PeriodReminderPreviewView.as_view(),
        name="period-reminders-preview",
    ),
    path(
        "notifications/<int:notification_id>/retry/",
        views.NotificationRetryView.as_view(),
        name="notification-retry",
    ),
]
