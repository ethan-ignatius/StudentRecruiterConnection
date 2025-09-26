from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction

from accounts.models import User
from profiles.models import Skill
from .models import Job, JobApplication, ApplicationStatusChange
from .forms import JobSearchForm, JobForm, JobApplicationForm, QuickApplicationForm, ApplicationStatusForm


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
    
    context = {
        'form': form,
        'jobs': page_obj,
        'total_count': paginator.count,
        'has_filters': any(request.GET.values())
    }
    
    return render(request, 'jobs/job_search.html', context)


def job_detail(request, pk):
    """Job detail view with quick apply option."""
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
    
    can_apply = (
        request.user.is_authenticated and 
        request.user.is_job_seeker() and 
        not user_applied and
        job.posted_by != request.user
    )
    
    # Initialize quick application form if user can apply
    quick_form = None
    if can_apply:
        quick_form = QuickApplicationForm(user=request.user, job=job)
    
    context = {
        'job': job,
        'user_applied': user_applied,
        'user_application': user_application,
        'can_apply': can_apply,
        'quick_form': quick_form,
    }
    
    return render(request, 'jobs/job_detail.html', context)


@login_required
@require_POST
def quick_apply(request, pk):
    """One-click application with optional tailored note."""
    job = get_object_or_404(Job, pk=pk, status=Job.Status.ACTIVE)
    
    # Check permissions
    if not request.user.is_job_seeker():
        return JsonResponse({
            'success': False, 
            'error': 'Only job seekers can apply for jobs.'
        })
    
    if job.posted_by == request.user:
        return JsonResponse({
            'success': False, 
            'error': 'You cannot apply to your own job posting.'
        })
    
    # Check if already applied
    if JobApplication.objects.filter(job=job, applicant=request.user).exists():
        return JsonResponse({
            'success': False, 
            'error': 'You have already applied for this job.'
        })
    
    form = QuickApplicationForm(request.POST, user=request.user, job=job)
    if form.is_valid():
        # Create application
        application = JobApplication.objects.create(
            job=job,
            applicant=request.user,
            cover_letter=form.cleaned_data.get('tailored_note', ''),
            status=JobApplication.Status.APPLIED
        )
        
        # Log initial status
        ApplicationStatusChange.objects.create(
            application=application,
            old_status='',
            new_status=JobApplication.Status.APPLIED,
            changed_by=request.user,
            notes='Application submitted'
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Application submitted successfully!',
            'redirect_url': f'/jobs/{job.pk}/'
        })
    
    return JsonResponse({
        'success': False,
        'error': 'Please check your input and try again.'
    })


@login_required
def apply_for_job(request, pk):
    """Full application form for detailed applications."""
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
            with transaction.atomic():
                application = form.save(commit=False)
                application.job = job
                application.applicant = request.user
                application.status = JobApplication.Status.APPLIED
                application.save()
                
                # Log initial status
                ApplicationStatusChange.objects.create(
                    application=application,
                    old_status='',
                    new_status=JobApplication.Status.APPLIED,
                    changed_by=request.user,
                    notes='Application submitted with cover letter'
                )
            
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
        
        # Group applications by status for better organization
        status_groups = {}
        for app in applications:
            status = app.get_status_display()
            if status not in status_groups:
                status_groups[status] = []
            status_groups[status].append(app)
        
        template = 'jobs/my_applications.html'
        context = {
            'applications': applications,
            'status_groups': status_groups
        }
    
    return render(request, template, context)


@login_required
def application_detail(request, pk):
    """Detailed view of a specific application with status history."""
    application = get_object_or_404(JobApplication, pk=pk)
    
    # Check permissions - only applicant or job poster can view
    if application.applicant != request.user and application.job.posted_by != request.user:
        raise Http404("Application not found")
    
    # Get status change history
    status_history = application.status_changes.all()
    
    # Status update form for recruiters
    status_form = None
    if request.user == application.job.posted_by and request.method == 'POST':
        status_form = ApplicationStatusForm(request.POST, instance=application)
        if status_form.is_valid():
            old_status = application.status
            new_status = status_form.cleaned_data['status']
            
            if old_status != new_status:
                with transaction.atomic():
                    status_form.save()
                    
                    # Log status change
                    ApplicationStatusChange.objects.create(
                        application=application,
                        old_status=old_status,
                        new_status=new_status,
                        changed_by=request.user,
                        notes=status_form.cleaned_data.get('notes', '')
                    )
                
                messages.success(request, f"Application status updated to {application.get_status_display()}")
                return redirect('jobs:application_detail', pk=pk)
    elif request.user == application.job.posted_by:
        status_form = ApplicationStatusForm(instance=application)
    
    context = {
        'application': application,
        'status_history': status_history,
        'status_form': status_form,
        'is_recruiter': request.user == application.job.posted_by,
        'is_applicant': request.user == application.applicant,
    }
    
    return render(request, 'jobs/application_detail.html', context)


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
    
    # Group applications by status
    status_groups = {}
    for app in applications:
        status = app.get_status_display()
        if status not in status_groups:
            status_groups[status] = []
        status_groups[status].append(app)
    
    context = {
        'job': job,
        'applications': applications,
        'status_groups': status_groups,
        'total_applications': applications.count()
    }
    
    return render(request, 'jobs/job_applications.html', context)