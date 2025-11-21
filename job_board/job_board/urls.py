from django.contrib import admin
from django.urls import path, include
from . import views
from accounts.views import CustomLoginView
from django.contrib.auth import views as auth_views
from jobs.admin import admin_site  # ✅ import your custom admin site

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path("", views.home, name="home"),
    path("admin/", admin_site.urls),  # ✅ use JobBoardAdminSite
    path("accounts/", include("accounts.urls")),
    path("profiles/", include(("profiles.urls", "profiles"), namespace="profiles")),
    path("jobs/", include(("jobs.urls", "jobs"), namespace="jobs")),
    path("", include("django.contrib.auth.urls")),
    path("recommended/", include('recommended.urls')),
]
