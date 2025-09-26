from django.conf import settings
from django.db import models
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class JobSeekerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    headline = models.CharField(max_length=120, blank=True)
    summary = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    show_headline = models.BooleanField(default=True)
    show_location = models.BooleanField(default=True)
    show_summary = models.BooleanField(default=True)
    show_skills = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}"

class Skill(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Education(models.Model):
    profile = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name="educations")
    school = models.CharField(max_length=120)
    degree = models.CharField(max_length=120, blank=True)
    field_of_study = models.CharField(max_length=120, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    current = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    show = models.BooleanField(default=True)

    class Meta:
        ordering = ["-current", "-end_date", "-start_date"]

class Experience(models.Model):
    profile = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name="experiences")
    title = models.CharField(max_length=120)
    company = models.CharField(max_length=120)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    current = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    show = models.BooleanField(default=True)

    class Meta:
        ordering = ["-current", "-end_date", "-start_date"]

class Link(models.Model):
    class Kind(models.TextChoices):
        WEBSITE = "WEBSITE", "Website"
        LINKEDIN = "LINKEDIN", "LinkedIn"
        GITHUB = "GITHUB", "GitHub"
        PORTFOLIO = "PORTFOLIO", "Portfolio"
        OTHER = "OTHER", "Other"

    profile = models.ForeignKey(JobSeekerProfile, on_delete=models.CASCADE, related_name="links")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.WEBSITE)
    label = models.CharField(max_length=60, blank=True)
    url = models.URLField()
    show = models.BooleanField(default=True)

JobSeekerProfile.add_to_class("skills", models.ManyToManyField(Skill, blank=True))
