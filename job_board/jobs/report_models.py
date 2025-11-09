from django.db import models
from django.conf import settings
from .models import Job

User = settings.AUTH_USER_MODEL


class JobReport(models.Model):
    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('fake', 'Fake Job Posting'),
        ('discriminatory', 'Discriminatory'),
        ('other', 'Other'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(help_text="Please describe the issue")
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_reports')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ['job', 'reported_by']  # One report per user per job
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report for {self.job.title} by {self.reported_by.username}"
