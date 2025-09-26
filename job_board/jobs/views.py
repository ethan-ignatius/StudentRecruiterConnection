from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404

from accounts.models import User
from profiles.models import Skill
from .models import Job, JobApplication
from .forms import JobSearchForm, JobForm, JobApplicationForm
from django.urls import reverse
from django.conf import settings

def job_search(request):
    """Job search view with filtering."""
    form = JobSearchForm(request.GET)
    jobs = Job.objects.filter(status=Job.Status.ACTIVE).select_related('posted_by')
    
    if form.is_valid():
        # Text search in title, company, description
        q = form.cleaned_data.get('q')
        if q:
            jobs = jobs.filter(
                Q(title__icontains=q) |
                Q(company__icontains=q) |
                Q(description__icontains=q)
            )
        
        # Location filter
        location = form.cleaned_data.get('location')
        if location:
            jobs = jobs.filter(location__icontains=location)
        
        # Work type filter
        work_type = form.cleaned_data.get('work_type')
        if work_type:
            jobs = jobs.filter(work_type=work_type)
        
        # Salary range filters
        salary_min = form.cleaned_data.get('salary_min')
        salary_max = form.cleaned_data.get('salary_max')
        
        if salary_min:
            jobs = jobs.filter(
                Q(salary_max__gte=salary_min) | Q(salary_max__isnull=True)
            )
        
        if salary_max:
            jobs = jobs.filter(
                Q(salary_min__lte=salary_max) | Q(salary_min__isnull=True)
            )
        
        # Visa sponsorship filter
        if form.cleaned_data.get('visa_sponsorship'):
            jobs = jobs.filter(visa_sponsorship=True)
        
        # Skills filter
        skill_names = form.cleaned_data.get('skills', [])
        if skill_names:
            # Find jobs that have any of the specified skills as required or nice-to-have
            skill_objs = Skill.objects.filter(name__in=skill_names)
            jobs = jobs.filter(
                Q(required_skills__in=skill_objs) | 
                Q(nice_to_have_skills__in=skill_objs)
            ).distinct()
    
    # Pagination
    paginator = Paginator(jobs, 10)  # Show 10 jobs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    map_queryset = jobs

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
    for j in map_queryset
    if j.latitude is not None and j.longitude is not None
]
    
    context = {
        'form': form,
        'jobs': page_obj,
        'total_count': paginator.count,
        'has_filters': any(request.GET.values()),
        "jobs_for_map": jobs_for_map,
    }
    return render(request, 'jobs/job_search.html', context)


def job_detail(request, pk):
    """Job detail view."""
    job = get_object_or_404(Job, pk=pk, status=Job.Status.ACTIVE)
    
    # Check if current user has already applied
    user_applied = False
    user_application = None
    if request.user.is_authenticated:
        try:
            user_application = JobApplication.objects.get(job=job, applicant=request.user)
            user_applied = True
        except JobApplication.DoesNotExist:
            pass
    
    context = {
        'job': job,
        'user_applied': user_applied,
        'user_application': user_application,
        'can_apply': (
            request.user.is_authenticated and 
            request.user.is_job_seeker() and 
            not user_applied and
            job.posted_by != request.user
        )
    }
    
    return render(request, 'jobs/job_detail.html', context)


@login_required
def apply_for_job(request, pk):
    """Apply for a job."""
    job = get_object_or_404(Job, pk=pk, status=Job.Status.ACTIVE)
    
    # Check permissions
    if not request.user.is_job_seeker():
        messages.error(request, "Only job seekers can apply for jobs.")
        return redirect('jobs:detail', pk=pk)
    
    if job.posted_by == request.user:
        messages.error(request, "You cannot apply to your own job posting.")
        return redirect('jobs:detail', pk=pk)
    
    # Check if already applied
    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        messages.warning(request, "You have already applied for this job.")
        return redirect('jobs:detail', pk=pk)
    
    if request.method == 'POST':
        form = JobApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.applicant = request.user
            application.save()
            
            messages.success(request, "Your application has been submitted successfully!")
            return redirect('jobs:detail', pk=pk)
    else:
        form = JobApplicationForm()
    
    context = {
        'form': form,
        'job': job
    }
    
    return render(request, 'jobs/apply_for_job.html', context)


@login_required
def post_job(request):
    """Post a new job (recruiters only)."""
    if not request.user.is_recruiter():
        messages.error(request, "Only recruiters can post jobs.")
        return redirect('jobs:search')
    
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.posted_by = request.user
            job.save()
            form.save()  # Save many-to-many relationships
            
            messages.success(request, "Job posted successfully!")
            return redirect('jobs:detail', pk=job.pk)
    else:
        form = JobForm()
    
    return render(request, 'jobs/post_job.html', {'form': form})


@login_required
def my_jobs(request):
    """View jobs posted by the current user (recruiters) or applied to (job seekers)."""
    if request.user.is_recruiter():
        jobs = Job.objects.filter(posted_by=request.user).order_by('-created_at')
        template = 'jobs/my_posted_jobs.html'
        context = {'jobs': jobs}
    else:
        applications = JobApplication.objects.filter(
            applicant=request.user
        ).select_related('job', 'job__posted_by').order_by('-applied_at')
        template = 'jobs/my_applications.html'
        context = {'applications': applications}
    
    return render(request, template, context)


@login_required
def edit_job(request, pk):
    """Edit a job posting."""
    job = get_object_or_404(Job, pk=pk)
    
    # Check permissions
    if job.posted_by != request.user:
        raise Http404("Job not found")
    
    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, "Job updated successfully!")
            return redirect('jobs:detail', pk=job.pk)
    else:
        form = JobForm(instance=job)
    
    return render(request, 'jobs/edit_job.html', {'form': form, 'job': job})


@login_required
def job_applications(request, pk):
    """View applications for a specific job (recruiters only)."""
    job = get_object_or_404(Job, pk=pk)
    
    # Check permissions
    if job.posted_by != request.user:
        raise Http404("Job not found")
    
    applications = job.applications.select_related(
        'applicant', 'applicant__profile'
    ).order_by('-applied_at')
    
    context = {
        'job': job,
        'applications': applications
    }
    
    return render(request, 'jobs/job_applications.html', context)