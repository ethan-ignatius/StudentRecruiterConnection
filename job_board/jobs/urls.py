from django.urls import path
from . import views

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
]
