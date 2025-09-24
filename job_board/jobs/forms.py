from django import forms
from django.db.models import Q
from profiles.models import Skill
from .models import Job, JobApplication


class JobSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search job titles, companies, or keywords...',
            'class': 'search-input'
        }),
        label="Search"
    )
    
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'City, State or Remote',
            'class': 'location-input'
        }),
        label="Location"
    )
    
    skills = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Python, React, SQL...',
            'class': 'skills-input'
        }),
        label="Skills",
        help_text="Comma-separated skills"
    )
    
    work_type = forms.ChoiceField(
        required=False,
        choices=[('', 'Any work type')] + Job.WorkType.choices,
        label="Work Type"
    )
    
    salary_min = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': '50000',
            'min': 0
        }),
        label="Minimum Salary ($)"
    )
    
    salary_max = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={
            'placeholder': '150000',
            'min': 0
        }),
        label="Maximum Salary ($)"
    )
    
    visa_sponsorship = forms.BooleanField(
        required=False,
        label="Visa sponsorship available"
    )
    
    def clean_skills(self):
        skills_text = self.cleaned_data.get('skills', '').strip()
        if not skills_text:
            return []
        
        # Parse comma-separated skills
        skill_names = [s.strip() for s in skills_text.split(',') if s.strip()]
        return skill_names
    
    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')
        
        if salary_min and salary_max and salary_min > salary_max:
            raise forms.ValidationError("Minimum salary cannot be greater than maximum salary.")
        
        return cleaned_data


class JobForm(forms.ModelForm):
    required_skills_csv = forms.CharField(
        required=False,
        label="Required Skills",
        help_text="Comma-separated skills, e.g. Python, SQL, React",
        widget=forms.TextInput(attrs={'placeholder': 'Python, SQL, React...'})
    )
    
    nice_to_have_skills_csv = forms.CharField(
        required=False,
        label="Nice-to-Have Skills",
        help_text="Comma-separated skills",
        widget=forms.TextInput(attrs={'placeholder': 'Docker, AWS, GraphQL...'})
    )

    class Meta:
        model = Job
        fields = [
            'title', 'company', 'location', 'work_type', 'description',
            'requirements', 'salary_min', 'salary_max', 'visa_sponsorship',
            'benefits', 'expires_at', 'status'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6}),
            'requirements': forms.Textarea(attrs={'rows': 4}),
            'benefits': forms.Textarea(attrs={'rows': 3}),
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'salary_min': forms.NumberInput(attrs={'min': 0, 'placeholder': '50000'}),
            'salary_max': forms.NumberInput(attrs={'min': 0, 'placeholder': '150000'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make certain fields required
        self.fields['title'].required = True
        self.fields['company'].required = True
        self.fields['description'].required = True
        
        # Pre-populate skills if editing
        if self.instance and self.instance.pk:
            req_skills = [s.name for s in self.instance.required_skills.all().order_by('name')]
            nice_skills = [s.name for s in self.instance.nice_to_have_skills.all().order_by('name')]
            
            self.fields['required_skills_csv'].initial = ', '.join(req_skills)
            self.fields['nice_to_have_skills_csv'].initial = ', '.join(nice_skills)

    def clean_required_skills_csv(self):
        return self._clean_skills_csv('required_skills_csv')
    
    def clean_nice_to_have_skills_csv(self):
        return self._clean_skills_csv('nice_to_have_skills_csv')
    
    def _clean_skills_csv(self, field_name):
        """Parse and deduplicate comma-separated skills."""
        raw = self.cleaned_data.get(field_name, '').strip()
        if not raw:
            return []
        
        seen = set()
        skills = []
        for part in (p.strip() for p in raw.split(',')):
            if not part:
                continue
            key = part.lower()
            if key in seen:
                continue
            seen.add(key)
            skills.append(part)
        
        return skills

    def clean(self):
        cleaned_data = super().clean()
        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')
        
        if salary_min and salary_max and salary_min > salary_max:
            raise forms.ValidationError("Minimum salary cannot be greater than maximum salary.")
        
        return cleaned_data

    def save(self, commit=True):
        job = super().save(commit=commit)
        
        if commit and job.pk:
            # Handle required skills
            req_skill_names = self.cleaned_data.get('required_skills_csv', [])
            req_skill_objs = [Skill.objects.get_or_create(name=name)[0] for name in req_skill_names]
            job.required_skills.set(req_skill_objs)
            
            # Handle nice-to-have skills
            nice_skill_names = self.cleaned_data.get('nice_to_have_skills_csv', [])
            nice_skill_objs = [Skill.objects.get_or_create(name=name)[0] for name in nice_skill_names]
            job.nice_to_have_skills.set(nice_skill_objs)
        
        return job


class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = ['cover_letter']
        widgets = {
            'cover_letter': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Tell the employer why you\'re interested in this position and why you\'d be a great fit...'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cover_letter'].required = False