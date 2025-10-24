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
        choices=[("", "Any")] + list(Job.WorkType.choices),
        widget=forms.Select(),
        label="Work Type"
    )

    salary_min = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': '50000', 'min': 0}),
        label="Minimum Salary ($)"
    )

    salary_max = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'placeholder': '150000', 'min': 0}),
        label="Maximum Salary ($)"
    )

    # Keep the Yes/No/Any tri-state behaviour from before
    visa_sponsorship = forms.TypedChoiceField(
        required=False,
        label="Visa sponsorship",
        choices=(("", "Any"), (True, "Yes"), (False, "No")),
        coerce=lambda v: None if v in ("", None)
                         else v in (True, "True", "true", "1", "on", "yes", "y"),
        empty_value=None,
        widget=forms.Select()
    )

    # hidden geolocation from the browser
    lat = forms.FloatField(required=False, widget=forms.HiddenInput())
    lng = forms.FloatField(required=False, widget=forms.HiddenInput())

    # NEW: radius as a number input (no slider/checkboxes)
    radius = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=3000,
        label="Radius (miles)",
        widget=forms.NumberInput(attrs={'placeholder': '10'})
    )

    commute_radius = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=3000,
        label="Commute Distance (miles)",
        widget=forms.NumberInput(attrs={'placeholder': '10'})
    )

    # --- cleaning helpers ---

    def clean_skills(self):
        raw = (self.cleaned_data.get("skills") or "").strip()
        if not raw:
            return []
        return [s.strip() for s in raw.split(",") if s.strip()]

    def clean(self):
        cleaned_data = super().clean()

        salary_min = cleaned_data.get('salary_min')
        salary_max = cleaned_data.get('salary_max')
        if salary_min and salary_max and salary_min > salary_max:
            raise forms.ValidationError(
                "Minimum salary cannot be greater than maximum salary."
            )

        # If the user entered a radius, we need a location to compute distance.
        radius = cleaned_data.get('radius')
        lat = cleaned_data.get('lat')
        lng = cleaned_data.get('lng')
        if radius not in (None, "") and (lat is None or lng is None):
            self.add_error(
                None,
                "Your location is needed to filter by distance. Please allow location access."
            )

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

    # Render visa sponsorship as a Yes/No select rather than a checkbox
    visa_sponsorship = forms.TypedChoiceField(
        required=False,
        label="Visa sponsorship",
        choices=((True, "Yes"), (False, "No")),
        coerce=lambda v: v in (True, "True", "true", "1", "on", "yes", "y"),
        widget=forms.Select()
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

    # A concise US-cities set that matches the <datalist> values (City, ST)
    US_CITIES = {
        "New York, NY","Los Angeles, CA","Chicago, IL","Houston, TX","Phoenix, AZ",
        "Philadelphia, PA","San Antonio, TX","San Diego, CA","Dallas, TX","San Jose, CA",
        "Austin, TX","Jacksonville, FL","San Francisco, CA","Columbus, OH","Fort Worth, TX",
        "Indianapolis, IN","Charlotte, NC","Seattle, WA","Denver, CO","Boston, MA",
        "Detroit, MI","Nashville, TN","Portland, OR","Oklahoma City, OK","Las Vegas, NV",
        "Memphis, TN","Louisville, KY","Baltimore, MD","Milwaukee, WI","Albuquerque, NM",
        "Tucson, AZ","Fresno, CA","Sacramento, CA","Kansas City, MO","Atlanta, GA",
        "Miami, FL","New Orleans, LA","Minneapolis, MN","Saint Paul, MN","Honolulu, HI",
        "Anchorage, AK","Montgomery, AL","Juneau, AK","Little Rock, AR","Denver, CO",
        "Hartford, CT","Dover, DE","Tallahassee, FL","Atlanta, GA","Boise, ID",
        "Springfield, IL","Indianapolis, IN","Des Moines, IA","Topeka, KS","Frankfort, KY",
        "Baton Rouge, LA","Augusta, ME","Annapolis, MD","Boston, MA","Lansing, MI",
        "Saint Paul, MN","Jackson, MS","Jefferson City, MO","Helena, MT","Lincoln, NE",
        "Carson City, NV","Concord, NH","Trenton, NJ","Santa Fe, NM","Albany, NY",
        "Raleigh, NC","Bismarck, ND","Columbus, OH","Oklahoma City, OK","Salem, OR",
        "Harrisburg, PA","Providence, RI","Columbia, SC","Pierre, SD","Nashville, TN",
        "Austin, TX","Salt Lake City, UT","Montpelier, VT","Richmond, VA","Olympia, WA",
        "Charleston, WV","Madison, WI","Cheyenne, WY","Washington, DC",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make Location a required field
        self.fields['location'].required = True
        # Keep your existing required flags
        self.fields['title'].required = True
        self.fields['company'].required = True
        self.fields['description'].required = True

        # Pre-populate skills if editing (unchanged)
        if self.instance and self.instance.pk:
            req_skills = [s.name for s in self.instance.required_skills.all().order_by('name')]
            nice_skills = [s.name for s in self.instance.nice_to_have_skills.all().order_by('name')]
            self.fields['required_skills_csv'].initial = ', '.join(req_skills)
            self.fields['nice_to_have_skills_csv'].initial = ', '.join(nice_skills)

    def clean(self):
        cleaned = super().clean()
        work_type = cleaned.get('work_type')
        loc = (cleaned.get('location') or '').strip()

        if work_type == Job.WorkType.REMOTE:
            # Force the canonical value for remote jobs
            cleaned['location'] = 'Remote'
            return cleaned

        # On-site / Hybrid => must be a US city from our list
        if not loc:
            self.add_error('location', "Location is required for on-site or hybrid roles.")
            return cleaned

        # Normalize spacing/casing; compare to our canonical set
        normalized = ', '.join([part.strip() for part in loc.split(',', 1)]) if ',' in loc else loc
        if normalized not in self.US_CITIES:
            self.add_error(
                'location',
                "Please choose a US city from the list (format: City, ST)."
            )
        return cleaned
    
    # ---------- FIX START ----------
    def clean_required_skills_csv(self):
        """
        Parse the comma-separated string into a list of whole skill names
        (prevents it from being treated as characters later).
        """
        raw = (self.cleaned_data.get('required_skills_csv') or '').strip()
        if not raw:
            return []
        parts = [p.strip() for p in raw.replace('\n', ',').split(',') if p.strip()]
        seen, out = set(), []
        for p in parts:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out

    def clean_nice_to_have_skills_csv(self):
        raw = (self.cleaned_data.get('nice_to_have_skills_csv') or '').strip()
        if not raw:
            return []
        parts = [p.strip() for p in raw.replace('\n', ',').split(',') if p.strip()]
        seen, out = set(), []
        for p in parts:
            if p not in seen:
                seen.add(p)
                out.append(p)
        return out
    # ---------- FIX END ----------


    def save(self, commit=True):
        job = super().save(commit=commit)
        # Your existing skills saving logic (unchanged)…
        if commit and job.pk:
            req_skill_names = self.cleaned_data.get('required_skills_csv', [])
            req_skill_objs = [Skill.objects.get_or_create(name=name)[0] for name in req_skill_names]
            job.required_skills.set(req_skill_objs)

            nice_skill_names = self.cleaned_data.get('nice_to_have_skills_csv', [])
            nice_skill_objs = [Skill.objects.get_or_create(name=name)[0] for name in nice_skill_names]
            job.nice_to_have_skills.set(nice_skill_objs)
        return job

class QuickApplicationForm(forms.Form):
    """Form for one-click application with optional tailored note"""
    tailored_note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Add a personalized note to make your application stand out... (optional)',
            'class': 'quick-note-input',
            'maxlength': 500
        }),
        label="Personal Note",
        help_text="Optional: Briefly explain why you're interested in this role (max 500 characters)",
        max_length=500
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.job = kwargs.pop('job', None)
        super().__init__(*args, **kwargs)
        
        # Pre-populate with suggested content if user has profile
        if self.user and hasattr(self.user, 'profile') and self.job:
            profile = self.user.profile
            if profile.headline or profile.skills.exists():
                suggestion = self.generate_suggestion(profile, self.job)
                self.fields['tailored_note'].widget.attrs['placeholder'] = suggestion
    
    def generate_suggestion(self, profile, job):
        """Generate a suggested note based on user profile and job"""
        suggestions = []
        
        # Match skills
        user_skills = set(skill.name.lower() for skill in profile.skills.all())
        job_skills = set(skill.name.lower() for skill in job.required_skills.all()) | \
                    set(skill.name.lower() for skill in job.nice_to_have_skills.all())
        
        matching_skills = user_skills & job_skills
        if matching_skills:
            skill_list = ', '.join(list(matching_skills)[:3])  # First 3 matches
            suggestions.append(f"I have experience with {skill_list}")
        
        # Add headline if available
        if profile.headline:
            suggestions.append(f"As a {profile.headline.lower()}, I'm excited about this opportunity")
        
        if suggestions:
            return f"Example: {'. '.join(suggestions[:2])}..."
        
        return "Add a personalized note to make your application stand out... (optional)"


class JobApplicationForm(forms.ModelForm):
    """Full application form for detailed applications"""
    class Meta:
        model = JobApplication
        fields = ['cover_letter']
        widgets = {
            'cover_letter': forms.Textarea(attrs={
                'rows': 8,
                'placeholder': 'Write a detailed cover letter explaining why you\'re interested in this position and why you\'d be a great fit...'
            })
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cover_letter'].required = False
        self.fields['cover_letter'].label = "Cover Letter"
        self.fields['cover_letter'].help_text = "Tell the employer about your interest and qualifications"


class ApplicationStatusForm(forms.ModelForm):
    """Form for recruiters to update application status"""
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Add notes about this status change...'
        }),
        label="Notes",
        help_text="Optional notes about the status change"
    )
    
    class Meta:
        model = JobApplication
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'status-select'
            })
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].label = "Application Status"