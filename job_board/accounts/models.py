from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class AccountType(models.TextChoices):
        JOB_SEEKER = "JOB_SEEKER", "Job Seeker"
        RECRUITER = "RECRUITER", "Recruiter"

    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.JOB_SEEKER,
        help_text="Controls which features the account can access.",
    )

    def is_job_seeker(self) -> bool:
        return self.account_type == self.AccountType.JOB_SEEKER

    def is_recruiter(self) -> bool:
        return self.account_type == self.AccountType.RECRUITER

class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"From {self.sender.username} to {self.recipient.username}: {self.content[:30]}"
