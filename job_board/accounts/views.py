from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.auth import login
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)

    def clean(self):
        cleaned = super().clean()
        return cleaned

    def _post_clean(self):
        super()._post_clean()
        try:
            pw2_errors = self.errors.get("password2")
        except Exception:
            pw2_errors = None
        if pw2_errors and not self.errors.get("password1"):
            for err in pw2_errors:
                self.add_error("password1", err)
            try:
                self.errors.pop("password2", None)
            except Exception:
                pass

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
