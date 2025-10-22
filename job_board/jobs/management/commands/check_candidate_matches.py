# job_board/jobs/management/commands/check_candidate_matches.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta

from jobs.models import SavedCandidateSearch, SearchNotification
from profiles.models import JobSeekerProfile


class Command(BaseCommand):
    help = 'Check saved candidate searches for new matches and send notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Check for candidates created/updated in the last N hours (default: 24)'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        self.stdout.write(self.style.SUCCESS(
            f'Checking for candidate matches created/updated since {cutoff_time}'
        ))
        
        # Get all saved searches with notifications enabled
        searches = SavedCandidateSearch.objects.filter(
            notify_on_new_matches=True
        ).select_related('recruiter')
        
        total_notifications = 0
        
        for search in searches:
            # Build query for candidates matching this search
            candidates_qs = JobSeekerProfile.objects.filter(
                # Only candidates updated since cutoff
                updated_at__gte=cutoff_time
            )
            
            # Apply search filters
            if search.skills:
                skill_names = search.get_skill_list()
                for skill_name in skill_names:
                    candidates_qs = candidates_qs.filter(
                        skills__name__iexact=skill_name
                    )
            
            if search.location:
                candidates_qs = candidates_qs.filter(
                    location__icontains=search.location
                )
            
            candidates = candidates_qs.distinct()
            candidate_count = candidates.count()
            
            if candidate_count > 0:
                # Create notification record
                notification = SearchNotification.objects.create(
                    saved_search=search,
                    candidates_count=candidate_count
                )
                notification.new_candidates.set([c.user for c in candidates])
                
                # Update last_notified timestamp
                search.last_notified = timezone.now()
                search.save(update_fields=['last_notified'])
                
                total_notifications += 1
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Notified {search.recruiter.username} about {candidate_count} '
                        f'new match{"es" if candidate_count != 1 else ""} for "{search.name}"'
                    )
                )
                
                # In a real implementation, you would send an email here:
                # send_notification_email(search, candidates)
            else:
                self.stdout.write(
                    f'  No new matches for "{search.name}" ({search.recruiter.username})'
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nComplete! Sent {total_notifications} notification(s) total.'
            )
        )
        
        # Show how to set up cron/scheduled task
        if total_notifications > 0:
            self.stdout.write('\n' + self.style.WARNING(
                'To run this automatically, set up a cron job or scheduled task:\n'
                '  0 * * * * cd /path/to/project && python manage.py check_candidate_matches --hours=1\n'
                '  (This runs every hour and checks for candidates from the last hour)'
            ))


def send_notification_email(saved_search, candidates):
    """
    Send email notification to recruiter about new matches.
    
    In a production environment, you would implement this using Django's
    email functionality or a service like SendGrid, Mailgun, etc.
    
    Example implementation:
    
    from django.core.mail import send_mail
    from django.template.loader import render_to_string
    
    subject = f'New candidates match your search: {saved_search.name}'
    
    context = {
        'search': saved_search,
        'candidates': candidates,
        'count': candidates.count(),
    }
    
    html_message = render_to_string('emails/candidate_match_notification.html', context)
    plain_message = render_to_string('emails/candidate_match_notification.txt', context)
    
    send_mail(
        subject=subject,
        message=plain_message,
        html_message=html_message,
        from_email='noreply@yourjobboard.com',
        recipient_list=[saved_search.recruiter.email],
        fail_silently=False,
    )
    """
    pass
