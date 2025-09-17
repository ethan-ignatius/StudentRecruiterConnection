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
