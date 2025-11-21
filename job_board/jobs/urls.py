from django.urls import path
from . import views
from . import candidate_views
from . import notification_views

app_name = "jobs"

urlpatterns = [
    path("", views.job_search, name="search"),
    path("post/", views.post_job, name="post"),
    path("my-jobs/", views.my_jobs, name="my_jobs"),
    path("my-applications/", views.my_applications, name="my_applications"),
    path("<int:pk>/", views.job_detail, name="detail"),
    path("<int:pk>/quick-apply/", views.quick_apply, name="quick_apply"),
    path("<int:pk>/edit/", views.edit_job, name="edit"),
    path("<int:pk>/applications/", views.job_applications, name="applications"),
    path("application/<int:pk>/", views.application_detail, name="application_detail"),
    path("<int:pk>/close/", views.close_job, name="close"),
    path("<int:pk>/reopen/", views.reopen_job, name="reopen"),
    path("application/<int:pk>/accept/", views.accept_offer, name="application_accept"),
    path("application/<int:pk>/status/", views.update_application_status, name="application_status_update"),
    path("<int:pk>/report/", views.report_job, name="report_job"),

    # Candidate Search URLs
    path("candidates/", candidate_views.candidate_search, name="candidate_search"),
    path("candidates/save-search/", candidate_views.save_candidate_search, name="save_candidate_search"),
    path("candidates/saved-searches/", candidate_views.saved_searches, name="saved_searches"),
    path("candidates/saved-searches/<int:pk>/run/", candidate_views.run_saved_search, name="run_saved_search"),
    path("candidates/saved-searches/<int:pk>/delete/", candidate_views.delete_saved_search, name="delete_saved_search"),
    path("candidates/saved-searches/<int:pk>/toggle-notifications/", candidate_views.toggle_search_notifications, name="toggle_search_notifications"),

    path("notifications/", notification_views.notifications_list, name="notifications"),
    path(
        "notifications/<int:pk>/",
        notification_views.notification_detail,
        name="notification_detail",
    ),
    path(
        "notifications/<int:pk>/read/",
        notification_views.mark_notification_read,
        name="mark_notification_read",
    ),
    path(
        "notifications/mark-all-read/",
        notification_views.mark_all_read,
        name="mark_all_read",
    ),

    # Admin moderation
    path("admin/moderation-dashboard/", views.moderation_dashboard, name="moderation_dashboard"),

    # CSV Export (User Story 20)
    path("<int:job_pk>/applications/export/", views.export_job_applications_csv, name="export_job_applications"),
    path("export/all-applications/", views.export_all_applications_csv, name="export_all_applications"),
    path("export/jobs/", views.export_jobs_csv, name="export_jobs"),
    path("export/users/", views.export_users_csv, name="export_users"),
]
