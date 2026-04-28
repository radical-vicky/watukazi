from django.contrib import admin
from .models import EmployerProfile

@admin.register(EmployerProfile)
class EmployerProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'company_name', 'industry', 'rating', 'total_jobs_posted', 'created_at']
    list_filter = ['industry', 'created_at']
    search_fields = ['company_name', 'user__username', 'user__email', 'business_registration']
    readonly_fields = ['rating', 'total_jobs_posted', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Company Information', {
            'fields': ('company_name', 'company_description', 'company_logo', 'industry', 'employee_count', 'year_established')
        }),
        ('Business Details', {
            'fields': ('business_registration', 'website')
        }),
        ('Statistics', {
            'fields': ('rating', 'total_jobs_posted')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')