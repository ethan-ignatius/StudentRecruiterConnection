from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse, Http404, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.urls import reverse
from .models import Job, JobApplication, ApplicationStatusChange, JobReport
from django.db.models import Case, When, Value, IntegerField
from .forms import JobSearchForm, JobForm, QuickApplicationForm, ApplicationStatusForm, JobReportForm
from .notifications import notify_admins_of_report
from django.db.models import Prefetch
from math import radians, sin, cos, asin, sqrt
from jobs.geocoding import geocode_city_state
from django.utils import timezone
from django.contrib.admin.views.decorators import staff_member_required
from datetime import timedelta
import json  # ← added
import csv

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
    dlat = radians(lat2 - lat1); dlon = radians(lat2 - lon1)
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

    # ---------------- Recruiter applicant map (additive only) ----------------
    # Always render the section for the job owner; pins appear if any can be geocoded.
    applicant_markers = []
    try:
        if request.user.is_authenticated and job.posted_by_id == request.user.id:
            apps_qs = (
                JobApplication.objects
                .filter(job=job)
                .select_related('applicant', 'applicant__profile')
                .order_by('-applied_at')
            )
            for app in apps_qs:
                prof = getattr(app.applicant, "profile", None)
                loc = getattr(prof, "location", None) if prof else None
                if not loc:
                    continue
                parts = [p.strip() for p in str(loc).split(",")]
                city = parts[0] if parts else ""
                state = parts[1] if len(parts) > 1 else ""
                coords = geocode_city_state(city, state) if city else None
                if not coords:
                    continue
                lat, lng = coords
                label = (app.applicant.get_full_name() or getattr(app.applicant, "username", "")) or "Applicant"
                profile_url = ""
                try:
                    if hasattr(app.applicant, "username"):
                        profile_url = reverse('profiles:public_profile', args=[app.applicant.username])
                except Exception:
                    profile_url = ""
                applicant_markers.append({
                    "lat": lat,
                    "lng": lng,
                    "label": label,
                    "location": loc,
                    "status": app.status,
                    "profile_url": profile_url,
                })
    except Exception:
        # Never break the page if mapping fails
        applicant_markers = []

    # Check for reports (admin only)
    job_reports = []
    if request.user.is_authenticated and request.user.is_staff:
        job_reports = JobReport.objects.filter(job=job).select_related('reported_by').order_by('-created_at')

    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'can_apply': can_apply,
        'user_applied': user_applied,
        'user_application': user_application,
        'quick_form': quick_form,
        'applicant_markers_json': json.dumps(applicant_markers),      # ← added
        'job_reports': job_reports,
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
def my_applications(request):
    """
    Job seeker dashboard: list the current user's job applications,
    grouped by status, newest first.
    """
    # Recruiters shouldn't land here; bounce them to their dashboard
    # (User model exposes is_recruiter() in this project)
    if hasattr(request.user, "is_recruiter") and request.user.is_recruiter():
        messages.info(request, "Recruiters manage postings; showing your jobs instead.")
        return redirect("jobs:my_jobs")

    applications = (
        JobApplication.objects
        .select_related("job")
        .filter(applicant=request.user)
        .order_by("-applied_at")
    )

    # Group apps by status for the template's quick stats/cards
    status_order = [
        JobApplication.Status.APPLIED,
        JobApplication.Status.REVIEWING,
        JobApplication.Status.INTERVIEW,
        JobApplication.Status.OFFER,
        JobApplication.Status.ACCEPTED,
        JobApplication.Status.REJECTED,
    ]
    status_groups = {status: [] for status in status_order}
    for app in applications:
        status_groups.setdefault(app.status, []).append(app)

    return render(
        request,
        "jobs/my_applications.html",
        {
            "applications": applications,
            "status_groups": status_groups,
        },
    )


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
    application = (
        JobApplication.objects
        .select_related('job', 'applicant', 'applicant__profile')
        .get(pk=pk)
    )
    is_recruiter_owner = (request.user == application.job.posted_by)
    is_applicant_owner = (request.user == application.applicant)
    if not (is_recruiter_owner or is_applicant_owner):
        raise Http404("Application not found")

    if request.method == 'POST' and is_recruiter_owner:
        form = ApplicationStatusForm(request.POST, instance=application, request_user=request.user)
        if form.is_valid():
            new_status = form.cleaned_data['status']
            if new_status == JobApplication.Status.ACCEPTED:
                messages.error(request, "Recruiters can’t mark as Accepted. Ask the candidate to accept the offer.")
                return redirect('jobs:application_detail', pk=application.pk)

            old_status = application.status
            if new_status != old_status:
                # Use direct update + refresh to avoid any weird resets
                JobApplication.objects.filter(pk=application.pk).update(
                    status=new_status, updated_at=timezone.now()
                )
                application.refresh_from_db()
                ApplicationStatusChange.objects.create(
                    application=application,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=request.user,
                    notes='Status updated by recruiter'
                )
                messages.success(request, f"Status updated to {application.get_status_display()}.")
        else:
            messages.error(request, "Please fix the errors below.")

        return redirect('jobs:application_detail', pk=application.pk)
    else:
        form = ApplicationStatusForm(instance=application, request_user=request.user) if is_recruiter_owner else None

    history = ApplicationStatusChange.objects.filter(application=application).order_by('changed_at')

    return render(request, 'jobs/application_detail.html', {
        'application': application,
        'form': form,
        'history': history,
    })

@login_required
@require_POST
def accept_offer(request, pk):
    application = get_object_or_404(JobApplication, pk=pk)

    # Only the applicant can accept
    if request.user != application.applicant:
        raise Http404("Application not found")

    if application.status != JobApplication.Status.OFFER:
        messages.error(request, "You can only accept an active offer.")
        return redirect('jobs:application_detail', pk=application.pk)

    old_status = application.status
    JobApplication.objects.filter(pk=application.pk).update(
        status=JobApplication.Status.ACCEPTED, updated_at=timezone.now()
    )
    application.refresh_from_db()

    ApplicationStatusChange.objects.create(
        application=application,
        old_status=old_status,
        new_status=JobApplication.Status.ACCEPTED,
        changed_by=request.user,
        notes="Candidate accepted the offer"
    )
    messages.success(request, "Offer accepted. 🎉")
    return redirect('jobs:application_detail', pk=application.pk)


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

# job_board/jobs/views.py  (add anywhere below the view above)
@login_required
@require_POST
def accept_offer(request, pk):
    application = get_object_or_404(JobApplication, pk=pk)

    # Only the applicant can accept
    if request.user != application.applicant:
        raise Http404("Application not found")

    if application.status != JobApplication.Status.OFFER:
        messages.error(request, "You can only accept an active offer.")
        return redirect('jobs:application_detail', pk=application.pk)

    old_status = application.status
    application.status = JobApplication.Status.ACCEPTED
    application.save(update_fields=['status', 'updated_at'])

    ApplicationStatusChange.objects.create(
        application=application,
        old_status=old_status,
        new_status=JobApplication.Status.ACCEPTED,
        changed_by=request.user,
        notes="Candidate accepted the offer"
    )

    messages.success(request, "Offer accepted. 🎉")
    return redirect('jobs:application_detail', pk=application.pk)

@login_required
@require_POST
def update_application_status(request, pk):
    """Recruiter-only: set application status (cannot set Accepted)."""
    application = get_object_or_404(JobApplication, pk=pk)

    # only the job owner can update
    if request.user != application.job.posted_by:
        raise Http404("Application not found")

    new_status = request.POST.get("status")

    # recruiters CANNOT set Accepted; everything else is ok
    allowed = {
        JobApplication.Status.APPLIED,
        JobApplication.Status.REVIEWING,
        JobApplication.Status.INTERVIEW,
        JobApplication.Status.OFFER,
        JobApplication.Status.REJECTED,
    }
    if new_status not in allowed:
        messages.error(request, "Invalid status selection.")
        return redirect('jobs:application_detail', pk=application.pk)

    old_status = application.status
    if new_status != old_status:
        # write directly to DB, then refresh the instance we render
        JobApplication.objects.filter(pk=application.pk).update(
            status=new_status, updated_at=timezone.now()
        )
        application.refresh_from_db()

        ApplicationStatusChange.objects.create(
            application=application,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            notes='Status updated by recruiter'
        )
        messages.success(request, f"Status updated to {application.get_status_display()}.")

    return redirect('jobs:application_detail', pk=application.pk)

@staff_member_required
def moderation_dashboard(request):
    """Admin dashboard for moderating job posts"""
    # Get recent jobs (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_jobs = Job.objects.filter(
        created_at__gte=week_ago
    ).select_related('posted_by').order_by('-created_at')[:20]
    
    # Get unreviewed reports
    unreviewed_reports = JobReport.objects.filter(
        reviewed=False
    ).select_related('job', 'reported_by').order_by('-created_at')[:10]
    
    # Get moderation statistics
    stats = {
        'active_jobs': Job.objects.filter(status='ACTIVE').count(),
        'removed_jobs': Job.objects.filter(status='REMOVED').count(),
        'closed_jobs': Job.objects.filter(status='CLOSED').count(),
        'total_jobs': Job.objects.count(),
        'unreviewed_reports': JobReport.objects.filter(reviewed=False).count(),
        'total_reports': JobReport.objects.count(),
    }
    
    return render(request, 'admin/jobs/moderation_dashboard.html', {
        'recent_jobs': recent_jobs,
        'unreviewed_reports': unreviewed_reports,
        'stats': stats,
    })

@login_required
def report_job(request, pk):
    """Allow users to report inappropriate job posts"""
    job = get_object_or_404(Job, pk=pk)
    
    # Check if user has already reported this job
    existing_report = JobReport.objects.filter(job=job, reported_by=request.user).first()
    if existing_report:
        messages.info(request, "You have already reported this job.")
        return redirect('jobs:detail', pk=pk)
    
    if request.method == 'POST':
        form = JobReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.job = job
            report.reported_by = request.user
            report.save()
            
            # Notify administrators
            notify_admins_of_report(report)
            
            messages.success(request, "Thank you for reporting this job. Our team will review it.")
            return redirect('jobs:detail', pk=pk)
    else:
        form = JobReportForm()
    
    return render(request, 'jobs/report_job.html', {
        'form': form,
        'job': job,
    })

# ------------------------------------------------------------
# CSV Export Views (User Story 20)
# ------------------------------------------------------------

@login_required
def export_job_applications_csv(request, job_pk):
    """Export all applications for a specific job as CSV (Recruiter only)"""
    job = get_object_or_404(Job, pk=job_pk)

    # Only the job owner can export applications
    if job.posted_by != request.user:
        raise Http404("Job not found")

    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="applications_{job.title.replace(" ", "_")}_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    # Write header row
    writer.writerow([
        'Application ID',
        'Applicant Name',
        'Applicant Email',
        'Applicant Username',
        'Status',
        'Applied Date',
        'Last Updated',
        'Cover Letter Preview',
        'Applicant Location',
        'Applicant Headline',
        'Skills'
    ])

    # Query all applications for this job
    applications = JobApplication.objects.filter(job=job).select_related(
        'applicant',
        'applicant__profile'
    ).prefetch_related('applicant__profile__skills').order_by('-applied_at')

    # Write data rows
    for app in applications:
        profile = getattr(app.applicant, 'profile', None)
        skills = ', '.join([skill.name for skill in profile.skills.all()]) if profile else ''
        cover_letter_preview = app.cover_letter[:100] + '...' if len(app.cover_letter) > 100 else app.cover_letter

        writer.writerow([
            app.id,
            app.applicant.get_full_name() or app.applicant.username,
            app.applicant.email,
            app.applicant.username,
            app.get_status_display(),
            app.applied_at.strftime('%Y-%m-%d %H:%M'),
            app.updated_at.strftime('%Y-%m-%d %H:%M'),
            cover_letter_preview,
            profile.location if profile else '',
            profile.headline if profile else '',
            skills
        ])

    return response

@login_required
def export_all_applications_csv(request):
    """Export all applications for the logged-in recruiter's jobs as CSV"""
    if not request.user.is_recruiter():
        raise Http404("Access denied")

    # Get all jobs posted by this recruiter
    recruiter_jobs = Job.objects.filter(posted_by=request.user)

    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="all_applications_{request.user.username}_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    # Write header row
    writer.writerow([
        'Job Title',
        'Job Company',
        'Application ID',
        'Applicant Name',
        'Applicant Email',
        'Applicant Username',
        'Status',
        'Applied Date',
        'Last Updated',
        'Cover Letter Preview',
        'Applicant Location',
        'Applicant Headline',
        'Skills'
    ])

    # Query all applications for recruiter's jobs
    applications = JobApplication.objects.filter(
        job__in=recruiter_jobs
    ).select_related(
        'job',
        'applicant',
        'applicant__profile'
    ).prefetch_related('applicant__profile__skills').order_by('-applied_at')

    # Write data rows
    for app in applications:
        profile = getattr(app.applicant, 'profile', None)
        skills = ', '.join([skill.name for skill in profile.skills.all()]) if profile else ''
        cover_letter_preview = app.cover_letter[:100] + '...' if len(app.cover_letter) > 100 else app.cover_letter

        writer.writerow([
            app.job.title,
            app.job.company,
            app.id,
            app.applicant.get_full_name() or app.applicant.username,
            app.applicant.email,
            app.applicant.username,
            app.get_status_display(),
            app.applied_at.strftime('%Y-%m-%d %H:%M'),
            app.updated_at.strftime('%Y-%m-%d %H:%M'),
            cover_letter_preview,
            profile.location if profile else '',
            profile.headline if profile else '',
            skills
        ])

    return response

@staff_member_required
def export_jobs_csv(request):
    """Export all jobs as CSV (Admin only)"""
    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="all_jobs_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    # Write header row
    writer.writerow([
        'Job ID',
        'Title',
        'Company',
        'Location',
        'Work Type',
        'Status',
        'Posted By',
        'Posted Date',
        'Salary Min',
        'Salary Max',
        'Currency',
        'Visa Sponsorship',
        'Required Skills',
        'Nice to Have Skills',
        'Application Count',
        'Description Preview'
    ])

    # Query all jobs
    jobs = Job.objects.all().select_related('posted_by').prefetch_related(
        'required_skills',
        'nice_to_have_skills',
        'applications'
    ).order_by('-created_at')

    # Write data rows
    for job in jobs:
        required_skills = ', '.join([skill.name for skill in job.required_skills.all()])
        nice_skills = ', '.join([skill.name for skill in job.nice_to_have_skills.all()])
        description_preview = job.description[:200] + '...' if len(job.description) > 200 else job.description

        writer.writerow([
            job.id,
            job.title,
            job.company,
            job.location,
            job.get_work_type_display(),
            job.get_status_display(),
            job.posted_by.username,
            job.created_at.strftime('%Y-%m-%d %H:%M'),
            job.salary_min or '',
            job.salary_max or '',
            job.salary_currency,
            'Yes' if job.visa_sponsorship else 'No',
            required_skills,
            nice_skills,
            job.applications.count(),
            description_preview.replace('\n', ' ').replace('\r', ' ')
        ])

    return response

@staff_member_required
def export_users_csv(request):
    """Export all users as CSV (Admin only)"""
    from accounts.models import User

    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="all_users_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    # Write header row
    writer.writerow([
        'User ID',
        'Username',
        'Email',
        'First Name',
        'Last Name',
        'Account Type',
        'Date Joined',
        'Last Login',
        'Is Active',
        'Is Staff',
        'Profile Headline',
        'Profile Location',
        'Skills Count'
    ])

    # Query all users
    users = User.objects.all().prefetch_related('profile__skills').order_by('-date_joined')

    # Write data rows
    for user in users:
        profile = getattr(user, 'profile', None)
        skills_count = profile.skills.count() if profile else 0

        writer.writerow([
            user.id,
            user.username,
            user.email,
            user.first_name,
            user.last_name,
            user.get_account_type_display(),
            user.date_joined.strftime('%Y-%m-%d %H:%M'),
            user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else '',
            'Yes' if user.is_active else 'No',
            'Yes' if user.is_staff else 'No',
            profile.headline if profile else '',
            profile.location if profile else '',
            skills_count
        ])

    return response
