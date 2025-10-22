# job_board/jobs/notification_views.py - NEW FILE

from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, JsonResponse
from django.urls import reverse

from .models import SearchNotification, SavedCandidateSearch


@login_required
def notifications_list(request):
    """View all notifications for the logged-in recruiter"""
    if not request.user.is_recruiter():
        raise Http404("Page not found")
    
    # Get all notifications for this recruiter's saved searches
    notifications = SearchNotification.objects.filter(
        saved_search__recruiter=request.user
    ).select_related('saved_search').prefetch_related('new_candidates').order_by('-sent_at')
    
    # Split into unread and read
    unread = notifications.filter(is_read=False)
    read = notifications.filter(is_read=True)
    
    context = {
        'unread_notifications': unread,
        'read_notifications': read,
        'unread_count': unread.count(),
        'total_count': notifications.count(),
    }
    
    return render(request, 'jobs/notifications_list.html', context)


@login_required
@require_POST
def mark_notification_read(request, pk):
    """Mark a single notification as read"""
    if not request.user.is_recruiter():
        raise Http404("Page not found")
    
    notification = get_object_or_404(
        SearchNotification,
        pk=pk,
        saved_search__recruiter=request.user
    )
    
    notification.mark_as_read()
    
    # Check if this is an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'is_read': True})
    
    messages.success(request, "Notification marked as read.")
    return redirect('jobs:notifications')


@login_required
@require_POST
def mark_all_read(request):
    """Mark all notifications as read for this recruiter"""
    if not request.user.is_recruiter():
        raise Http404("Page not found")
    
    notifications = SearchNotification.objects.filter(
        saved_search__recruiter=request.user,
        is_read=False
    )
    
    count = notifications.count()
    
    for notification in notifications:
        notification.mark_as_read()
    
    messages.success(request, f"Marked {count} notification{'s' if count != 1 else ''} as read.")
    return redirect('jobs:notifications')


@login_required
def notification_detail(request, pk):
    """View notification details and go to search results"""
    if not request.user.is_recruiter():
        raise Http404("Page not found")
    
    notification = get_object_or_404(
        SearchNotification,
        pk=pk,
        saved_search__recruiter=request.user
    )
    
    # Mark as read when viewing
    notification.mark_as_read()
    
    # Redirect to the saved search results
    saved_search = notification.saved_search
    
    # Build query string from saved search params
    params = []
    if saved_search.skills:
        params.append(f'skills={saved_search.skills}')
    if saved_search.location:
        params.append(f'location={saved_search.location}')
    params.append(f'saved_search={saved_search.id}')
    params.append(f'notification={notification.id}')
    
    query_string = '&'.join(params)
    return redirect(f"{reverse('jobs:candidate_search')}?{query_string}")


def get_unread_count(user):
    """Helper function to get unread notification count for a user"""
    if not user.is_authenticated or not user.is_recruiter():
        return 0
    
    return SearchNotification.objects.filter(
        saved_search__recruiter=user,
        is_read=False
    ).count()
