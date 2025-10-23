# job_board/jobs/candidate_forms.py

from django import forms
from .models import SavedCandidateSearch
from profiles.models import Skill
from django import forms

class CandidateSearchForm(forms.Form):
    """Form for searching candidates"""
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by name, headline, or summary...',
            'class': 'search-input'
        }),
        label="Search"
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
    
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'City, State',
            'class': 'location-input'
        }),
        label="Location"
    )
    
    def clean_skills(self):
        skills_text = self.cleaned_data.get('skills', '').strip()
        if not skills_text:
            return []
        
        # Parse comma-separated skills
        skill_names = [s.strip() for s in skills_text.split(',') if s.strip()]
        return skill_names

class SaveCandidateSearchForm(forms.ModelForm):
    """Form for saving a candidate search"""

    class Meta:
        model = SavedCandidateSearch
        fields = ['name', 'skills', 'location', 'notify_on_new_matches']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'e.g., Senior Python Developers in NYC',
                'class': 'search-name-input'
            }),
            'skills': forms.TextInput(attrs={
                'placeholder': 'Python, Django, React...',
                'readonly': 'readonly'
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'City, State or Remote',
                'readonly': 'readonly'
            }),
            # This gets overridden in __init__ to a Select, but leaving here is harmless.
            'notify_on_new_matches': forms.Select()
        }
        help_texts = {
            'name': 'Give this search a memorable name',
            'notify_on_new_matches': 'Get notified when new candidates match your criteria'
        }

    def __init__(self, *args, **kwargs):
        # Accept initial search params to pre-fill and to read in clean()
        self._search_params = kwargs.pop('search_params', {}) or {}
        super().__init__(*args, **kwargs)

        # Turn the boolean into a Yes/No dropdown
        # We use a ChoiceField so the rendered widget is a <select>.
        self.fields['notify_on_new_matches'] = forms.ChoiceField(
            choices=((True, 'Yes'), (False, 'No')),
            widget=forms.Select(),
            label='Send notifications for new matches?',
            initial=True
        )

        # Pre-fill the read-only fields so the user sees what will be saved
        if 'skills' in self._search_params:
            self.fields['skills'].initial = self._search_params.get('skills', '')
        if 'location' in self._search_params:
            self.fields['location'].initial = self._search_params.get('location', '')

    def clean(self):
        cleaned = super().clean()

        # Cast Yes/No (which come back as strings) to boolean for the model field
        notif = cleaned.get('notify_on_new_matches')
        if isinstance(notif, str):
            if notif in ('True', 'true', '1', 'Yes', 'yes'):
                cleaned['notify_on_new_matches'] = True
            else:
                cleaned['notify_on_new_matches'] = False
        return cleaned