# job_board/jobs/notifications.py
from __future__ import annotations

from typing import List, Iterable, TYPE_CHECKING
from django.db import transaction
from django.utils import timezone
from django.db.models import QuerySet
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

from .models import SavedCandidateSearch, SearchNotification

if TYPE_CHECKING:  # only for type checkers; won't import at runtime
    from django.contrib.auth.models import User
    from profiles.models import JobSeekerProfile


# ---------- helpers ----------

def _split_csv(text: str) -> List[str]:
    """
    Split a comma-separated string of tokens into a clean list.
    Empty tokens are dropped. Whitespace is stripped.
    """
    if not text:
        return []
    return [t.strip() for t in text.split(",") if t.strip()]


def _profile_location_text(profile) -> str:
    """
    Best-effort textual location from the profile for substring matching.
    (Avoids hard dependency on a specific field name.)
    """
    for attr in ("location", "city", "region", "state", "country"):
        val = getattr(profile, attr, None)
        if val:
            return str(val)
    return ""


# ---------- matching logic (keeps your "Name:" sentinel) ----------

def candidate_matches_saved_search(profile, saved_search: SavedCandidateSearch) -> bool:
    """
    Return True if `profile` matches `saved_search`.
    Rules (unchanged from your current behavior):
      - If skills starts with "Name: ", treat the remainder as a free-text query
        searched across first/last name, username, headline, summary.
      - Else, treat skills as CSV of required skill names (ALL must be present).
      - If a location is set on the search, require it to be a substring of the
        profile's location text.
    """
    skills_text = (saved_search.skills or "").strip()
    location_text = (saved_search.location or "").strip()

    # Free-text name/keyword search via the "Name:" sentinel
    if skills_text.lower().startswith("name:"):
        q_val = skills_text.split(":", 1)[1].strip().lower()
        if not q_val:
            return False
        haystacks = [
            (getattr(profile.user, "first_name", "") or "").lower(),
            (getattr(profile.user, "last_name", "") or "").lower(),
            (getattr(profile.user, "username", "") or "").lower(),
            (getattr(profile, "headline", "") or "").lower(),
            (getattr(profile, "summary", "") or "").lower(),
        ]
        if not any(q_val in h for h in haystacks):
            return False
    else:
        # Required skills: ALL must be present on the profile
        if skills_text:
            try:
                profile_skill_names = {
                    (s or "").lower() for s in profile.skills.values_list("name", flat=True)
                }
            except Exception:
                # In case profile.skills relation differs in test envs, fall back defensively
                profile_skill_names = set()
            for required in _split_csv(skills_text):
                if required.lower() not in profile_skill_names:
                    return False

    # Location substring match (if provided)
    if location_text:
        profile_loc = _profile_location_text(profile).lower()
        if location_text.lower() not in profile_loc:
            return False

    return True


# ---------- notification aggregation ----------

def _remove_stale_memberships(user, still_matching_saved_search_ids: set[int]) -> None:
    """
    If a user was included in notifications for searches they no longer match,
    remove them from those notifications; delete empty notifications.
    """
    stale_qs: QuerySet[SearchNotification] = (
        SearchNotification.objects
        .filter(new_candidates=user)
        .exclude(saved_search_id__in=still_matching_saved_search_ids)
    )

    for n in stale_qs:
        n.new_candidates.remove(user)
        remaining = n.new_candidates.count()
        if remaining == 0:
            n.delete()
        else:
            # ensure counter is correct
            n.candidates_count = remaining
            n.save(update_fields=["candidates_count"])


def notify_saved_searches_for_profile(profile) -> int:
    """
    Upsert notifications for the given job-seeker profile.

    Guarantee (new): **At most ONE SearchNotification row per SavedCandidateSearch.**
    - All matching candidates are aggregated into that single row ("bucket").
    - If the only existing row was previously read, new matches re-open it.
    - Any stray duplicate rows (from history) are merged into the bucket and deleted.

    Returns the number of saved-search buckets that were created or updated for this profile.
    """
    user = profile.user

    # Compute which saved searches currently match this profile
    active_saved_searches: List[SavedCandidateSearch] = list(
        SavedCandidateSearch.objects.filter(notify_on_new_matches=True)
    )
    matched: List[SavedCandidateSearch] = [
        ss for ss in active_saved_searches if candidate_matches_saved_search(profile, ss)
    ]
    matched_ids = {ss.id for ss in matched}

    # Remove stale memberships from notifications where this profile no longer matches
    _remove_stale_memberships(user, matched_ids)

    updated = 0

    # Upsert into a single bucket per saved search
    for ss in matched:
        with transaction.atomic():
            # Lock the newest row for this saved search, if any
            bucket: SearchNotification | None = (
                SearchNotification.objects
                .filter(saved_search=ss)
                .order_by("-sent_at")
                .select_for_update()
                .first()
            )

            if bucket is None:
                bucket = SearchNotification.objects.create(
                    saved_search=ss,
                    sent_at=timezone.now(),
                )

            # Merge any duplicate rows for this saved search into the bucket
            dupes = (
                SearchNotification.objects
                .filter(saved_search=ss)
                .exclude(pk=bucket.pk)
            )
            if dupes.exists():
                # Bring all candidate links over
                dup_candidate_ids = (
                    dupes.values_list("new_candidates__id", flat=True).distinct()
                )
                for uid in dup_candidate_ids:
                    if uid and not bucket.new_candidates.filter(pk=uid).exists():
                        bucket.new_candidates.add(uid)
                # Remove the duplicates
                dupes.delete()

            # Re-open if previously marked read
            if getattr(bucket, "is_read", False):
                bucket.is_read = False
                if hasattr(bucket, "read_at"):
                    bucket.read_at = None

            # Add this user if not yet present
            if not bucket.new_candidates.filter(pk=user.pk).exists():
                bucket.new_candidates.add(user)

            # Update counters and bump timestamp so newest floats to the top
            bucket.candidates_count = bucket.new_candidates.count()
            bucket.sent_at = timezone.now()
            save_fields = ["candidates_count", "sent_at"]
            if hasattr(bucket, "is_read"):
                save_fields.append("is_read")
            if hasattr(bucket, "read_at"):
                save_fields.append("read_at")
            bucket.save(update_fields=save_fields)

            updated += 1

    return updated


def notify_admins_of_report(job_report):
    """Send email notification to admin users when a job is reported"""
    try:
        User = get_user_model()
        
        # Get all admin users
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        admin_emails = [user.email for user in admin_users if user.email]
        
        if not admin_emails:
            return False
            
        subject = f"Job Report: {job_report.job.title} at {job_report.job.company}"
        
        message = f"""
A job posting has been reported by a user and requires review.

Job Details:
- Title: {job_report.job.title}
- Company: {job_report.job.company}
- Posted by: {job_report.job.posted_by.username}

Report Details:
- Reported by: {job_report.reported_by.username}
- Reason: {job_report.get_reason_display()}
- Description: {job_report.description}
- Date: {job_report.created_at.strftime('%B %d, %Y at %I:%M %p')}

Please review this report in the admin panel.

Moderation Dashboard: /jobs/admin/moderation-dashboard/
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            fail_silently=True,
        )
        return True
        
    except Exception as e:
        # Log the error but don't fail the report submission
        print(f"Failed to send admin notification email: {e}")
        return False
