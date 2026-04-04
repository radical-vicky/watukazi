from django.contrib import admin
from .models import JobRequest, JobMatch

@admin.register(JobRequest)
class JobRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'employer', 'location', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'location')
    search_fields = ('title', 'description', 'employer__username')
    filter_horizontal = ('required_skills',)

@admin.register(JobMatch)
class JobMatchAdmin(admin.ModelAdmin):
    list_display = ('job_request', 'worker', 'status', 'match_score', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('job_request__title', 'worker__username')