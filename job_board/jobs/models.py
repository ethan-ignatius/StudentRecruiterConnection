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
    latitude  = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
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
    
    def save(self, *args, **kwargs):
        # Normalize location
        loc = (self.location or "").strip()

        # If Remote or blank: clear coords
        if not loc or loc.lower().startswith("remote"):
            self.latitude = None
            self.longitude = None
        else:
            # Decide if we must (re)geocode:
            need = False
            # 1) New object OR coords missing
            if self.pk is None or self.latitude is None or self.longitude is None:
                need = True
            else:
                # 2) Location text changed since last save
                try:
                    old = type(self).objects.get(pk=self.pk)
                except type(self).DoesNotExist:
                    old = None
                if old and (old.location or "").strip() != loc:
                    need = True

            if need:
                try:
                    from .geocoding import geocode_city_state
                    parts = [p.strip() for p in loc.split(",")]
                    if len(parts) >= 2:
                        res = geocode_city_state(parts[0], parts[1])
                        if res:
                            self.latitude, self.longitude = res
                        else:
                            # If lookup fails, clear to avoid stale/wrong pins
                            self.latitude = None
                            self.longitude = None
                except Exception:
                    # Don’t break the save on geocode hiccups
                    pass

        super().save(*args, **kwargs)

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
    
    @property
    def has_coords(self) -> bool:
        return self.latitude is not None and self.longitude is not None


class JobApplication(models.Model):
    class Status(models.TextChoices):
        APPLIED = "APPLIED", "Applied"
        REVIEWING = "REVIEWING", "Under Review"
        INTERVIEW = "INTERVIEW", "Interview"
        OFFER = "OFFER", "Offer Extended"
        ACCEPTED = "ACCEPTED", "Offer Accepted"
        REJECTED = "REJECTED", "Not Selected"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="applications")
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name="job_applications")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.APPLIED)
    cover_letter = models.TextField(blank=True, help_text="Optional personalized message")
    applied_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status tracking fields
    status_notes = models.TextField(blank=True, help_text="Internal notes about status changes")
    last_status_change = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ["job", "applicant"]
        ordering = ["-applied_at"]
        indexes = [
            models.Index(fields=["applicant", "status"]),
            models.Index(fields=["job", "status"]),
            models.Index(fields=["status", "updated_at"]),
        ]

    def __str__(self):
        return f"{self.applicant.username} -> {self.job.title}"
    
    @property
    def status_display_class(self):
        """Return CSS class for status display"""
        status_classes = {
            self.Status.APPLIED: "status-applied",
            self.Status.REVIEWING: "status-reviewing", 
            self.Status.INTERVIEW: "status-interview",
            self.Status.OFFER: "status-offer",
            self.Status.ACCEPTED: "status-accepted",
            self.Status.REJECTED: "status-rejected",
            self.Status.WITHDRAWN: "status-withdrawn",
        }
        return status_classes.get(self.status, "status-default")
    
    def get_status_progress(self):
        """Return progress percentage for status display"""
        progress_map = {
            self.Status.APPLIED: 20,
            self.Status.REVIEWING: 40,
            self.Status.INTERVIEW: 60,
            self.Status.OFFER: 80,
            self.Status.ACCEPTED: 100,
            self.Status.REJECTED: 0,
            self.Status.WITHDRAWN: 0,
        }
        return progress_map.get(self.status, 0)


class ApplicationStatusChange(models.Model):
    """Track status change history for applications"""
    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name="status_changes")
    old_status = models.CharField(max_length=20, choices=JobApplication.Status.choices)
    new_status = models.CharField(max_length=20, choices=JobApplication.Status.choices)
    changed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="status_changes_made")
    changed_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ["-changed_at"]
    
    def __str__(self):
        return f"{self.application} - {self.old_status} to {self.new_status}"

class CityCoord(models.Model):
    city  = models.CharField(max_length=120)
    state = models.CharField(max_length=120)
    lat   = models.FloatField()
    lng   = models.FloatField()

    class Meta:
        unique_together = ("city", "state")
