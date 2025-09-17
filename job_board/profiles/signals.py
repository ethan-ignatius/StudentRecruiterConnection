from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import JobSeekerProfile

User = settings.AUTH_USER_MODEL

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile_for_job_seeker(sender, instance, created, **kwargs):
    if created and getattr(instance, "is_job_seeker", lambda: False)():
        JobSeekerProfile.objects.get_or_create(user=instance)
