# job_board/accounts/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/",  views.CustomLoginView.as_view(), name="login"),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('inbox/', views.inbox, name='inbox'),
    path('send-message/', views.send_message, name='send_message'),
    path('send-message/<int:recipient_id>/', views.send_message, name='send_message_to'),
    path('send-email/<int:recipient_id>/', views.send_email_message, name='send_email_message'),
    path('messages/', views.conversations, name='conversations'),
    path('messages/<int:user_id>/', views.conversations, name='conversation'),
]
