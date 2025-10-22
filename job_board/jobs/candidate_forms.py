# job_board/jobs/candidate_forms.py

from django import forms
from .models import SavedCandidateSearch
from profiles.models import Skill


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
                'placeholder': 'City, State',
                'readonly': 'readonly'
            }),
        }
        help_texts = {
            'name': 'Give this search a memorable name',
            'notify_on_new_matches': 'Get notified when new candidates match your criteria'
        }
    
    def __init__(self, *args, **kwargs):
        # Accept initial search params to pre-fill
        search_params = kwargs.pop('search_params', None)
        super().__init__(*args, **kwargs)
        
        if search_params:
            if 'skills' in search_params:
                self.fields['skills'].initial = search_params['skills']
            if 'location' in search_params:
                self.fields['location'].initial = search_params['location']
