from django.urls import path
from . import views

app_name = "jobs"

urlpatterns = [
    path("", views.job_search, name="search"),
    path("post/", views.post_job, name="post"),
    path("my-jobs/", views.my_jobs, name="my_jobs"),
    path("<int:pk>/", views.job_detail, name="detail"),
    path("<int:pk>/apply/", views.apply_for_job, name="apply"),
    path("<int:pk>/edit/", views.edit_job, name="edit"),
    path("<int:pk>/applications/", views.job_applications, name="applications"),
]