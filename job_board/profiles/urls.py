from django.urls import path
from . import views

app_name = "profiles"

urlpatterns = [
    path("me/", views.my_profile, name="my_profile"),
    path("me/edit/", views.edit_profile, name="edit_profile"),
    path("u/<str:username>/", views.public_profile, name="public_profile"),
]
