# job_board/accounts/views.py
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2", "account_type")

def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(reverse("login"))
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form})


class CustomLoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    def get_success_url(self):
        user = self.request.user
        try:
            if user.is_recruiter():
                return reverse("jobs:my_jobs")
        except Exception:
            pass
        return reverse("profiles:my_profile")
