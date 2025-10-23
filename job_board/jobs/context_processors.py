# job_board/jobs/context_processors.py - NEW FILE

from .models import SearchNotification


def notification_count(request):
    """
    Add unread notification count to all template contexts.
    This makes {{ unread_notifications_count }} available in every template.
    """
    if not request.user.is_authenticated:
        return {'unread_notifications_count': 0}
    
    if not hasattr(request.user, 'is_recruiter') or not request.user.is_recruiter():
        return {'unread_notifications_count': 0}
    
    count = SearchNotification.objects.filter(
        saved_search__recruiter=request.user,
        is_read=False
    ).count()
    
    return {'unread_notifications_count': count}
