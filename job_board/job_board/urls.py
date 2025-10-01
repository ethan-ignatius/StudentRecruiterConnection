# job_board/job_board/urls.py
from django.contrib import admin
from django.urls import path, include
from . import views
from accounts.views import CustomLoginView  # ⬅️ added

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),  # ⬅️ added
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("profiles/", include(("profiles.urls", "profiles"), namespace="profiles")),
    path("jobs/", include(("jobs.urls", "jobs"), namespace="jobs")),
    path("", include("django.contrib.auth.urls")),
    path("recommended/", include('recommended.urls')),
]
