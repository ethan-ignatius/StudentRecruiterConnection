from django.contrib import admin
from .models import JobSeekerProfile, Skill, Education, Experience, Link

class EducationInline(admin.TabularInline):
    model = Education
    extra = 0

class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0

class LinkInline(admin.TabularInline):
    model = Link
    extra = 0

@admin.register(JobSeekerProfile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "headline", "location", "updated_at")
    inlines = [EducationInline, ExperienceInline, LinkInline]
    filter_horizontal = ("skills",)

admin.site.register(Skill)
