from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from django.contrib.admin import SimpleListFilter
from django.utils.safestring import mark_safe
from .models import Job, JobApplication, JobReport


class ModerationStatusFilter(SimpleListFilter):
    title = 'job status'
    parameter_name = 'mod_status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active'),
            ('closed', 'Closed'),
            ('removed', 'Removed by Admin'),
            ('draft', 'Draft'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'active':
            return queryset.filter(status='ACTIVE')
        if self.value() == 'closed':
            return queryset.filter(status='CLOSED')
        if self.value() == 'removed':
            return queryset.filter(status='REMOVED')
        if self.value() == 'draft':
            return queryset.filter(status='DRAFT')


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'company', 'location', 'work_type', 
        'posted_by', 'colored_status', 'moderated_by', 'created_at'
    ]
    list_filter = [
        ModerationStatusFilter, 'work_type', 'visa_sponsorship', 
        'created_at', 'posted_by__account_type', 'moderated_by'
    ]
    search_fields = ['title', 'company', 'location', 'description', 'posted_by__username']
    filter_horizontal = ['required_skills', 'nice_to_have_skills']
    readonly_fields = ['created_at', 'updated_at', 'moderated_at']
    actions = ['remove_jobs', 'restore_jobs', 'close_jobs']
    
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
        ('Moderation', {
            'fields': ('moderated_by', 'moderated_at', 'moderation_notes'),
            'classes': ('collapse',)
        }),
        ('Meta', {
            'fields': ('posted_by', 'expires_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )

    def colored_status(self, obj):
        colors = {
            'ACTIVE': '#10b981',   # green
            'REMOVED': '#ef4444',  # red
            'CLOSED': '#3b82f6',   # blue
            'DRAFT': '#8b5cf6',    # purple
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    colored_status.short_description = 'Status'

    def remove_jobs(self, request, queryset):
        updated = 0
        for job in queryset:
            if job.status != 'REMOVED':
                job.status = 'REMOVED'
                job.moderated_by = request.user
                job.moderated_at = timezone.now()
                job.moderation_notes = f"Removed by {request.user.username} for policy violation"
                job.save()
                updated += 1
        
        self.message_user(request, f"{updated} job(s) removed successfully.")
    remove_jobs.short_description = "Remove selected jobs (spam/abuse)"

    def restore_jobs(self, request, queryset):
        updated = 0
        for job in queryset:
            if job.status == 'REMOVED':
                job.status = 'ACTIVE'
                job.moderated_by = request.user
                job.moderated_at = timezone.now()
                job.moderation_notes = f"Restored by {request.user.username}"
                job.save()
                updated += 1
        
        self.message_user(request, f"{updated} job(s) restored successfully.")
    restore_jobs.short_description = "Restore removed jobs"

    def close_jobs(self, request, queryset):
        updated = 0
        for job in queryset:
            if job.status == 'ACTIVE':
                job.status = 'CLOSED'
                job.moderated_by = request.user
                job.moderated_at = timezone.now()
                job.moderation_notes = f"Closed by {request.user.username}"
                job.save()
                updated += 1
        
        self.message_user(request, f"{updated} job(s) closed successfully.")
    close_jobs.short_description = "Close selected jobs"


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


@admin.register(JobReport)
class JobReportAdmin(admin.ModelAdmin):
    list_display = [
        'job', 'reported_by', 'reason', 'reviewed', 
        'reviewed_by', 'created_at'
    ]
    list_filter = ['reason', 'reviewed', 'created_at']
    search_fields = ['job__title', 'job__company', 'reported_by__username', 'description']
    readonly_fields = ['created_at']
    actions = ['mark_reviewed', 'mark_unreviewed']
    
    fieldsets = (
        ('Report Details', {
            'fields': ('job', 'reported_by', 'reason', 'description', 'created_at')
        }),
        ('Review Status', {
            'fields': ('reviewed', 'reviewed_by', 'reviewed_at'),
            'classes': ('collapse',)
        })
    )

    def mark_reviewed(self, request, queryset):
        updated = 0
        for report in queryset:
            if not report.reviewed:
                report.reviewed = True
                report.reviewed_by = request.user
                report.reviewed_at = timezone.now()
                report.save()
                updated += 1
        
        self.message_user(request, f"{updated} report(s) marked as reviewed.")
    mark_reviewed.short_description = "Mark selected reports as reviewed"

    def mark_unreviewed(self, request, queryset):
        updated = queryset.filter(reviewed=True).update(
            reviewed=False, 
            reviewed_by=None, 
            reviewed_at=None
        )
        self.message_user(request, f"{updated} report(s) marked as unreviewed.")
    mark_unreviewed.short_description = "Mark selected reports as unreviewed"


# Custom admin site configuration
class JobBoardAdminSite(admin.AdminSite):
    site_header = "Job Board Administration"
    site_title = "Job Board Admin"
    index_title = "Welcome to Job Board Administration"
    
    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        # Add moderation dashboard link to admin index
        moderation_url = reverse('jobs:moderation_dashboard')
        extra_context['moderation_dashboard_url'] = moderation_url
        return super().index(request, extra_context)

# Register the custom admin site
admin_site = JobBoardAdminSite(name='admin')

# Re-register all models with the custom admin site
admin_site.register(Job, JobAdmin)
admin_site.register(JobApplication, JobApplicationAdmin)
admin_site.register(JobReport, JobReportAdmin)