# job_board/jobs/candidate_views.py

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count
from django.http import Http404
from django.urls import reverse

from accounts.models import User
from profiles.models import JobSeekerProfile, Skill
from .models import SavedCandidateSearch, SearchNotification
from .candidate_forms import CandidateSearchForm, SaveCandidateSearchForm
from django.utils import timezone 


@login_required
def candidate_search(request):
    """Search for job seeker candidates (Story #11)"""
    if not request.user.is_recruiter():
        raise Http404("Page not found")
    
    form = CandidateSearchForm(request.GET)
    
    # Start with all job seekers who have profiles
    candidates_qs = JobSeekerProfile.objects.select_related('user').prefetch_related('skills')
    
    search_params = {}  # Track what was searched for saving later
    
    if form.is_valid():
        q = form.cleaned_data.get('q')
        if q:
            search_params['q'] = q
            candidates_qs = candidates_qs.filter(
                Q(user__first_name__icontains=q) |
                Q(user__last_name__icontains=q) |
                Q(user__username__icontains=q) |
                Q(headline__icontains=q) |
                Q(summary__icontains=q)
            )
        
        location = form.cleaned_data.get('location')
        if location:
            search_params['location'] = location
            candidates_qs = candidates_qs.filter(location__icontains=location)
        
        skills = form.cleaned_data.get('skills')
        if skills:
            search_params['skills'] = ', '.join(skills)
            # Filter candidates who have ANY of the specified skills
            for skill_name in skills:
                candidates_qs = candidates_qs.filter(
                    skills__name__iexact=skill_name
                ).distinct()
    
    candidates_qs = candidates_qs.order_by('-updated_at')
    
    # Pagination
    paginator = Paginator(candidates_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Check if this is a saved search being run
    saved_search_id = request.GET.get('saved_search')
    current_saved_search = None
    if saved_search_id:
        try:
            current_saved_search = SavedCandidateSearch.objects.get(
                id=saved_search_id,
                recruiter=request.user
            )
            current_saved_search.last_run = timezone.now()
            current_saved_search.save(update_fields=['last_run'])
        except SavedCandidateSearch.DoesNotExist:
            pass
    
    context = {
        'form': form,
        'candidates': page_obj,
        'total_count': paginator.count,
        'has_filters': any(v for k, v in request.GET.items() if k not in ('page',) and v),
        'search_params': search_params,
        'current_saved_search': current_saved_search,
    }
    return render(request, 'jobs/candidate_search.html', context)


@login_required
@require_POST
def save_candidate_search(request):
    """Save current search criteria (Story #15)"""
    if not request.user.is_recruiter():
        raise Http404("Page not found")
    
    # Get search parameters from POST
    search_params = {
        'skills': request.POST.get('skills', ''),
        'location': request.POST.get('location', ''),
    }
    
    form = SaveCandidateSearchForm(request.POST, search_params=search_params)
    
    if form.is_valid():
        saved_search = form.save(commit=False)
        saved_search.recruiter = request.user
        saved_search.save()
        
        messages.success(
            request,
            f'Search "{saved_search.name}" saved successfully! '
            f'{"You\'ll be notified of new matches." if saved_search.notify_on_new_matches else ""}'
        )
        return redirect('jobs:saved_searches')
    else:
        messages.error(request, 'Please provide a name for your search.')
        return redirect('jobs:candidate_search')


@login_required
def saved_searches(request):
    """View all saved candidate searches (Story #15)"""
    if not request.user.is_recruiter():
        raise Http404("Page not found")
    
    searches = SavedCandidateSearch.objects.filter(
        recruiter=request.user
    ).annotate(
        notification_count=Count('notifications')
    ).order_by('-created_at')
    
    context = {
        'searches': searches,
    }
    return render(request, 'jobs/saved_searches.html', context)


@login_required
@require_POST
def run_saved_search(request, pk):
    """Run a saved search (Story #15)"""
    if not request.user.is_recruiter():
        raise Http404("Page not found")
    
    saved_search = get_object_or_404(
        SavedCandidateSearch,
        pk=pk,
        recruiter=request.user
    )
    
    # Build query string from saved search params
    params = []
    if saved_search.skills:
        params.append(f'skills={saved_search.skills}')
    if saved_search.location:
        params.append(f'location={saved_search.location}')
    params.append(f'saved_search={saved_search.id}')
    
    query_string = '&'.join(params)
    return redirect(f"{reverse('jobs:candidate_search')}?{query_string}")


@login_required
@require_POST
def delete_saved_search(request, pk):
    """Delete a saved search (Story #15)"""
    if not request.user.is_recruiter():
        raise Http404("Page not found")
    
    saved_search = get_object_or_404(
        SavedCandidateSearch,
        pk=pk,
        recruiter=request.user
    )
    
    search_name = saved_search.name
    saved_search.delete()
    
    messages.success(request, f'Search "{search_name}" deleted.')
    return redirect('jobs:saved_searches')


@login_required
@require_POST
def toggle_search_notifications(request, pk):
    """Toggle notifications for a saved search (Story #15)"""
    if not request.user.is_recruiter():
        raise Http404("Page not found")
    
    saved_search = get_object_or_404(
        SavedCandidateSearch,
        pk=pk,
        recruiter=request.user
    )
    
    saved_search.notify_on_new_matches = not saved_search.notify_on_new_matches
    saved_search.save(update_fields=['notify_on_new_matches'])
    
    if saved_search.notify_on_new_matches:
        messages.success(request, f'Notifications enabled for "{saved_search.name}"')
    else:
        messages.success(request, f'Notifications disabled for "{saved_search.name}"')
    
    return redirect('jobs:saved_searches')
