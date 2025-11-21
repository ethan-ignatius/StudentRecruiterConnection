from django.urls import path
from . import views

app_name = "recommended"

urlpatterns = [
    path("", views.index, name="index"),

    path("job/<int:job_id>/", views.recommended_candidates, name="recommended_candidates"),
]
