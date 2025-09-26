from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import User
from profiles.models import JobSeekerProfile

# Create your views here.
@login_required
def index(request):
    profile_type = request.user.account_type
    if profile_type == User.AccountType.JOB_SEEKER:
        return recommended_jobs(request)
    else:
        return recommended_candidates(request)

@login_required
def recommended_jobs(request):
    profile = JobSeekerProfile.objects.get(user=request.user)
    skills = profile.skills.all()
    return render(request, "recommended/recommended_jobs.html", {"profile": profile, "skills": skills})

def recommended_candidates(request):
    return render(request, "recommended/recommended_candidates.html")