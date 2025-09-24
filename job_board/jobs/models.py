from django.conf import settings
from django.db import models
from django.utils import timezone
from django.urls import reverse
from profiles.models import Skill

User = settings.AUTH_USER_MODEL


class Job(models.Model):
    class WorkType(models.TextChoices):
        REMOTE = "REMOTE", "Remote"
        ON_SITE = "ON_SITE", "On-site"
        HYBRID = "HYBRID", "Hybrid"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        CLOSED = "CLOSED", "Closed"
        DRAFT = "DRAFT", "Draft"

    # Basic job information
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True, help_text="City, State or 'Remote'")
    work_type = models.CharField(max_length=20, choices=WorkType.choices, default=WorkType.ON_SITE)
    
    # Job details
    description = models.TextField()
    requirements = models.TextField(blank=True, help_text="Required qualifications and experience")
    
    # Compensation
    salary_min = models.PositiveIntegerField(null=True, blank=True, help_text="Minimum salary (USD)")
    salary_max = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum salary (USD)")
    salary_currency = models.CharField(max_length=3, default="USD")
    
    # Additional benefits/info
    visa_sponsorship = models.BooleanField(default=False, help_text="Visa sponsorship available")
    benefits = models.TextField(blank=True, help_text="Benefits and perks")
    
    # Skills and requirements
    required_skills = models.ManyToManyField(Skill, blank=True, related_name="jobs_required")
    nice_to_have_skills = models.ManyToManyField(Skill, blank=True, related_name="jobs_nice_to_have")
    
    # Meta information
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="posted_jobs")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["work_type"]),
            models.Index(fields=["location"]),
            models.Index(fields=["salary_min", "salary_max"]),
        ]

    def __str__(self):
        return f"{self.title} at {self.company}"

    def get_absolute_url(self):
        return reverse("jobs:detail", kwargs={"pk": self.pk})

    @property
    def is_active(self):
        return (
            self.status == self.Status.ACTIVE and
            (not self.expires_at or self.expires_at > timezone.now())
        )

    @property
    def salary_range_display(self):
        if self.salary_min and self.salary_max:
            return f"${self.salary_min:,} - ${self.salary_max:,}"
        elif self.salary_min:
            return f"${self.salary_min:,}+"
        elif self.salary_max:
            return f"Up to ${self.salary_max:,}"
        return "Salary not specified"


class JobApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        REVIEWING = "REVIEWING", "Under Review"
        INTERVIEWED = "INTERVIEWED", "Interviewed"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="job_applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    cover_letter = models.TextField(blank=True)
    applied_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["job", "applicant"]
        ordering = ["-applied_at"]

    def __str__(self):
        return f"{self.applicant.username} -> {self.job.title}"