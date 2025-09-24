from django.contrib import admin
from .models import Job, JobApplication


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'company', 'location', 'work_type', 
        'posted_by', 'status', 'created_at'
    ]
    list_filter = [
        'status', 'work_type', 'visa_sponsorship', 
        'created_at', 'posted_by__account_type'
    ]
    search_fields = ['title', 'company', 'location', 'description']
    filter_horizontal = ['required_skills', 'nice_to_have_skills']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'company', 'location', 'work_type', 'status')
        }),
        ('Job Details', {
            'fields': ('description', 'requirements', 'benefits')
        }),
        ('Compensation', {
            'fields': ('salary_min', 'salary_max', 'salary_currency', 'visa_sponsorship')
        }),
        ('Skills', {
            'fields': ('required_skills', 'nice_to_have_skills')
        }),
        ('Meta', {
            'fields': ('posted_by', 'expires_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'applicant', 'job', 'status', 'applied_at'
    ]
    list_filter = ['status', 'applied_at', 'job__company']
    search_fields = [
        'applicant__username', 'applicant__email',
        'job__title', 'job__company'
    ]
    readonly_fields = ['applied_at', 'updated_at']
    
    fieldsets = (
        ('Application Details', {
            'fields': ('job', 'applicant', 'status')
        }),
        ('Cover Letter', {
            'fields': ('cover_letter',)
        }),
        ('Timestamps', {
            'fields': ('applied_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )