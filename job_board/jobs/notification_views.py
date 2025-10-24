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
    if not request.user.is_recruiter():
        raise Http404("Page not found")

    # SHOW UNREAD ONLY
    unread = (
        SearchNotification.objects
        .filter(saved_search__recruiter=request.user, is_read=False)
        .select_related("saved_search").prefetch_related("new_candidates")
        .order_by("-sent_at")
    )

    context = {
        "unread_notifications": unread,
        "read_notifications": None,           # template no-op now
        "unread_count": unread.count(),
    }
    return render(request, "jobs/notifications_list.html", context)


@login_required
def notification_detail(request, pk):
    if not request.user.is_recruiter():
        raise Http404("Page not found")

    n = get_object_or_404(
        SearchNotification, pk=pk, saved_search__recruiter=request.user
    )

    # When opened, clear it from the list (delete instead of keeping as "read")
    saved_search = n.saved_search
    n.delete()

    # Redirect to the search with the saved criteria
    params = []
    skills_text = (saved_search.skills or "").strip()
    if skills_text:
        params.append(f"skills={skills_text}")
    if saved_search.location:
        params.append(f"location={saved_search.location}")
    return redirect(f"{reverse('jobs:candidate_search')}?{'&'.join(params)}")


@login_required
@require_POST
def mark_notification_read(request, pk):
    if not request.user.is_recruiter():
        raise Http404("Page not found")

    n = get_object_or_404(
        SearchNotification, pk=pk, saved_search__recruiter=request.user
    )
    n.delete()
    messages.success(request, "Notification cleared.")
    return redirect("jobs:notifications")


@login_required
@require_POST
def mark_all_read(request):
    if not request.user.is_recruiter():
        raise Http404("Page not found")

    qs = SearchNotification.objects.filter(saved_search__recruiter=request.user)
    count = qs.count()
    qs.delete()
    messages.success(request, f"Cleared {count} notification{'s' if count != 1 else ''}.")
    return redirect("jobs:notifications")
