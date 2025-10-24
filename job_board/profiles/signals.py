from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.conf import settings
from .models import JobSeekerProfile

# NEW: import the notification helper
from jobs.notifications import notify_saved_searches_for_profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_job_seeker(sender, instance, created, **kwargs):
    if created and getattr(instance, "is_job_seeker", lambda: False)():
        JobSeekerProfile.objects.get_or_create(user=instance)


# NEW: whenever a JobSeekerProfile is saved -> re-check notifications
@receiver(post_save, sender=JobSeekerProfile)
def _refresh_notifications_on_profile_save(sender, instance, **kwargs):
    notify_saved_searches_for_profile(instance)


# NEW: whenever skills are modified -> re-check notifications
@receiver(m2m_changed, sender=JobSeekerProfile.skills.through)
def _refresh_notifications_on_skills_change(sender, instance, action, **kwargs):
    if action in ("post_add", "post_remove", "post_clear"):
        notify_saved_searches_for_profile(instance)


# NEW: if the user’s name/username changes, also re-check (affects "Name:" queries)
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def _refresh_notifications_on_user_update(sender, instance, created, **kwargs):
    if not created and hasattr(instance, "profile"):
        notify_saved_searches_for_profile(instance.profile)
