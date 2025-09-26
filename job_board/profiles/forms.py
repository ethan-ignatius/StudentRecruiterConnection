from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from .models import JobSeekerProfile, Education, Experience, Link, Skill


# ---- Shared date validation + "current" logic ----
class _StartEndDateValidationMixin(forms.ModelForm):
    """
    - Make all fields required except 'current' and 'end_date' (end_date is conditional).
    - When 'current' is checked: end_date is cleared and not required.
    - When 'current' is NOT checked: end_date is required.
    - Keep the original start/end date validations.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"current", "end_date", "id", "DELETE", "show"}:
                continue
            field.required = True
        # ensure the checkbox isn't forced to be checked
        if "current" in self.fields:
            self.fields["current"].required = False

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        current = cleaned.get("current")
        today = timezone.now().date()

        # End date requirement depends on "current"
        if current:
            # not required and stored as None
            self.fields["end_date"].required = False
            cleaned["end_date"] = None
            self.cleaned_data["end_date"] = None
            end = None
        else:
            # must provide an end date
            self.fields["end_date"].required = True
            if not end:
                self.add_error("end_date", "This field is required.")

        # Original validations
        if start:
            if start > today:
                self.add_error("start_date", "Start date cannot be in the future.")
        if start and end and start > end:
            self.add_error("start_date", "Start date cannot be after end date.")
        return cleaned


class EducationForm(_StartEndDateValidationMixin, forms.ModelForm):
    show = forms.BooleanField(required=False)
    class Meta:
        model = Education
        fields = ("school", "degree", "field_of_study", "start_date", "end_date", "current", "description", "show")
        widgets = {
            "start_date": forms.DateInput(format="%Y-%m-%d", attrs={"class": "js-date", "placeholder": "YYYY-MM-DD"}),
            "end_date": forms.DateInput(format="%Y-%m-%d", attrs={"class": "js-date", "placeholder": "YYYY-MM-DD"}),
        }


class ExperienceForm(_StartEndDateValidationMixin, forms.ModelForm):
    show = forms.BooleanField(required=False)
    class Meta:
        model = Experience
        fields = ("title", "company", "start_date", "end_date", "current", "description", "show")
        widgets = {
            "start_date": forms.DateInput(format="%Y-%m-%d", attrs={"class": "js-date", "placeholder": "YYYY-MM-DD"}),
            "end_date": forms.DateInput(format="%Y-%m-%d", attrs={"class": "js-date", "placeholder": "YYYY-MM-DD"}),
        }


class ProfileForm(forms.ModelForm):
    skills_csv = forms.CharField(
        required=False,
        label="Skills",
        help_text="Comma-separated skills, e.g. Python, SQL, React",
    )

    class Meta:
        model = JobSeekerProfile
        fields = ("headline", "summary", "location", "show_headline", "show_summary", "show_location", "show_skills")

        widgets = {
            "show_headline": forms.CheckboxInput(),
            "show_summary": forms.CheckboxInput(),
            "show_location": forms.CheckboxInput(),
            "show_skills": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        inst = getattr(self, "instance", None)
        if inst and inst.pk:
            names = [s.name for s in inst.skills.all().order_by("name")]
            self.fields["skills_csv"].initial = ", ".join(names)

    def clean_skills_csv(self):
        raw = (self.cleaned_data.get("skills_csv") or "").strip()
        if not raw:
            return []
        seen, out = set(), []
        for part in (p.strip() for p in raw.split(",")):
            if not part:
                continue
            key = part.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(part)
        return out

    def save(self, commit=True):
        profile = super().save(commit=commit)
        names = self.cleaned_data.get("skills_csv", [])
        skill_objs = [Skill.objects.get_or_create(name=n)[0] for n in names]
        if commit and profile.pk:
            profile.skills.set(skill_objs)
        else:
            self._pending_skills = skill_objs
        return profile


class LinkForm(forms.ModelForm):
    """All link fields required."""
    show = forms.BooleanField(required=False)
    class Meta:
        model = Link
        fields = ("kind", "label", "url", "show")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"id", "DELETE", "show"}:
                continue
            field.required = True


EducationFormSet = inlineformset_factory(
    JobSeekerProfile, Education,
    form=EducationForm,
    fields=("school", "degree", "field_of_study", "start_date", "end_date", "current", "description", "show"),
    extra=0, can_delete=True
)

ExperienceFormSet = inlineformset_factory(
    JobSeekerProfile, Experience,
    form=ExperienceForm,
    fields=("title", "company", "start_date", "end_date", "current", "description", "show"),
    extra=0, can_delete=True
)

LinkFormSet = inlineformset_factory(
    JobSeekerProfile, Link,
    form=LinkForm, 
    fields=("kind", "label", "url", "show"),
    extra=0, can_delete=True
)
