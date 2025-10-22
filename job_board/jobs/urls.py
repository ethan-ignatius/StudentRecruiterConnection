from django.urls import path
from . import views
from . import candidate_views  # Add this import at top

app_name = "jobs"

urlpatterns = [
    path("", views.job_search, name="search"),
    path("post/", views.post_job, name="post"),
    path("my-jobs/", views.my_jobs, name="my_jobs"),
    path("<int:pk>/", views.job_detail, name="detail"),
    path("<int:pk>/quick-apply/", views.quick_apply, name="quick_apply"),
    path("<int:pk>/edit/", views.edit_job, name="edit"),
    path("<int:pk>/applications/", views.job_applications, name="applications"),
    path("application/<int:pk>/", views.application_detail, name="application_detail"),
    path("<int:pk>/close/", views.close_job, name="close"),
    path("<int:pk>/reopen/", views.reopen_job, name="reopen"),

    # Candidate Search URLs
    path("candidates/", candidate_views.candidate_search, name="candidate_search"),
    path("candidates/save-search/", candidate_views.save_candidate_search, name="save_candidate_search"),
    path("candidates/saved-searches/", candidate_views.saved_searches, name="saved_searches"),
    path("candidates/saved-searches/<int:pk>/run/", candidate_views.run_saved_search, name="run_saved_search"),
    path("candidates/saved-searches/<int:pk>/delete/", candidate_views.delete_saved_search, name="delete_saved_search"),
    path("candidates/saved-searches/<int:pk>/toggle-notifications/", candidate_views.toggle_search_notifications, name="toggle_search_notifications"),
]
