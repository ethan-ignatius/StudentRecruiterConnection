from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction
from profiles.models import Skill, JobSeekerProfile
from jobs.models import Job

User = get_user_model()

class Command(BaseCommand):
    help = 'Set up demo data for job board features'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up demo data...'))
        
        with transaction.atomic():
            # Create demo users
            self.create_demo_users()
            
            # Create skills
            self.create_skills()
            
            # Create jobs with skill associations
            self.create_jobs()
            
        self.stdout.write(self.style.SUCCESS('Demo data setup complete!'))
        self.stdout.write(self.style.WARNING('\nDemo Accounts Created:'))
        self.stdout.write('Job Seekers:')
        self.stdout.write('  - demo_seeker / password123 (with profile)')
        self.stdout.write('  - jane_dev / password123 (with profile)')
        self.stdout.write('Recruiters:')
        self.stdout.write('  - recruiter1 / password123')
        self.stdout.write('  - recruiter2 / password123')
        self.stdout.write('  - recruiter3 / password123')
        self.stdout.write('  - recruiter4 / password123')
        self.stdout.write('  - recruiter5 / password123')

    def create_demo_users(self):
        """Create demo users for testing"""
        # Job seekers
        seeker1, created = User.objects.get_or_create(
            username='demo_seeker',
            defaults={
                'email': 'seeker@demo.com',
                'first_name': 'Alex',
                'last_name': 'Johnson',
                'account_type': User.AccountType.JOB_SEEKER
            }
        )
        if created:
            seeker1.set_password('password123')
            seeker1.save()
        
        # Ensure JobSeekerProfile exists
        JobSeekerProfile.objects.get_or_create(
            user=seeker1,
            defaults={
                'headline': 'Full Stack Developer',
                'summary': 'Passionate full stack developer with 3 years of experience building web applications using React and Python.',
                'location': 'San Francisco, CA'
            }
        )

        seeker2, created = User.objects.get_or_create(
            username='jane_dev',
            defaults={
                'email': 'jane@demo.com',
                'first_name': 'Jane',
                'last_name': 'Smith',
                'account_type': User.AccountType.JOB_SEEKER
            }
        )
        if created:
            seeker2.set_password('password123')
            seeker2.save()
        
        JobSeekerProfile.objects.get_or_create(
            user=seeker2,
            defaults={
                'headline': 'UX Designer & Frontend Developer',
                'summary': 'Creative designer with strong technical skills. I bridge the gap between design and development.',
                'location': 'Austin, TX'
            }
        )

        # Recruiters
        recruiters_data = [
            ('recruiter1', 'recruiter1@techflow.com', 'Sarah', 'Wilson'),
            ('recruiter2', 'recruiter2@greentech.com', 'Mike', 'Chen'),
            ('recruiter3', 'recruiter3@designstudio.com', 'Lisa', 'Rodriguez'),
            ('recruiter4', 'recruiter4@airesearch.com', 'David', 'Kumar'),
            ('recruiter5', 'recruiter5@startupventures.com', 'Emma', 'Thompson'),
        ]
        
        for username, email, first_name, last_name in recruiters_data:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'account_type': User.AccountType.RECRUITER
                }
            )
            if created:
                user.set_password('password123')
                user.save()

    def create_skills(self):
        """Create demo skills"""
        skills = [
            'Python', 'JavaScript', 'React', 'TypeScript', 'Django',
            'PostgreSQL', 'AWS', 'Docker', 'Kubernetes', 'Redis',
            'HTML', 'CSS', 'Figma', 'Adobe Creative Suite', 'User Research',
            'Prototyping', 'Machine Learning', 'TensorFlow', 'PyTorch',
            'NumPy', 'Pandas', 'Statistics', 'Product Marketing', 'HubSpot',
            'Marketing Automation', 'Data Analysis', 'Terraform', 'CI/CD',
            'Monitoring', 'Git', 'Flask', 'Node.js', 'Vue.js', 'Angular',
            'MySQL', 'MongoDB', 'GraphQL', 'REST APIs', 'Microservices'
        ]
        
        for skill_name in skills:
            Skill.objects.get_or_create(name=skill_name)
        
        # Add skills to user profiles
        try:
            seeker1 = User.objects.get(username='demo_seeker')
            profile1 = JobSeekerProfile.objects.filter(user=seeker1).first()
            if profile1:
                seeker_skills = ['Python', 'JavaScript', 'React', 'Django', 'PostgreSQL', 'AWS', 'Git']
                for skill_name in seeker_skills:
                    skill = Skill.objects.get(name=skill_name)
                    profile1.skills.add(skill)
            
            seeker2 = User.objects.get(username='jane_dev')
            profile2 = JobSeekerProfile.objects.filter(user=seeker2).first()
            if profile2:
                designer_skills = ['Figma', 'Adobe Creative Suite', 'HTML', 'CSS', 'JavaScript', 'React', 'User Research']
                for skill_name in designer_skills:
                    skill = Skill.objects.get(name=skill_name)
                    profile2.skills.add(skill)
        except User.DoesNotExist:
            pass

    def create_jobs(self):
        """Create demo jobs with skill associations"""
        jobs_data = [
        {
            "title": "Full Stack Engineer",
            "company": "TechFlow",
            "location": "Remote",
            "work_type": "FULL_TIME",
            "description": "Work on scalable SaaS applications in Python/Django and React.",
            "requirements": "3+ years experience with full stack development.",
            "salary_min": 90000,
            "salary_max": 120000,
            "visa_sponsorship": True,
            "benefits": "Health, 401k, Remote stipend",
            "poster_username": "recruiter1",
            "required_skills": ["Python", "Django", "React", "PostgreSQL"],
            "nice_skills": ["AWS", "Docker", "Kubernetes"]
        },
        {
            "title": "UX Designer",
            "company": "DesignStudio",
            "location": "Austin, TX",
            "work_type": "FULL_TIME",
            "description": "Design and prototype engaging user experiences for web and mobile apps.",
            "requirements": "Portfolio of past work, proficiency in Figma and Adobe Suite.",
            "salary_min": 70000,
            "salary_max": 95000,
            "visa_sponsorship": False,
            "benefits": "Flexible hours, Remote-friendly, Health",
            "poster_username": "recruiter3",
            "required_skills": ["Figma", "Adobe Creative Suite", "User Research"],
            "nice_skills": ["React", "CSS"]
        },
        # Add more jobs here...
    ]

        for job_data in jobs_data:
            try:
                poster = User.objects.get(username=job_data['poster_username'])
                
                job, created = Job.objects.get_or_create(
                    title=job_data['title'],
                    company=job_data['company'],
                    defaults={
                        'location': job_data['location'],
                        'work_type': job_data['work_type'],
                        'description': job_data['description'],
                        'requirements': job_data['requirements'],
                        'salary_min': job_data['salary_min'],
                        'salary_max': job_data['salary_max'],
                        'visa_sponsorship': job_data['visa_sponsorship'],
                        'benefits': job_data['benefits'],
                        'posted_by': poster,
                        'status': 'ACTIVE',
                        'expires_at': timezone.now() + timezone.timedelta(days=60)
                    }
                )
                
                if created:
                    # Add required skills
                    for skill_name in job_data['required_skills']:
                        skill, _ = Skill.objects.get_or_create(name=skill_name)
                        job.required_skills.add(skill)
                    
                    # Add nice-to-have skills
                    for skill_name in job_data['nice_skills']:
                        skill, _ = Skill.objects.get_or_create(name=skill_name)
                        job.nice_to_have_skills.add(skill)
                    
                    self.stdout.write(f'Created job: {job.title} at {job.company}')
                else:
                    self.stdout.write(f'Job already exists: {job.title} at {job.company}')
                    
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Recruiter {job_data["poster_username"]} not found')
                )
