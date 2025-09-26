# job_board/recommended/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, F
from accounts.models import User
from profiles.models import JobSeekerProfile
from jobs.models import Job

@login_required
def index(request):
    if request.user.account_type == User.AccountType.JOB_SEEKER:
        return recommended_jobs(request)
    return recommended_candidates(request)

@login_required
def recommended_jobs(request):
    profile = JobSeekerProfile.objects.get(user=request.user)
    seeker_skills = profile.skills.values_list("id", flat=True)

    # Base: only active jobs
    qs = Job.objects.filter(status=Job.Status.ACTIVE)

    # Annotate matches:
    # - req_match: overlap with required_skills
    # - nice_match: overlap with nice_to_have_skills
    # - score = 2*req_match + 1*nice_match
    qs = qs.annotate(
        req_match=Count("required_skills", filter=Q(required_skills__in=seeker_skills), distinct=True),
        nice_match=Count("nice_to_have_skills", filter=Q(nice_to_have_skills__in=seeker_skills), distinct=True),
    ).annotate(
        score=F("req_match") * 2 + F("nice_match")
    ).filter(
        # Only show jobs that match at least one skill
        Q(req_match__gt=0) | Q(nice_match__gt=0)
    ).order_by("-score", "-created_at").distinct()

    # (Optional) pull the actually matched skill names to show chips
    # Doing it in Python for clarity:
    jobs_with_matches = []
    seeker_skill_ids = set(seeker_skills)
    for job in qs.prefetch_related("required_skills", "nice_to_have_skills"):
        matched_required = [s for s in job.required_skills.all() if s.id in seeker_skill_ids]
        matched_nice = [s for s in job.nice_to_have_skills.all() if s.id in seeker_skill_ids]
        jobs_with_matches.append({
            "job": job,
            "score": job.score,
            "matched_required": matched_required,
            "matched_nice": matched_nice,
        })

    return render(
        request,
        "recommended/recommended_jobs.html",
        {"profile": profile, "skills": profile.skills.all(), "recommendations": jobs_with_matches},
    )

def recommended_candidates(request):
    return render(request, "recommended/recommended_candidates.html")
