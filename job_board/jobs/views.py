from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.urls import reverse
from .models import Job, JobApplication, ApplicationStatusChange
from django.db.models import Case, When, Value, IntegerField
from .forms import JobSearchForm, JobForm, QuickApplicationForm, ApplicationStatusForm
from django.db.models import Prefetch
from math import radians, sin, cos, asin, sqrt
from jobs.geocoding import geocode_city_state

# ------------------------------------------------------------
# Search / discovery
# ------------------------------------------------------------
EARTH_MI = 3958.7613

def _ensure_coords(job):
    """Attach latitude/longitude to a job using its 'City, ST' location."""
    if getattr(job, "latitude", None) is not None and getattr(job, "longitude", None) is not None:
        return True
    loc = (job.location or "").strip()
    if not loc or "," not in loc:
        return False
    city, state = [p.strip() for p in loc.split(",", 1)]
    coords = geocode_city_state(city, state)  # caches in CityCoord
    if coords:
        job.latitude, job.longitude = coords  # attach for this request
        return True
    return False

def hav_miles(lat1, lon1, lat2, lon2):
    dlat = radians(lat2 - lat1); dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return 2 * EARTH_MI * asin(sqrt(a))

def job_search(request):
    form = JobSearchForm(request.GET or None)

    qs = Job.objects.filter(status=Job.Status.ACTIVE).select_related("posted_by")

    if form.is_valid():
        cd = form.cleaned_data

        if cd.get("q"):
            qs = qs.filter(
                Q(title__icontains=cd["q"]) |
                Q(company__icontains=cd["q"]) |
                Q(description__icontains=cd["q"])
            )

        if cd.get("location"):
            qs = qs.filter(location__icontains=cd["location"])

        if cd.get("work_type"):
            qs = qs.filter(work_type=cd["work_type"])

        if cd.get("salary_min") not in (None, ""):
            v = cd["salary_min"]
            qs = qs.filter(Q(salary_min__gte=v) | Q(salary_max__gte=v))

        if cd.get("salary_max") not in (None, ""):
            v = cd["salary_max"]
            qs = qs.filter(Q(salary_max__lte=v) | Q(salary_min__lte=v))

        visa = cd.get("visa_sponsorship")
        if visa is not None:
            qs = qs.filter(visa_sponsorship=visa)

        skills = cd.get("skills") or []
        if skills:
            qs = qs.filter(
                Q(required_skills__name__in=skills) |
                Q(nice_to_have_skills__name__in=skills)
            ).distinct()

    qs = qs.order_by("-created_at")
    jobs = list(qs)

    if form.is_valid():
        radius = form.cleaned_data.get("radius")
        lat = form.cleaned_data.get("lat")
        lng = form.cleaned_data.get("lng")

        if radius not in (None, "") and lat is not None and lng is not None:
            had_any_geocoded = False

            for j in jobs:
                # Treat fully-remote as 0 miles so they always pass distance filters
                if getattr(j, "work_type", None) == Job.WorkType.REMOTE:
                    j.distance_from_device = 0.0
                    had_any_geocoded = True
                    continue

                # Ensure the job has coords; try to geocode City, ST if missing
                if _ensure_coords(j) and j.latitude is not None and j.longitude is not None:
                    d = hav_miles(lat, lng, j.latitude, j.longitude)
                    j.distance_from_device = round(d, 2)
                    had_any_geocoded = True
                else:
                    j.distance_from_device = None

            # Only filter if at least one job had a distance computed
            if had_any_geocoded:
                jobs = [
                    j for j in jobs
                    if (j.distance_from_device is not None and j.distance_from_device <= radius)
                ]

    # --- Distance filtering only if a radius is provided ---
    if form.is_valid():
        commute_radius = form.cleaned_data.get("commute_radius")

        if commute_radius not in (None, ""):
            profile_city = profile_state = None

            # 🔧 Adjust to your actual profile model fields
            if request.user.is_authenticated and hasattr(request.user, "profile"):
                prof = request.user.profile

                # Case A: single location string like "City, ST"
                loc = getattr(prof, "location", None)
                if loc:
                    parts = [p.strip() for p in str(loc).split(",")]
                    if len(parts) >= 2:
                        profile_city = parts[0]
                        profile_state = parts[1]
                    elif len(parts) == 1:
                        # If only one token, treat it as city and leave state blank
                        profile_city = parts[0]

                # Case B: explicit fields on the profile (fallbacks)
                if not profile_city:
                    profile_city = getattr(prof, "city", None)
                if not profile_state:
                    profile_state = getattr(prof, "state", None)

            profile_lat = profile_lng = None
            if profile_city or profile_state:
                try:
                    # ✅ Pass two args as required
                    latlng = geocode_city_state(profile_city or "", profile_state or "")
                    if latlng:
                        profile_lat, profile_lng = latlng
                except Exception:
                    # Leave as None if geocoding fails
                    profile_lat = profile_lng = None

            if profile_lat is None or profile_lng is None:
                # No-op if we can't get a profile location; optionally flash a message
                pass
            else:
                had_any_geocoded = False
                for j in jobs:
                    # Remote = 0 miles
                    if getattr(j, "work_type", None) == Job.WorkType.REMOTE:
                        j.distance_miles = 0.0
                        had_any_geocoded = True
                        continue

                    if _ensure_coords(j) and j.latitude is not None and j.longitude is not None:
                        d = hav_miles(profile_lat, profile_lng, j.latitude, j.longitude)
                        j.distance_miles = round(d, 2)
                        had_any_geocoded = True
                    else:
                        j.distance_miles = None

                if had_any_geocoded:
                    jobs = [
                        j for j in jobs
                        if (j.distance_miles is not None and j.distance_miles <= commute_radius)
                    ]

                if commute_radius not in (None, "") and (profile_lat is not None and profile_lng is not None):
                    user_commute_location = {"lat": profile_lat, "lng": profile_lng, "radius": commute_radius}


    paginator = Paginator(jobs, 5)
    page_obj = paginator.get_page(request.GET.get("page"))

    jobs_for_map = [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "location": j.location or "",
            "url": reverse("jobs:detail", args=[j.id]),
            "latitude": j.latitude,
            "longitude": j.longitude,
        }
        for j in page_obj.object_list
        if j.latitude is not None and j.longitude is not None
    ]

    applied_job_ids = set()
    if request.user.is_authenticated and hasattr(request.user, "is_job_seeker") and request.user.is_job_seeker():
        visible_ids = [j.id for j in page_obj.object_list]
        applied_job_ids = set(
            JobApplication.objects.filter(applicant=request.user, job_id__in=visible_ids)
                                  .values_list("job_id", flat=True)
        )

    user_location = None
    user_commute_location = None
    
    if form.is_valid():
        lat = form.cleaned_data.get("lat")
        lng = form.cleaned_data.get("lng")
        if lat is not None and lng is not None:
            user_location = {"lat": lat, "lng": lng}

    context = {
        "form": form,
        "jobs": page_obj,
        "total_count": paginator.count,
        "has_filters": any(v for k, v in (request.GET or {}).items() if k not in ("page", "search") and v),
        "jobs_for_map": jobs_for_map,
        "applied_job_ids": applied_job_ids,
        "user_location": user_location,
        "user_commute_location": user_commute_location,
    }
    return render(request, "jobs/job_search.html", context)

# ------------------------------------------------------------
# Detail + apply
# ------------------------------------------------------------
@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)

    can_apply = (
        job.status == Job.Status.ACTIVE
        and request.user.is_authenticated
        and request.user.is_job_seeker()
        and job.posted_by_id != request.user.id
        and not JobApplication.objects.filter(job=job, applicant=request.user).exists()
    )

    user_applied = False
    user_application = None
    if request.user.is_authenticated and request.user.is_job_seeker():
        try:
            user_application = JobApplication.objects.get(job=job, applicant=request.user)
            user_applied = True
        except JobApplication.DoesNotExist:
            pass

    quick_form = QuickApplicationForm(user=request.user, job=job) if can_apply else None
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'can_apply': can_apply,
        'user_applied': user_applied,
        'user_application': user_application,
        'quick_form': quick_form,
    })


@login_required
@require_POST
def quick_apply(request, pk):
    job = get_object_or_404(Job, pk=pk, status=Job.Status.ACTIVE)

    if not request.user.is_job_seeker():
        return JsonResponse({'success': False, 'error': 'Only job seekers can apply.'}, status=403)
    if job.posted_by_id == request.user.id:
        return JsonResponse({'success': False, 'error': 'You cannot apply to your own job.'}, status=400)
    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        return JsonResponse({'success': False, 'error': 'You have already applied to this job.'}, status=400)

    form = QuickApplicationForm(request.POST, user=request.user, job=job)
    if not form.is_valid():
        return JsonResponse({'success': False, 'error': 'Please provide valid information.'}, status=400)

    application = JobApplication.objects.create(
        job=job,
        applicant=request.user,
        cover_letter=form.cleaned_data.get('tailored_note', '').strip() or None,
    )

    # Record submission; avoid NULL for old_status
    ApplicationStatusChange.objects.create(
        application=application,
        old_status=application.status,          # first row: same -> same
        new_status=application.status,
        changed_by=request.user,                # ← REQUIRED
        notes='Application submitted via Quick Apply'
    )

    return JsonResponse({
        'success': True,
        'message': 'Application submitted successfully.',
        'redirect_url': reverse('jobs:application_detail', args=[application.pk])
    })

# ------------------------------------------------------------
# Recruiter / management (unchanged)
# ------------------------------------------------------------
@login_required
def post_job(request):
    if not request.user.is_recruiter():
        raise Http404("Job not found")

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            job.save()
            form.save_m2m()
            messages.success(request, "Job posted successfully.")
            return redirect('jobs:detail', pk=job.pk)
    else:
        form = JobForm()
    return render(request, 'jobs/post_jobs.html', {'form': form})


@login_required
def my_jobs(request):
    # Order: status (Active, Draft, Closed) then title A→Z
    status_order = Case(
        When(status=Job.Status.ACTIVE, then=Value(0)),
        When(status=Job.Status.DRAFT, then=Value(1)),
        When(status=Job.Status.CLOSED, then=Value(2)),
        default=Value(3),
        output_field=IntegerField(),
    )

    qs = (
        Job.objects
        .filter(posted_by=request.user)
        .annotate(_status_order=status_order)
        .order_by('_status_order', 'title')
    )

    # 5 per page (same page size as seeker search)
    paginator = Paginator(qs, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Keep existing templates working by exposing both `jobs` and `page_obj`
    return render(request, 'jobs/my_posted_jobs.html', {
        'jobs': page_obj,        # iterable page for existing loops
        'page_obj': page_obj,    # if template wants explicit page object
        'paginator': paginator,  # optional
    })


@login_required
# job_board/jobs/views.py (function replaced)
def job_applications(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if job.posted_by != request.user:
        raise Http404("Job not found")

    applications = (
        JobApplication.objects
        .filter(job=job)
        .select_related('applicant', 'applicant__profile')
        .order_by('-applied_at')
    )

    # Stable status ordering
    status_order = [
        JobApplication.Status.APPLIED,
        JobApplication.Status.REVIEWING,
        JobApplication.Status.INTERVIEW,
        JobApplication.Status.OFFER,
        JobApplication.Status.ACCEPTED,
        JobApplication.Status.REJECTED,
        JobApplication.Status.WITHDRAWN,
    ]
    status_groups = {status: [] for status in status_order}
    for app in applications:
        status_groups.setdefault(app.status, []).append(app)

    context = {
        'job': job,
        'status_groups': status_groups,
        'total_applications': applications.count(),
        'status_form': ApplicationStatusForm(),
    }
    return render(request, 'jobs/job_applications.html', context)

@login_required
def application_detail(request, pk):
    from django.db.models import Prefetch  # local import to keep other files untouched

    # Fetch application + applicant profile + related info
    application = (
        JobApplication.objects
        .select_related('job', 'applicant', 'applicant__profile')
        .prefetch_related(
            Prefetch('applicant__profile__experiences'),
            Prefetch('applicant__profile__educations'),
            Prefetch('applicant__profile__links'),
        )
        .get(pk=pk)
    )

    # Permission: applicant themselves OR the recruiter who owns the job
    if not (application.applicant == request.user or application.job.posted_by == request.user):
        raise Http404("Application not found")

    # Build the status form (only recruiters can submit changes)
    if request.method == 'POST' and request.user == application.job.posted_by:
        form = ApplicationStatusForm(request.POST, instance=application)
        if form.is_valid():
            old_status = application.status
            application = form.save()
            ApplicationStatusChange.objects.create(
                application=application,
                old_status=old_status,
                new_status=application.status,
                changed_by=request.user,
                notes='Status updated by recruiter'
            )
            messages.success(request, "Application status updated.")
            return redirect('jobs:application_detail', pk=application.pk)
    else:
        form = ApplicationStatusForm(instance=application)

    # History unchanged
    history = ApplicationStatusChange.objects.filter(application=application).order_by('changed_at')

    # IMPORTANT: pass the same context the Seeker profile view uses
    return render(request, 'jobs/application_detail.html', {
        'application': application,
        'form': form,  # now always defined
        'history': history,
        # Keep the original variable for compatibility with any existing template references
        'applicant_profile': getattr(application.applicant, 'profile', None),
        # Provide the exact context used by Seeker profile
        'profile': getattr(application.applicant, 'profile', None),
        'experiences_qs': getattr(application.applicant, 'profile', None).experiences.filter(show=True) if getattr(application.applicant, 'profile', None) else [],
        'educations_qs': getattr(application.applicant, 'profile', None).educations.filter(show=True) if getattr(application.applicant, 'profile', None) else [],
        'links_qs': getattr(application.applicant, 'profile', None).links.filter(show=True) if getattr(application.applicant, 'profile', None) else [],
    })

@login_required
def edit_job(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if job.posted_by != request.user:
        raise Http404("Job not found")

    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            job = form.save()
            messages.success(request, "Job updated successfully.")
            return redirect('jobs:detail', pk=job.pk)
    else:
        form = JobForm(instance=job)
    return render(request, 'jobs/post_jobs.html', {'form': form})


@login_required
def close_job(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if job.posted_by != request.user:
        raise Http404("Job not found")
    if request.method == 'POST':
        job.status = Job.Status.CLOSED
        job.save(update_fields=['status'])
        messages.success(request, "Job closed. It will no longer be visible to job seekers.")
    return redirect('jobs:my_jobs')


@login_required
def reopen_job(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if job.posted_by != request.user:
        raise Http404("Job not found")
    if request.method == 'POST':
        job.status = Job.Status.ACTIVE
        job.save(update_fields=['status'])
        messages.success(request, "Job reopened and visible to job seekers.")
    return redirect('jobs:my_jobs')
